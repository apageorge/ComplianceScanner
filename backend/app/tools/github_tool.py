"""
github_tool.py
--------------
Thin async wrapper around the GitHub REST API.
All methods return plain Python dicts / strings so they can be
fed directly back into the Claude context as tool results.
"""

import os
import httpx
from typing import Optional

_GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    pat = os.getenv("GITHUB_PAT", "")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if pat:
        h["Authorization"] = f"Bearer {pat}"
    return h


def parse_repo(github_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from any github.com URL."""
    parts = github_url.rstrip("/").replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse GitHub URL: {github_url}")
    return parts[0], parts[1]


async def get_repo_meta(owner: str, repo: str) -> dict:
    """Fetch top-level repo metadata (description, topics, language, etc.)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{_GITHUB_API}/repos/{owner}/{repo}", headers=_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        return {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "topics": data.get("topics", []),
            "language": data.get("language"),
            "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
            "default_branch": data.get("default_branch", "main"),
            "stars": data.get("stargazers_count"),
        }


async def get_readme(owner: str, repo: str) -> str:
    """Fetch the README as plain text (up to 8 KB to keep context lean)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_GITHUB_API}/repos/{owner}/{repo}/readme",
            headers={**_headers(), "Accept": "application/vnd.github.raw"},
            timeout=15,
        )
        if r.status_code == 404:
            return ""
        r.raise_for_status()
        return r.text[:8000]  # truncate generously


async def get_file_tree(owner: str, repo: str, branch: str = "main") -> list[str]:
    """
    Return a flat list of all file paths in the repo (recursive tree).
    Falls back to 'master' if 'main' is 404.
    """
    async with httpx.AsyncClient() as client:
        for b in [branch, "master", "main"]:
            r = await client.get(
                f"{_GITHUB_API}/repos/{owner}/{repo}/git/trees/{b}",
                params={"recursive": "1"},
                headers=_headers(),
                timeout=20,
            )
            if r.status_code == 200:
                items = r.json().get("tree", [])
                return [i["path"] for i in items if i["type"] == "blob"]
        r.raise_for_status()  # surface the last error
        return []


async def get_file_content(owner: str, repo: str, path: str) -> str:
    """
    Fetch a single file's raw content (truncated to 6 KB).
    Returns empty string if file not found or binary.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers={**_headers(), "Accept": "application/vnd.github.raw"},
            timeout=15,
        )
        if r.status_code == 404:
            return ""
        r.raise_for_status()
        try:
            return r.text[:6000]
        except Exception:
            return ""


async def search_code(owner: str, repo: str, query: str) -> list[dict]:
    """
    Search code within a single repo using GitHub code search.
    Returns up to 10 results with file path and a text fragment.

    GitHub code search requires authentication and is rate-limited
    to 10 req/min even with a PAT.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_GITHUB_API}/search/code",
            params={"q": f"{query} repo:{owner}/{repo}", "per_page": 10},
            headers=_headers(),
            timeout=20,
        )
        if r.status_code in (422, 503):
            # Search unavailable for this repo (too large, fork, etc.)
            return []
        r.raise_for_status()
        items = r.json().get("items", [])
        return [{"path": i["path"], "url": i["html_url"]} for i in items]


async def check_paths_exist(owner: str, repo: str, paths: list[str]) -> dict[str, bool]:
    """
    Given a list of file paths (or directory prefixes), check which exist
    by scanning the repo tree. Returns {path: bool}.
    """
    try:
        tree = await get_file_tree(owner, repo)
    except Exception:
        return {p: False for p in paths}

    tree_set = set(tree)
    result = {}
    for p in paths:
        # Match exact file or any file under a directory prefix
        result[p] = p in tree_set or any(f.startswith(p.rstrip("/") + "/") for f in tree_set)
    return result
