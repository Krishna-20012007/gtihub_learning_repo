"""
backend/agent.py
================
LangChain AI Agent powered by OpenRouter (ChatOpenRouter) and create_agent.

--- COLLEGE STUDENT EXPLANATION: WHAT IS AN AI AGENT? ---
A standard chatbot is reactive: you give it a prompt, it runs once through
an LLM, and replies with text.

An **AI Agent** is much more powerful! An Agent uses an LLM as a "reasoning brain"
connected to an active decision loop:
1. **Perception**: The agent reads user input, past conversation turns, and
   learning progress from database memory.
2. **Reasoning & Planning**: The agent thinks: "What does the student need?
   Should I inspect a real repository? Which tool should I use?"
3. **Action (Tool Calling)**: If needed, the agent invokes external tools
   (e.g., querying GitHub's REST API for branches, commits, or issues).
4. **Observation**: The agent reads the tool's output and integrates it.
5. **Response & State Update**: The agent delivers a personalized explanation,
   gives a practical task, and advances the student's learning progress.

--- HOW LANGCHAIN ORCHESTRATION WORKS ---
LangChain provides the framework that connects:
- The LLM provider (`ChatOpenRouter` routing to OpenRouter)
- The Tool definitions (`@tool` decorated functions)
- The Execution Graph (`create_agent` from `langchain.agents`)
When invoked, `create_agent` manages the cycle between the LLM and the tools
until a final answer is reached.
-----------------------------------------------------------------------------
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

from langchain_openrouter import ChatOpenRouter
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from backend.tools.github_tools import GITHUB_TOOLS
from backend.database import get_user_progress, update_user_progress, save_chat_message, get_chat_history

load_dotenv()

# Read configuration from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-5-mini").strip()

# Comprehensive 10-Lesson Curriculum metadata used by both Agent and /lessons endpoint
CURRICULUM = [
    {
        "id": 1,
        "title": "Git vs GitHub",
        "description": "Understand the fundamental distinction between local version control (Git) and cloud collaboration (GitHub).",
        "explanation": (
            "Git is a distributed version control software installed locally on your computer. It tracks file changes "
            "and history offline.\n\nGitHub is a cloud platform that hosts remote Git repositories and adds collaboration "
            "tools like Pull Requests, Issues, code reviews, and CI/CD pipelines."
        ),
        "example": "git --version          # Runs locally on your machine\ngithub.com/octocat     # Remote cloud hosting",
        "practical_task": "Ask the agent to search for popular repositories using `search_repositories` to see real projects on GitHub.",
        "quiz": [
            {
                "question": "Can you use Git without having a GitHub account or internet connection?",
                "options": [
                    "No, Git requires an active GitHub subscription",
                    "Yes, Git works completely offline on your local machine",
                    "Only if you have an enterprise license",
                    "No, Git requires internet to save commits"
                ],
                "correct_index": 1,
                "explanation": "Git is an offline distributed version control system. GitHub is merely a cloud remote host."
            }
        ]
    },
    {
        "id": 2,
        "title": "Repositories",
        "description": "Learn what a repository is, how Git tracks project files in the .git folder, and how remotes work.",
        "explanation": (
            "A repository (repo) is a container for your project files, commit history, and configuration. "
            "Inside every Git repo is a hidden `.git` folder that stores the database of snapshots, branches, and configs."
        ),
        "example": "git init my-project       # Initialize new local repo\ngit clone <repo-url>     # Clone remote repository",
        "practical_task": "Ask the agent to inspect repository details for 'octocat/Spoon-Knife' using `get_repository`.",
        "quiz": [
            {
                "question": "Where does Git store all of its commit history and tracking data in a project?",
                "options": [
                    "In a cloud server database",
                    "Inside the hidden .git directory in the project root",
                    "In the Windows Registry",
                    "In the node_modules folder"
                ],
                "correct_index": 1,
                "explanation": "The hidden `.git` folder contains Git's internal object store, refs, HEAD pointer, and config."
            }
        ]
    },
    {
        "id": 3,
        "title": "Commits",
        "description": "Master staging changes with git add, writing clear commit messages, and understanding SHA-1 commit hashes.",
        "explanation": (
            "A commit represents an immutable snapshot of your repository at a specific point in time. "
            "Before committing, you stage selected changes using `git add`. Each commit is identified by a unique 40-character SHA hash."
        ),
        "example": "git add index.html\ngit commit -m \"feat: add responsive navigation bar\"",
        "practical_task": "Ask the agent to show the recent commits on 'octocat/Spoon-Knife' using `get_recent_commits`.",
        "quiz": [
            {
                "question": "What is the purpose of the staging area (index) in Git?",
                "options": [
                    "To upload code directly to GitHub",
                    "To prepare and curate precisely which modified files will be included in the next commit",
                    "To permanently delete untracked files",
                    "To compile Python files"
                ],
                "correct_index": 1,
                "explanation": "The staging area lets you selectively assemble changes with `git add` before committing them."
            }
        ]
    },
    {
        "id": 4,
        "title": "Branches",
        "description": "Understand lightweight Git pointers, feature branches, and isolating new experiments without breaking main.",
        "explanation": (
            "A branch is essentially a lightweight, movable pointer to a commit. Creating branches allows multiple developers "
            "to work on different features or fixes in complete isolation without disrupting the stable `main` branch."
        ),
        "example": "git branch feature/user-profile    # Create branch\ngit switch feature/user-profile    # Switch to branch",
        "practical_task": "Ask the agent to list active branches on 'octocat/Spoon-Knife' using `get_branches`.",
        "quiz": [
            {
                "question": "What does Git's HEAD pointer represent?",
                "options": [
                    "The top-most directory of your hard drive",
                    "A reference pointing to the current branch/commit you currently have checked out",
                    "The GitHub user profile picture",
                    "The oldest commit in the repository"
                ],
                "correct_index": 1,
                "explanation": "HEAD points to the currently checked-out branch or commit in your working directory."
            }
        ]
    },
    {
        "id": 5,
        "title": "Merging",
        "description": "Learn how to combine branch histories, fast-forward merges, 3-way merges, and resolving merge conflicts.",
        "explanation": (
            "Merging integrates changes from one branch into another. If histories haven't diverged, Git does a fast-forward merge. "
            "If both branches edited the same lines of a file, Git generates conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) "
            "requiring manual resolution."
        ),
        "example": "git switch main\ngit merge feature/user-profile\n# If conflict occurs: edit file, git add, git commit",
        "practical_task": "Ask the agent: 'What happens during a merge conflict and how do I fix it?'",
        "quiz": [
            {
                "question": "What does Git do when two branches modify the exact same line of a file differently?",
                "options": [
                    "It automatically deletes the older file",
                    "It throws an unresolvable fatal error and destroys the repo",
                    "It pauses the merge and inserts conflict markers for the developer to review and resolve",
                    "It defaults to whatever is on GitHub"
                ],
                "correct_index": 2,
                "explanation": "Git stops and inserts conflict markers so you can manually decide which code to keep."
            }
        ]
    },
    {
        "id": 6,
        "title": "Pull Requests",
        "description": "Explore GitHub Pull Requests (PRs), code review etiquette, automated checks, and discussions.",
        "explanation": (
            "A Pull Request is a GitHub collaboration feature. You notify repository maintainers that you have completed work "
            "on a branch and request them to pull your changes into their branch. Maintainers can review diffs, leave comments, and approve."
        ),
        "example": "git push origin feature/login\n# Then open PR on GitHub comparing feature/login -> main",
        "practical_task": "Ask the agent to check open pull requests on 'octocat/Spoon-Knife' using `get_pull_requests`.",
        "quiz": [
            {
                "question": "Is a Pull Request a native command built into the local `git` CLI?",
                "options": [
                    "Yes, it is run with `git pull-request`",
                    "No, PRs are a hosting platform feature provided by GitHub, GitLab, etc.",
                    "Yes, added in Git 2.0",
                    "Only on Linux"
                ],
                "correct_index": 1,
                "explanation": "Pull Requests are collaboration mechanisms created by platforms like GitHub, not native git CLI commands."
            }
        ]
    },
    {
        "id": 7,
        "title": "Issues",
        "description": "Learn how to track bugs, suggest features, assign team members, and reference issues in commit messages.",
        "explanation": (
            "GitHub Issues act as project management boards. Anyone can report bugs or propose enhancements. "
            "You can link commits to issues by writing keywords like 'Fixes #42' in your commit message, which auto-closes the issue when merged."
        ),
        "example": "git commit -m \"fix: resolve mobile navbar overflow (Fixes #42)\"",
        "practical_task": "Ask the agent to retrieve open issues on 'octocat/Spoon-Knife' using `get_open_issues`.",
        "quiz": [
            {
                "question": "How can you automatically close issue #15 when merging a commit into the default branch?",
                "options": [
                    "Email GitHub support",
                    "Include 'Closes #15' or 'Fixes #15' in your commit message",
                    "Delete issue #15 manually beforehand",
                    "Tag the repo owner in a comment"
                ],
                "correct_index": 1,
                "explanation": "GitHub automatically links and closes issues when commit messages contain 'Fixes #<number>'."
            }
        ]
    },
    {
        "id": 8,
        "title": "Forks",
        "description": "Understand forking open-source repositories, configuring upstream remotes, and contributing upstream.",
        "explanation": (
            "A fork is your own personal copy of another user's repository on GitHub. It lives in your GitHub account, "
            "giving you full write access. You make changes on your fork, then submit a Pull Request back to the original (upstream) project."
        ),
        "example": "git remote add upstream https://github.com/original-author/repo.git\ngit fetch upstream",
        "practical_task": "Ask the agent to explain the difference between 'origin' and 'upstream' remotes.",
        "quiz": [
            {
                "question": "What is the primary difference between a fork and a branch?",
                "options": [
                    "A fork creates a separate copy of the repository in your own GitHub account; a branch lives inside the same repo",
                    "Branches can only be created by repository owners",
                    "Forks cannot have commits",
                    "There is no difference"
                ],
                "correct_index": 0,
                "explanation": "A fork is a complete personal clone of a repo on GitHub, allowing you to propose PRs without write permissions."
            }
        ]
    },
    {
        "id": 9,
        "title": "GitHub Actions",
        "description": "Introduction to Continuous Integration and Continuous Deployment (CI/CD) workflows using YAML automation.",
        "explanation": (
            "GitHub Actions allows you to automate software workflows directly in GitHub. You define workflows in YAML files "
            "under `.github/workflows/`. They automatically trigger on events (e.g., `on: push`) to run tests, linters, or build docker containers."
        ),
        "example": "name: CI\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: pytest",
        "practical_task": "Ask the agent: 'How does a GitHub Actions workflow trigger on a push event?'",
        "quiz": [
            {
                "question": "In which directory must GitHub Actions workflow YAML files be placed in a repository?",
                "options": [
                    "/.actions/",
                    "/.github/workflows/",
                    "/ci-cd/",
                    "In the project root directly"
                ],
                "correct_index": 1,
                "explanation": "GitHub looks for workflow definitions specifically in the `.github/workflows/` directory."
            }
        ]
    },
    {
        "id": 10,
        "title": "Basic Git Workflow",
        "description": "The complete end-to-end developer lifecycle: clone -> branch -> edit -> commit -> push -> PR -> merge.",
        "explanation": (
            "The standard real-world team workflow combines all previous lessons:\n"
            "1. Pull latest `main` (`git pull origin main`)\n"
            "2. Branch for your task (`git switch -c feature/my-task`)\n"
            "3. Make edits, stage, and commit (`git add . && git commit -m 'feat: ...'`)\n"
            "4. Push branch to remote (`git push origin feature/my-task`)\n"
            "5. Open Pull Request on GitHub, review code, pass CI, and merge!"
        ),
        "example": "git pull origin main\ngit switch -c feature/cool-idea\ngit add .\ngit commit -m \"feat: implement cool idea\"\ngit push origin feature/cool-idea",
        "practical_task": "Ask the agent to summarize the full workflow and test your readiness for open-source contributing!",
        "quiz": [
            {
                "question": "Before starting new work on a feature branch, what is the best practice command to run?",
                "options": [
                    "git push --force",
                    "git pull origin main (to ensure you have the latest updates from the team)",
                    "git init",
                    "git reset --hard"
                ],
                "correct_index": 1,
                "explanation": "Always pull the latest changes from the default branch before branching off to avoid outdated code."
            }
        ]
    }
]


def build_system_prompt(progress: Dict[str, Any]) -> str:
    """
    Constructs a rich pedagogical prompt tailored to the student's current standing.
    Informs the Agent about:
    - Persona: GitCoach, friendly and encouraging tutor.
    - Current lesson and skill level.
    - Tools available and when to invoke them.
    - Pedagogical requirements (explain, example, practical task, quiz prompt).
    """
    current_idx = min(max(progress.get("current_lesson", 1), 1), 10)
    current_lesson = CURRICULUM[current_idx - 1]
    completed_ids = progress.get("completed_lessons", [])
    skill = progress.get("skill_level", "Beginner")

    return f"""You are GitCoach, an expert interactive AI Agent dedicated to teaching Git and GitHub to college students and developers.

--- CURRENT STUDENT STANDING ---
- Student Skill Level: {skill}
- Current Lesson: Lesson {current_idx} - {current_lesson['title']}
- Completed Lessons: {completed_ids if completed_ids else 'None yet'}
- Total Lessons: 10

--- THE 10-LESSON CURRICULUM ---
1. Git vs GitHub
2. Repositories
3. Commits
4. Branches
5. Merging
6. Pull Requests
7. Issues
8. Forks
9. GitHub Actions
10. Basic Git workflow

--- YOUR RESPONSIBILITIES AS AN AI AGENT ---
1. Understand the student's question and adapt your explanations to their skill level ({skill}).
2. When teaching a lesson, provide:
   - A clear, simple explanation (no overwhelming jargon)
   - A concise, copy-pasteable command or syntax example
   - A practical task or challenge for the student to try
   - An invitation to take the interactive quiz or ask questions
3. ACTUALLY DECIDE WHEN TO USE TOOLS:
   - When asked about repositories, branches, commits, PRs, issues, or searching projects, ALWAYS call the appropriate tool from your toolkit:
     * `search_repositories(query)` -> find projects on GitHub
     * `get_repository(owner, repo)` -> inspect repo stars, forks, default branch
     * `get_branches(owner, repo)` -> list real branches
     * `get_recent_commits(owner, repo)` -> show real commit SHAs, authors, messages
     * `get_open_issues(owner, repo)` -> demonstrate issue tracking
     * `get_pull_requests(owner, repo)` -> demonstrate open PRs
   - Inspect the tool's output and explain it clearly to the student. Never make up fake GitHub data when a tool can fetch real data!
4. SKILL ASSESSMENT:
   - If the student shows strong familiarity, acknowledge their skill and note that their level is advancing.
   - If they are a beginner, provide extra analogies (e.g. Git commit = checkpoint in a video game).
5. PROGRESS TRACKING:
   - If the student demonstrates understanding of the current lesson (or says they finished the task), congratulate them and encourage them to advance to the next lesson!
"""


def get_agent_executor():
    """
    Initializes and returns the LangChain agent graph using `create_agent` and `ChatOpenRouter`.
    """
    # Instantiate ChatOpenRouter with specified model and key
    # Default: openai/gpt-5-mini; configurable via OPENROUTER_MODEL
    model = ChatOpenRouter(
        model=OPENROUTER_MODEL,
        temperature=0,
        api_key=OPENROUTER_API_KEY
    )

    # Use current LangChain API: create_agent
    agent_graph = create_agent(
        model=model,
        tools=GITHUB_TOOLS
    )
    return agent_graph


def format_educational_fallback(user_message: str, progress: Dict[str, Any], reason: str = "") -> str:
    """
    Generates a helpful, structured educational response if OpenRouter API is unavailable or unconfigured.
    This ensures that testing, demonstration, and student learning can continue gracefully even without an active key.
    """
    current_idx = min(max(progress.get("current_lesson", 1), 1), 10)
    lesson = CURRICULUM[current_idx - 1]
    msg_lower = user_message.lower()

    # Check for repository or GitHub inspection queries
    tool_demo = ""
    if "commit" in msg_lower:
        tool_demo = (
            "\n\n**[Live Tool Simulation: `get_recent_commits('octocat', 'Spoon-Knife')`]**\n"
            "- `[d0dd1f6]` by octocat (2024-03-15): \"Updated README with fork instructions\"\n"
            "- `[a1b2c3d]` by defunkt (2024-02-10): \"Change index.html text styling\"\n"
            "- `[e4f5a6b]` by octocat (2024-01-20): \"Add test stylesheet\"\n\n"
            "Notice how each commit has a 7-character short SHA hash, an author, a date, and a message describing *what* changed!"
        )
    elif "branch" in msg_lower:
        tool_demo = (
            "\n\n**[Live Tool Simulation: `get_branches('octocat', 'Spoon-Knife')`]**\n"
            "- `main` (default production branch)\n"
            "- `feature/change-spoons` (isolated feature branch)\n"
            "- `gh-pages` (GitHub Pages hosting branch)\n\n"
            "Branches allow you to work on separate experiments without touching `main` until you are ready!"
        )
    elif "issue" in msg_lower:
        tool_demo = (
            "\n\n**[Live Tool Simulation: `get_open_issues('octocat', 'Spoon-Knife')`]**\n"
            "- `#104`: \"Improve explanation of forking vs cloning in README\" (opened by @code-newbie)\n"
            "- `#99`: \"Broken link to GitHub Documentation\" (opened by @dev-learner)\n\n"
            "Issues are discussion boards for tracking bugs and planned features."
        )
    elif "pull" in msg_lower or "pr" in msg_lower:
        tool_demo = (
            "\n\n**[Live Tool Simulation: `get_pull_requests('octocat', 'Spoon-Knife')`]**\n"
            "- `PR #105`: \"docs: clarify branch creation command\" (by @git-fanatic)\n"
            "- `PR #102`: \"fix: update broken asset path in HTML\" (by @web-master)\n\n"
            "A Pull Request asks repo owners to review and merge your branch into their main codebase."
        )

    config_hint = ""
    if "api key" in reason.lower() or "unauthorized" in reason.lower() or not OPENROUTER_API_KEY:
        config_hint = (
            "\n\n> **Note**: To enable live OpenRouter LLM completions with model `" + OPENROUTER_MODEL + "`, "
            "add your active `OPENROUTER_API_KEY` to the `.env` file."
        )

    return (
        f"### Hello! I am GitCoach, your GitHub Learning AI Agent.\n\n"
        f"You are currently working on **Lesson {lesson['id']}: {lesson['title']}**.\n\n"
        f"**Explanation:**\n{lesson['explanation']}\n\n"
        f"**Example:**\n```bash\n{lesson['example']}\n```\n\n"
        f"**Practical Task:**\n{lesson['practical_task']}\n"
        f"{tool_demo}\n\n"
        f"You can also take the quiz on the right panel to test your knowledge and record your score!"
        f"{config_hint}"
    )


def process_user_message(session_id: str, user_message: str) -> Dict[str, Any]:
    """
    Core agent processing routine:
    1. Loads user progress & chat history from SQLite.
    2. Builds customized system prompt.
    3. Executes LangChain agent with tool calling via OpenRouter.
    4. Detects if tool calls occurred and inspects the result.
    5. Updates SQLite memory if the student advances or answers correctly.
    6. Returns structured response with updated progress and tool metadata.
    """
    # 1. Retrieve user progress
    progress = get_user_progress(session_id)
    save_chat_message(session_id, "user", user_message)

    tool_used = None
    agent_response_text = ""

    # Check if a valid API key is present
    has_valid_key = bool(OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("sk-or-your-key"))

    if has_valid_key:
        try:
            agent_graph = get_agent_executor()
            system_prompt = build_system_prompt(progress)

            # Build messages list
            messages = [SystemMessage(content=system_prompt)]

            # Load recent conversation history (last 6 messages)
            history = get_chat_history(session_id, limit=6)
            for h in history[:-1]:  # Exclude current user message which is appended next
                if h["role"] == "user":
                    messages.append(HumanMessage(content=h["content"]))
                else:
                    messages.append(AIMessage(content=h["content"]))

            messages.append(HumanMessage(content=user_message))

            # Invoke the LangChain agent graph
            result = agent_graph.invoke({"messages": messages})
            result_messages = result.get("messages", [])

            # Inspect if any tools were called during execution
            for msg in result_messages:
                if isinstance(msg, ToolMessage) or getattr(msg, "tool_call_id", None):
                    tool_used = getattr(msg, "name", "github_tool")
                    break

            # Extract the final AI message
            for msg in reversed(result_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    agent_response_text = str(msg.content)
                    break

            if not agent_response_text and result_messages:
                agent_response_text = str(result_messages[-1].content)

        except Exception as e:
            error_str = str(e)
            print(f"[Agent Execution Notice]: {error_str}")
            agent_response_text = format_educational_fallback(user_message, progress, reason=error_str)
    else:
        # Fallback tutor mode for testing/unconfigured key
        agent_response_text = format_educational_fallback(
            user_message,
            progress,
            reason="OPENROUTER_API_KEY is not configured or uses placeholder."
        )

    # 5. Persist assistant reply to database
    save_chat_message(session_id, "assistant", agent_response_text)

    # 6. Check if user asked to move to next lesson or if lesson completed
    msg_lower = user_message.lower()
    if any(phrase in msg_lower for phrase in ["next lesson", "completed lesson", "done with task", "move on", "advance"]):
        current_l = progress["current_lesson"]
        progress = update_user_progress(session_id, completed_lesson=current_l)

    return {
        "response": agent_response_text,
        "session_id": session_id,
        "progress": progress,
        "tool_called": tool_used
    }
