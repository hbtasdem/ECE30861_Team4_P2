import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Mapping, Union
from urllib.parse import urlparse

import requests

GITHUB_API = "https://api.github.com"


def get_pull_requests(owner: str, repo: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Get merged pull requests."""
    prs = []
    page = 1
    # limit the number of prs to 500
    # some repos have thousands of PRs and take too long to check all
    while page <= 5:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
        params: Mapping[str, Union[str, int]] = {"state": "closed", "per_page": 100, "page": page}
        r = requests.get(url, headers=headers, params=params)
        if r.status_code != 200:
            print(f"Error fetching PRs: {r.status_code}, {r.text}")
            break
        data = r.json()
        if not data:
            break
        merged_prs = [pr for pr in data if pr.get("merged_at")]
        prs.extend(merged_prs)
        page += 1
    return prs


def has_reviews(owner: str, repo: str, pr_number: str, headers: Dict[str, str]) -> bool:
    """Check if a PR has at least one review."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return False
    return len(r.json()) > 0


def pr_info(pr: Dict[str, Any], owner: str, repo: str, headers: Dict[str, str]) -> tuple[int, int]:
    """This function will be run in parallel for each PR"""
    pr_number = pr["number"]

    # Get total lines in PR
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    r = requests.get(url, headers=headers)
    pr_lines = 0
    if r.status_code == 200:
        data = r.json()
        pr_lines = data.get("additions", 0) + data.get("deletions", 0)
    # Check if PR has reviews
    reviewed = has_reviews(owner, repo, pr_number, headers)
    return pr_lines, reviewed


def reviewedness_score(repo_url: str) -> tuple[float, float]:
    """Compute reviewedness score between 0 and 1."""
    # start latency timer
    start = time.time()

    if not repo_url:
        end = time.time()
        latency = end - start
        return -1, latency

    # Extract owner and repo name from GitHub URL.
    path_parts = urlparse(repo_url).path.strip("/").split("/")
    owner = path_parts[0]
    repo = path_parts[1]

    # Look at pull requests
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}

    prs = get_pull_requests(owner, repo, headers)
    if not prs:
        end = time.time()
        latency = end - start
        return 0.0, latency

    total_lines = 0
    reviewed_lines = 0

    # Use ThreadPoolExecutor to fetch PR info concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Map each PR to pr_info; returns results in the same order
        results = executor.map(lambda pr: pr_info(pr, owner, repo, headers), prs)
        for pr_lines, reviewed in results:
            total_lines += pr_lines
            if reviewed:
                reviewed_lines += pr_lines

    if total_lines == 0:
        end = time.time()
        latency = end - start
        return 0.0, latency

    end = time.time()
    latency = end - start
    reviewedness = round(reviewed_lines / total_lines, 2)
    return (reviewedness, latency)


if __name__ == "__main__":
    # repo_url = "https://github.com/google-research/bert" # example with 0
    repo_url = "https://github.com/psf/requests"  # example with 1
    reviewedness, latency = reviewedness_score(repo_url)
    print("Reviewedness score:", reviewedness)
    print("Reviewedness latency: ", latency)
