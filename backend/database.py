"""
backend/database.py
===================
SQLite Database & Memory Persistence Layer for GitHub Learning AI Agent.

--- COLLEGE STUDENT EXPLANATION: HOW MEMORY & PROGRESS WORK IN AI AGENTS ---
By default, Large Language Models (LLMs) are stateless. Every time you send a
prompt to an LLM, it has zero recollection of previous conversations or what
lessons you have finished.

To turn an LLM into an intelligent, adaptive educational Agent, we need:
1. Short-Term Memory: Remembering the recent conversation turns so context
   is maintained within a chat session.
2. Long-Term State (Persistence): Storing the student's progress, skill level,
   completed lessons, and quiz scores in a reliable database (SQLite).

When the student sends a message, our backend queries this database to get their
current standing (e.g., "Student is at Lesson 3: Commits, Skill: Beginner").
This state is injected into the Agent's system prompt so the Agent knows exactly
where the student is in the curriculum and can personalize its instructions!
-----------------------------------------------------------------------------
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Database file path in the project root or backend folder
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "learning_agent.db")

TOTAL_LESSONS = 10


def get_db_connection() -> sqlite3.Connection:
    """Creates a thread-safe connection to the SQLite database with dictionary rows."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes database tables if they do not already exist.
    Creates:
      1. `user_progress`: Tracks student session, skill level, current lesson,
         completed lesson IDs (JSON array), and quiz scores (JSON dict).
      2. `chat_history`: Stores message history (user and assistant turns) for context.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table for tracking curriculum progress and skill assessment
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            session_id TEXT PRIMARY KEY,
            skill_level TEXT DEFAULT 'Beginner',
            current_lesson INTEGER DEFAULT 1,
            completed_lessons TEXT DEFAULT '[]',
            quiz_scores TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for persisting conversational history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES user_progress (session_id)
        )
    """)

    conn.commit()
    conn.close()


def get_user_progress(session_id: str) -> Dict[str, Any]:
    """
    Retrieves progress for a specific user session.
    If the user does not exist yet, creates an initial progress profile.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_progress WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()

    if row is None:
        # Create a new beginner session
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO user_progress (session_id, skill_level, current_lesson, completed_lessons, quiz_scores, created_at, updated_at)
            VALUES (?, 'Beginner', 1, '[]', '{}', ?, ?)
        """, (session_id, now, now))
        conn.commit()

        completed = []
        scores = {}
        progress_data = {
            "session_id": session_id,
            "skill_level": "Beginner",
            "current_lesson": 1,
            "completed_lessons": completed,
            "quiz_scores": scores,
            "progress_percentage": 0.0,
            "total_lessons": TOTAL_LESSONS
        }
    else:
        completed = json.loads(row["completed_lessons"]) if row["completed_lessons"] else []
        scores = json.loads(row["quiz_scores"]) if row["quiz_scores"] else {}
        pct = round((len(completed) / TOTAL_LESSONS) * 100, 1)
        progress_data = {
            "session_id": row["session_id"],
            "skill_level": row["skill_level"],
            "current_lesson": row["current_lesson"],
            "completed_lessons": completed,
            "quiz_scores": scores,
            "progress_percentage": min(pct, 100.0),
            "total_lessons": TOTAL_LESSONS
        }

    conn.close()
    return progress_data


def update_user_progress(
    session_id: str,
    skill_level: Optional[str] = None,
    current_lesson: Optional[int] = None,
    completed_lesson: Optional[int] = None,
    quiz_score: Optional[tuple[int, int]] = None  # (lesson_id, score_percentage)
) -> Dict[str, Any]:
    """
    Updates the student's progress in SQLite.
    Can update skill level, current lesson, mark a lesson as completed, or record quiz scores.
    """
    # Ensure profile exists
    current_data = get_user_progress(session_id)
    completed_list = current_data["completed_lessons"]
    scores_dict = current_data["quiz_scores"]

    new_skill = skill_level if skill_level is not None else current_data["skill_level"]
    new_lesson = current_lesson if current_lesson is not None else current_data["current_lesson"]

    if completed_lesson is not None and completed_lesson not in completed_list:
        completed_list.append(completed_lesson)
        completed_list.sort()
        # If the completed lesson is the current lesson, advance current_lesson if < 10
        if completed_lesson == new_lesson and new_lesson < TOTAL_LESSONS:
            new_lesson = new_lesson + 1

    if quiz_score is not None:
        lesson_id, score_val = quiz_score
        scores_dict[str(lesson_id)] = score_val
        # If passing score (>= 70), automatically mark completed if not already
        if score_val >= 70 and lesson_id not in completed_list:
            completed_list.append(lesson_id)
            completed_list.sort()
            if lesson_id == new_lesson and new_lesson < TOTAL_LESSONS:
                new_lesson = new_lesson + 1

    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        UPDATE user_progress
        SET skill_level = ?,
            current_lesson = ?,
            completed_lessons = ?,
            quiz_scores = ?,
            updated_at = ?
        WHERE session_id = ?
    """, (
        new_skill,
        new_lesson,
        json.dumps(completed_list),
        json.dumps(scores_dict),
        now,
        session_id
    ))

    conn.commit()
    conn.close()

    return get_user_progress(session_id)


def reset_user_progress(session_id: str) -> Dict[str, Any]:
    """Resets the student's progress and quiz scores back to lesson 1."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        UPDATE user_progress
        SET skill_level = 'Beginner',
            current_lesson = 1,
            completed_lessons = '[]',
            quiz_scores = '{}',
            updated_at = ?
        WHERE session_id = ?
    """, (now, session_id))

    # Also clear chat history for clean slate
    cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))

    conn.commit()
    conn.close()

    return get_user_progress(session_id)


def save_chat_message(session_id: str, role: str, content: str):
    """Persists a message in chat history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (session_id, role, content)
        VALUES (?, ?, ?)
    """, (session_id, role, content))
    conn.commit()
    conn.close()


def get_chat_history(session_id: str, limit: int = 15) -> List[Dict[str, str]]:
    """Retrieves recent conversation messages for prompt context."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM chat_history
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT ?
    """, (session_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# Initialize the database on module import
init_db()
