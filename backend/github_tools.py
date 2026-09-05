"""
backend/tools/github_tools.py
=============================
GitHub REST API Tools for the LangChain GitHub Learning AI Agent.

--- COLLEGE STUDENT EXPLANATION: WHAT ARE TOOLS & HOW DO THEY WORK? ---
An LLM (like GPT) is trained on static data up to a knowledge cutoff date.
It cannot natively browse the live internet, check your real repository, or
read GitHub commit hashes.

Tools bridge this gap! In LangChain, a "Tool" is a Python function annotated
with the `@tool` decorator. LangChain inspects the function's:
1. Name (e.g. `get_recent_commits`)
2. Type hints (e.g. `owner: str, repo: str`)
3. Docstring ("Fetch the 5 most recent commits...")

When the Agent receives a user prompt (e.g., "What was the last commit on
octocat/Spoon-Knife?"), the LLM reads the tool docstrings, decides:
"Aha! I need the get_recent_commits tool with owner='octocat', repo='Spoon-Knife'!"
The Agent emits a structured tool call, our code runs the Python function,
and passes the real GitHub REST API output back to the LLM. The LLM inspects
the output and formulates a helpful explanation for the student!
-----------------------------------------------------------------------------
"""

import os
import requests
from typing import List, Dict, Any
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()


def _get_headers() -> Dict[str, str]:
    """
    Constructs standard GitHub REST API headers.
    If GITHUB_TOKEN is configured, sends Authorization header to enjoy higher rate limits (5,000 req/hr).
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Learning-AI-Agent"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


# Fallback / Mock Data for popular repositories in case GitHub rate limit (403) or offline occurs
DEMO_DATA = {
    "octocat/Spoon-Knife": {
        "repo": {
            "name": "Spoon-Knife",
            "full_name": "octocat/Spoon-Knife",
            "description": "This repo is for spoon-knife demonstration and training forks.",
            "stars": 13800,
            "forks": 142500,
            "default_branch": "main",
            "open_issues": 1240,
            "language": "HTML"
        },
        "branches": ["main", "feature/change-spoons", "patch-1", "gh-pages"],
        "commits": [
            {"sha": "d0dd1f6", "author": "octocat", "message": "Updated README with fork instructions", "date": "2024-03-15"},
            {"sha": "a1b2c3d", "author": "defunkt", "message": "Change index.html text styling", "date": "2024-02-10"},
            {"sha": "e4f5a6b", "author": "octocat", "message": "Add test stylesheet", "date": "2024-01-20"},
            {"sha": "9c8b7a6", "author": "student-contributor", "message": "Fix typo in tutorial notes", "date": "2023-11-05"},
            {"sha": "5e4d3c2", "author": "octocat", "message": "Initial commit with spoon-knife demo", "date": "2023-01-01"}
        ],
        "issues": [
            {"number": 104, "title": "Improve explanation of forking vs cloning in README", "user": "code-newbie", "state": "open", "comments": 4},
            {"number": 99, "title": "Broken link to GitHub Documentation", "user": "dev-learner", "state": "open", "comments": 2},
            {"number": 87, "title": "Add step-by-step example for creating Pull Requests", "user": "student99", "state": "open", "comments": 7}
        ],
        "pulls": [
            {"number": 105, "title": "docs: clarify branch creation command", "user": "git-fanatic", "state": "open", "created_at": "2024-03-18"},
            {"number": 102, "title": "fix: update broken asset path in HTML", "user": "web-master", "state": "open", "created_at": "2024-03-10"},
            {"number": 98, "title": "feat: add interactive Git cheatsheet in README", "user": "open-sourcerer", "state": "open", "created_at": "2024-02-28"}
        ]
    }
}


@tool
def search_repositories(query: str) -> str:
    """
    Searches GitHub for public repositories matching a search query.
    Use this tool when a student asks to find popular projects, libraries, or examples on GitHub.
    
    Args:
        query: The search keywords (e.g. 'fastapi', 'machine learning', 'react').
    """
    url = f"{GITHUB_API_BASE}/search/repositories"
    params = {"q": query, "per_page": 5, "sort": "stars", "order": "desc"}
    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if not items:
                return f"No repositories found matching '{query}'."
            results = []
            for item in items:
                results.append(
                    f"- {item.get('full_name')} (* {item.get('stargazers_count')} stars)\n"
                    f"  Description: {item.get('description') or 'No description'}\n"
                    f"  URL: {item.get('html_url')}\n"
                    f"  Language: {item.get('language') or 'N/A'}"
                )
            return f"Found top repositories for '{query}':\n\n" + "\n\n".join(results)
        elif response.status_code == 403:
            # Rate limited fallback
            return (
                f"[Notice: GitHub API rate limit reached. Showing educational demo repositories for '{query}']:\n\n"
                f"- octocat/Spoon-Knife (* 13,800 stars) - Educational repo for practicing forks and branching.\n"
                f"- torvalds/linux (* 175,000 stars) - The Linux kernel source tree, the largest Git project.\n"
                f"- tiangolo/fastapi (* 78,000 stars) - High-performance modern Python web framework."
            )
        else:
            return f"GitHub API search returned status {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return f"Error executing search_repositories for '{query}': {str(e)}"


@tool
def get_repository(owner: str, repo: str) -> str:
    """
    Retrieves metadata about a specific GitHub repository, including stars, forks, default branch, and description.
    Use this tool when teaching Lesson 2 (Repositories) or when a student asks about a specific repository.
    
    Args:
        owner: The username or organization owning the repo (e.g. 'octocat' or 'tiangolo').
        repo: The repository name (e.g. 'Spoon-Knife' or 'fastapi').
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=10)
        if response.status_code == 200:
            data = response.json()
            return (
                f"Repository: {data.get('full_name')}\n"
                f"Description: {data.get('description') or 'No description'}\n"
                f"Stars: {data.get('stargazers_count')} | Forks: {data.get('forks_count')}\n"
                f"Default Branch: {data.get('default_branch')}\n"
                f"Open Issues: {data.get('open_issues_count')}\n"
                f"Primary Language: {data.get('language') or 'Not specified'}\n"
                f"Clone URL: {data.get('clone_url')}\n"
                f"License: {data.get('license', {}).get('name') if data.get('license') else 'None'}"
            )
        else:
            # Check demo data fallback
            key = f"{owner}/{repo}"
            if key in DEMO_DATA:
                d = DEMO_DATA[key]["repo"]
                return (
                    f"[Educational Demo Data for {key}]:\n"
                    f"Repository: {d['full_name']}\n"
                    f"Description: {d['description']}\n"
                    f"Stars: {d['stars']} | Forks: {d['forks']}\n"
                    f"Default Branch: {d['default_branch']}\n"
                    f"Open Issues: {d['open_issues']}\n"
                    f"Primary Language: {d['language']}\n"
                    f"Clone URL: https://github.com/{key}.git"
                )
            return f"Unable to fetch repository {owner}/{repo}. Status: {response.status_code}"
    except Exception as e:
        return f"Error retrieving repository {owner}/{repo}: {str(e)}"


@tool
def get_branches(owner: str, repo: str) -> str:
    """
    Lists the branches available in a GitHub repository.
    Use this tool when teaching Lesson 4 (Branches) or illustrating how branches isolate code changes.
    
    Args:
        owner: The owner of the repository (e.g. 'octocat').
        repo: The repository name (e.g. 'Spoon-Knife').
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches"
    try:
        response = requests.get(url, headers=_get_headers(), params={"per_page": 10}, timeout=10)
        if response.status_code == 200:
            branches = response.json()
            if not branches:
                return f"No branches found for {owner}/{repo}."
            branch_names = [f"- {b.get('name')} (latest commit: {b.get('commit', {}).get('sha', '')[:7]})" for b in branches]
            return f"Branches in {owner}/{repo}:\n" + "\n".join(branch_names)
        else:
            key = f"{owner}/{repo}"
            if key in DEMO_DATA:
                branches = DEMO_DATA[key]["branches"]
                return f"[Educational Demo Branches for {key}]:\n" + "\n".join([f"- {b}" for b in branches])
            return f"Could not fetch branches for {owner}/{repo}. Status: {response.status_code}"
    except Exception as e:
        return f"Error fetching branches for {owner}/{repo}: {str(e)}"


@tool
def get_recent_commits(owner: str, repo: str) -> str:
    """
    Fetches the 5 most recent commits for a GitHub repository.
    Use this tool when teaching Lesson 3 (Commits) to show commit hashes, authors, messages, and timestamps.
    
    Args:
        owner: The repository owner (e.g. 'octocat').
        repo: The repository name (e.g. 'Spoon-Knife').
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
    try:
        response = requests.get(url, headers=_get_headers(), params={"per_page": 5}, timeout=10)
        if response.status_code == 200:
            commits = response.json()
            if not commits:
                return f"No commits found in {owner}/{repo}."
            lines = []
            for c in commits:
                sha = c.get("sha", "")[:7]
                commit_info = c.get("commit", {})
                author = commit_info.get("author", {}).get("name", "Unknown")
                date = commit_info.get("author", {}).get("date", "")[:10]
                message = commit_info.get("message", "").split("\n")[0]
                lines.append(f"- [{sha}] by {author} ({date}): \"{message}\"")
            return f"Recent commits in {owner}/{repo}:\n" + "\n".join(lines)
        else:
            key = f"{owner}/{repo}"
            if key in DEMO_DATA:
                commits = DEMO_DATA[key]["commits"]
                lines = [f"- [{c['sha']}] by {c['author']} ({c['date']}): \"{c['message']}\"" for c in commits]
                return f"[Educational Demo Commits for {key}]:\n" + "\n".join(lines)
            return f"Could not fetch commits for {owner}/{repo}. Status: {response.status_code}"
    except Exception as e:
        return f"Error fetching recent commits for {owner}/{repo}: {str(e)}"


@tool
def get_open_issues(owner: str, repo: str) -> str:
    """
    Retrieves the 5 most recent open issues for a GitHub repository.
    Use this tool when teaching Lesson 7 (Issues) to demonstrate bug tracking, issue numbers, and discussion threads.
    
    Args:
        owner: The repository owner (e.g. 'octocat').
        repo: The repository name (e.g. 'Spoon-Knife').
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    try:
        response = requests.get(url, headers=_get_headers(), params={"state": "open", "per_page": 5}, timeout=10)
        if response.status_code == 200:
            issues = response.json()
            # GitHub issues endpoint returns pull requests as well; filter to pure issues if needed
            pure_issues = [i for i in issues if "pull_request" not in i]
            if not pure_issues:
                return f"No open issues found in {owner}/{repo}."
            lines = []
            for i in pure_issues[:5]:
                number = i.get("number")
                title = i.get("title")
                author = i.get("user", {}).get("login", "Unknown")
                comments = i.get("comments", 0)
                lines.append(f"- #{number}: \"{title}\" (opened by @{author}, {comments} comments)")
            return f"Open issues in {owner}/{repo}:\n" + "\n".join(lines)
        else:
            key = f"{owner}/{repo}"
            if key in DEMO_DATA:
                issues = DEMO_DATA[key]["issues"]
                lines = [f"- #{i['number']}: \"{i['title']}\" (opened by @{i['user']}, {i['comments']} comments)" for i in issues]
                return f"[Educational Demo Issues for {key}]:\n" + "\n".join(lines)
            return f"Could not fetch open issues for {owner}/{repo}. Status: {response.status_code}"
    except Exception as e:
        return f"Error fetching open issues for {owner}/{repo}: {str(e)}"


@tool
def get_pull_requests(owner: str, repo: str) -> str:
    """
    Retrieves the 5 most recent open pull requests (PRs) for a GitHub repository.
    Use this tool when teaching Lesson 6 (Pull Requests) to explain how developers propose code changes for review.
    
    Args:
        owner: The repository owner (e.g. 'octocat').
        repo: The repository name (e.g. 'Spoon-Knife').
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    try:
        response = requests.get(url, headers=_get_headers(), params={"state": "open", "per_page": 5}, timeout=10)
        if response.status_code == 200:
            pulls = response.json()
            if not pulls:
                return f"No open pull requests found in {owner}/{repo}."
            lines = []
            for p in pulls[:5]:
                number = p.get("number")
                title = p.get("title")
                author = p.get("user", {}).get("login", "Unknown")
                created_at = p.get("created_at", "")[:10]
                lines.append(f"- PR #{number}: \"{title}\" (by @{author} on {created_at})")
            return f"Open pull requests in {owner}/{repo}:\n" + "\n".join(lines)
        else:
            key = f"{owner}/{repo}"
            if key in DEMO_DATA:
                pulls = DEMO_DATA[key]["pulls"]
                lines = [f"- PR #{p['number']}: \"{p['title']}\" (by @{p['user']} on {p['created_at']})" for p in pulls]
                return f"[Educational Demo Pull Requests for {key}]:\n" + "\n".join(lines)
            return f"Could not fetch pull requests for {owner}/{repo}. Status: {response.status_code}"
            return f"Could not fetch pull requests for {owner}/{repo}. Status: {response.status_code}"
    except Exception as e:
        return f"Error fetching pull requests for {owner}/{repo}: {str(e)}"


# Export list of all tools for LangChain agent binding
GITHUB_TOOLS = [
    search_repositories,
    get_repository,
    get_branches,
    get_recent_commits,
    get_open_issues,
    get_pull_requests
]
