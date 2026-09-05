# GitHub Learning AI Agent 🚀

An interactive, agentic learning platform that teaches Git and GitHub through hands-on practice, live GitHub REST API tool calling, automated quizzes, and persistent progress tracking.

Built with **Python 3.11+**, **LangChain**, **OpenRouter**, **FastAPI**, **SQLite**, and vanilla **HTML/CSS/JavaScript**.

---

## 🌟 Key Features

* **Real LangChain Agent**: Uses `langchain.agents.create_agent` with dynamic tool calling—not an ordinary static chatbot.
* **Exclusively OpenRouter**: Powered by `langchain-openrouter` using `ChatOpenRouter` with configurable models (`openai/gpt-5-mini` by default).
* **Live GitHub Tools**: Inspects real GitHub repositories with 6 custom `@tool` functions using the GitHub REST API.
* **10-Lesson Interactive Curriculum**: Complete pedagogical path from "Git vs GitHub" to "Basic Git Workflow".
* **Persistent SQLite Memory**: Stores student session progress, skill level assessment, completed lessons, and quiz scores across sessions.
* **Modern Responsive UI**: Dark glassmorphic dashboard with live progress meters, chat feed, interactive code examples, and instant-feedback quizzes.
* **Resilient & Safe**: Non-destructive operations only. Automatically falls back to educational mock data if GitHub rate limits occur.

---

## 📚 10-Lesson Curriculum

1. **Git vs GitHub**: Local version control vs cloud collaboration.
2. **Repositories**: Project anatomy, `.git` internals, cloning and remotes.
3. **Commits**: Staging with `git add`, commit messages, SHA hashes.
4. **Branches**: Lightweight pointers, feature branching, HEAD reference.
5. **Merging**: Fast-forward merges, 3-way merges, conflict resolution.
6. **Pull Requests**: Code review etiquette, discussions, merging PRs.
7. **Issues**: Bug tracking, linking commits via `Fixes #...`.
8. **Forks**: Contributing to open source, upstream remotes.
9. **GitHub Actions**: CI/CD automation, workflows, YAML triggers.
10. **Basic Git Workflow**: Full real-world lifecycle from branch to production.

---

## 🛠️ GitHub REST API Tools

The agent has access to 6 specialized LangChain `@tool` functions:

| Tool | Purpose | Example Query |
| :--- | :--- | :--- |
| `search_repositories(query)` | Search public repos by popularity | `search_repositories("fastapi")` |
| `get_repository(owner, repo)` | Retrieve stars, forks, default branch | `get_repository("octocat", "Spoon-Knife")` |
| `get_branches(owner, repo)` | List active branches in a repo | `get_branches("octocat", "Spoon-Knife")` |
| `get_recent_commits(owner, repo)` | Inspect recent commit SHAs and messages | `get_recent_commits("octocat", "Spoon-Knife")` |
| `get_open_issues(owner, repo)` | Review open bug reports and discussions | `get_open_issues("octocat", "Spoon-Knife")` |
| `get_pull_requests(owner, repo)` | Inspect proposed pull requests | `get_pull_requests("octocat", "Spoon-Knife")` |

---

## 🎓 College Student Guide: How the AI Agent Works

### 1. What is an AI Agent?
A regular chatbot simply takes an input string and generates an output string based on training data. An **AI Agent** uses an LLM as a *reasoning engine* inside an action loop: it interprets your goals, queries external databases or APIs, analyzes real-world output, and decides what action to take next.

### 2. How LangChain Works
LangChain is an orchestration framework that connects modular building blocks:
- **Models**: Standardized interfaces to LLM providers (e.g. `ChatOpenRouter`).
- **Tools**: Python functions that the LLM can decide to execute (`@tool`).
- **Agent Graphs**: Compiled graphs (`create_agent`) that loop between model thinking and tool execution until a final answer is prepared.

### 3. How Tools Work and How the Agent Chooses Them
When you annotate a Python function with `@tool`, LangChain generates a JSON Schema containing the function name, arguments, and docstring. When you ask: *"Show me the latest commits on octocat/Spoon-Knife"*, the LLM reads the tool schemas, matches your intent to `get_recent_commits`, extracts `owner="octocat"` and `repo="Spoon-Knife"`, executes the function via HTTP, and explains the results.

### 4. How Memory and Progress Work
LLMs are stateless by default. We bridge this with **SQLite** (`learning_agent.db`). Every time you chat or take a quiz:
- The backend loads your current lesson, skill level, and quiz scores from SQLite.
- This state is injected into the Agent's system prompt so it personalizes its lessons.
- When you pass a quiz or finish a task, SQLite is updated immediately!

---

## 📂 Project Structure

```text
github-learning-agent/
├── backend/
│   ├── main.py              # FastAPI application, REST endpoints, and static file mount
│   ├── agent.py             # LangChain agent graph with ChatOpenRouter and curriculum
│   ├── database.py          # SQLite database tracking progress, sessions, and scores
│   └── tools/
│       ├── __init__.py      # Tool exports
│       └── github_tools.py  # LangChain @tool definitions with GitHub REST API integration
├── frontend/
│   ├── index.html           # Responsive 3-column dashboard layout
│   ├── style.css            # Curated modern dark theme with glassmorphism
│   └── script.js            # Client logic connecting to /chat, /progress, and /lessons
├── .env.example             # Environment variable template
├── .gitignore               # Ignored files (venv, .env, *.db)
├── requirements.txt         # Pinned Python package dependencies
└── README.md                # Project documentation and student guide
```

---

## 🚀 Quick Setup Instructions

### 1. Prerequisites
- Python 3.11 or higher
- An OpenRouter API key ([Get one free or paid at openrouter.ai](https://openrouter.ai/keys))

### 2. Clone and Setup Environment
```bash
# Navigate to project directory
cd github-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and set your OpenRouter API key:
```env
OPENROUTER_API_KEY=sk-or-v1-your-real-openrouter-key
OPENROUTER_MODEL=openai/gpt-5-mini
GITHUB_TOKEN=
```
*(Note: `GITHUB_TOKEN` is optional. If left empty, public GitHub endpoints and graceful demo fallbacks are used).*

### 4. Run the Application
Start the FastAPI server:
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
or run directly with Python:
```bash
python backend/main.py
```

### 5. Access the Web Dashboard
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 🔌 API Reference

### `POST /chat`
Sends a message to the LangChain agent.
```json
// Request
{
  "message": "What is the difference between git fetch and git pull?",
  "session_id": "student_123"
}

// Response
{
  "response": "...",
  "session_id": "student_123",
  "progress": {
    "current_lesson": 1,
    "completed_lessons": [],
    "progress_percentage": 0.0,
    "skill_level": "Beginner"
  },
  "tool_called": null
}
```

### `GET /progress?session_id={session_id}`
Returns the user's current standing and quiz scores.

### `GET /lessons`
Returns the complete 10-lesson curriculum and quiz questions.

### `POST /quiz/submit`
Submits an answer for automatic grading and records progress in SQLite.
```json
{
  "session_id": "student_123",
  "lesson_id": 1,
  "selected_option": 1
}
```

### `POST /progress/reset`
Resets the student's progress and quiz scores back to Lesson 1.

---

## 🧪 Testing

Run backend tests using Python:
```bash
python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); print(c.get('/lessons').status_code)"
```
Test GitHub tools individually:
```bash
python -c "from backend.tools.github_tools import get_repository; print(get_repository.invoke({'owner':'octocat','repo':'Spoon-Knife'}))"
```
