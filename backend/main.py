"""
backend/main.py
===============
FastAPI Server & REST API Endpoints for the GitHub Learning AI Agent.

--- COLLEGE STUDENT EXPLANATION: HOW FASTAPI CONNECTS THE USER TO THE AGENT ---
FastAPI is a modern, high-performance web framework for Python.
Think of FastAPI as the "receptionist" and "router" of our AI Agent system:
1. When a user clicks "Send" in their browser, JavaScript sends an HTTP POST
   request with their message and session ID to `/chat`.
2. FastAPI validates the incoming JSON data using Pydantic models.
3. FastAPI calls `process_user_message(session_id, message)`, which passes the
   data to our LangChain Agent (`agent.py`).
4. The Agent reasons, optionally calls GitHub tools (`github_tools.py`), and updates
   progress in SQLite (`database.py`).
5. FastAPI packages the Agent's answer and the updated progress into a clean JSON
   response and sends it back to the browser!
-----------------------------------------------------------------------------
"""

import os
import uuid
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.agent import process_user_message, CURRICULUM
from backend.database import (
    init_db,
    get_user_progress,
    update_user_progress,
    reset_user_progress
)

# Initialize FastAPI application
app = FastAPI(
    title="GitHub Learning AI Agent API",
    description="Interactive Git & GitHub Learning Platform powered by LangChain and OpenRouter",
    version="1.0.0"
)

# Enable CORS (Cross-Origin Resource Sharing) so frontend can communicate smoothly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database tables exist on server startup
init_db()


# ----------------- PYDANTIC REQUEST & RESPONSE MODELS -----------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The message sent by the student")
    session_id: Optional[str] = Field(default=None, description="Unique session ID for memory tracking")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    progress: Dict[str, Any]
    tool_called: Optional[str] = None


class ResetRequest(BaseModel):
    session_id: str = Field(..., description="Unique session ID to reset")


class QuizSubmitRequest(BaseModel):
    session_id: str
    lesson_id: int
    selected_option: int  # index of the chosen option (0-based)


# ----------------- REST API ENDPOINTS -----------------

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint:
    Receives student message -> Invokes LangChain Agent -> Returns AI response + updated progress.
    """
    session_id = request.session_id or str(uuid.uuid4())
    try:
        agent_result = process_user_message(session_id, request.message)
        return ChatResponse(
            response=agent_result["response"],
            session_id=agent_result["session_id"],
            progress=agent_result["progress"],
            tool_called=agent_result.get("tool_called")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent processing error: {str(e)}")


@app.get("/progress")
async def get_progress_endpoint(session_id: str = Query(..., description="Student session ID")):
    """
    Returns the student's current learning progress, completed lessons, and quiz scores.
    """
    try:
        progress = get_user_progress(session_id)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch progress: {str(e)}")


@app.get("/lessons")
async def get_lessons_endpoint():
    """
    Returns the complete 10-lesson curriculum metadata including explanations,
    command examples, practical tasks, and quiz questions.
    """
    return {
        "total_lessons": len(CURRICULUM),
        "lessons": CURRICULUM
    }


@app.post("/progress/reset")
async def reset_progress_endpoint(request: Optional[ResetRequest] = None, session_id: Optional[str] = None):
    """
    Resets the student's progress and quiz scores back to Lesson 1.
    Accepts session_id in request body or as a query parameter.
    """
    sid = None
    if request and request.session_id:
        sid = request.session_id
    elif session_id:
        sid = session_id
    
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        updated_progress = reset_user_progress(sid)
        return {
            "message": "Progress successfully reset to Lesson 1",
            "progress": updated_progress
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset progress: {str(e)}")


@app.post("/quiz/submit")
async def submit_quiz_endpoint(submission: QuizSubmitRequest):
    """
    Evaluates a student's answer for a lesson quiz, records the score in SQLite,
    and advances the lesson progress upon passing (score >= 70%).
    """
    lesson_id = submission.lesson_id
    if lesson_id < 1 or lesson_id > len(CURRICULUM):
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson = CURRICULUM[lesson_id - 1]
    quiz_items = lesson.get("quiz", [])
    if not quiz_items:
        raise HTTPException(status_code=400, detail="No quiz available for this lesson")

    # Evaluate the first quiz question (or single question per lesson)
    question = quiz_items[0]
    is_correct = (submission.selected_option == question["correct_index"])
    score = 100 if is_correct else 0

    # Update progress in database
    updated_progress = update_user_progress(
        session_id=submission.session_id,
        quiz_score=(lesson_id, score),
        completed_lesson=lesson_id if is_correct else None
    )

    return {
        "lesson_id": lesson_id,
        "is_correct": is_correct,
        "score": score,
        "explanation": question.get("explanation", ""),
        "progress": updated_progress
    }


# ----------------- STATIC FRONTEND SERVING -----------------

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.exists(frontend_dir):
    # Mount static assets (/style.css, /script.js, etc.)
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        """Serves the frontend main dashboard HTML."""
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend index.html not found"}

    @app.get("/style.css")
    async def serve_css():
        return FileResponse(os.path.join(frontend_dir, "style.css"))

    @app.get("/script.js")
    async def serve_js():
        return FileResponse(os.path.join(frontend_dir, "script.js"))


if __name__ == "__main__":
    import uvicorn
    print("Starting GitHub Learning AI Agent on http://localhost:8000")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
