# Metric calculation: reviewedness

# TO RUN LOCAL: ADD ENVIRONMENT VARIABLE
# GITHUB_TOKEN = "yourgithubtoken"

import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Mapping, Union
from urllib.parse import urlparse

import boto3
import requests

GITHUB_API = "https://api.github.com"


def get_github_token() -> Any:
    """
    Get github token for api from ec2 or local env.

    Parameters
    ----------
    None

    Returns
    ----------
    str
        The github token
    """
    try:
        ssm = boto3.client("ssm", region_name="us-east-2")
        response = ssm.get_parameter(Name="/ece30861/GITHUB_TOKEN", WithDecryption=True)
        token = response["Parameter"]["Value"]
        if token:
            return token
    except Exception as e:
        print(f"Reviewedness: error fetching GitHub token. {e}")
        pass
    # no parameter found or no ec2 attahched or running locally w/o credentials
    # look for local env variable
    token = os.getenv("GITHUB_TOKEN")
    return token


def get_pull_requests(
    owner: str, repo: str, headers: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Get pull request info from git repo

    Parameters
    ----------
    owner : str
        owner of repo parsed from url.
    repo: str
        repo name parsed from url.
    headers: Dict[str, str]
        contains GITHUB_TOKEN from env variables.

    Returns
    -------
    List[Dict[str, Any]]
        List of dictionaries with pull request information
    """
    prs = []
    page = 1
    # limit the number of prs, some repos have thousands of PRs and take too long to check all
    # github api rate limit is 60 per hour. so we can only check 60...?
    while (
        page <= 1
    ):  # left as while loop in case we want to increase # prs checked easily
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
        params: Mapping[str, Union[str, int]] = {
            "state": "closed",
            "per_page": 60,
            "page": page,
        }
        r = requests.get(url, headers=headers, params=params)
        if r.status_code != 200:
            print(f"Reviewedness: Error fetching PRs for {owner}/{repo}: {r.status_code}, {r.text}")
            break
        data = r.json()
        if not data:
            break
        merged_prs = [pr for pr in data if pr.get("merged_at")]
        prs.extend(merged_prs)
        page += 1
    return prs


def pr_info(
    pr: Dict[str, Any], owner: str, repo: str, headers: Dict[str, str]
) -> tuple[int, int]:
    """
    Get pull request info from git repo.

    Parameters
    ----------
    owner : str
        owner of repo parsed from url.
    repo: str
        repo name parsed from url.
    headers: Dict[str, str]
        contains GITHUB_TOKEN from env variables.

    Returns
    -------
    List[Dict[str, Any]]
        List of dictionaries with pull request information
    """
    pr_number = pr["number"]

    # Get total lines in PR
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    r = requests.get(url, headers=headers)
    pr_lines = 0
    if r.status_code == 200:
        data = r.json()
        pr_lines = data.get("additions", 0) + data.get("deletions", 0)
    # Check if PR has reviews
    """Check if a PR has at least one review."""
    review_url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    rev_r = requests.get(review_url, headers=headers)
    if rev_r.status_code != 200:
        reviewed = False
    reviewed = len(rev_r.json()) > 0

    return pr_lines, reviewed


def reviewedness_score(code_url: str) -> tuple[float, float]:
    """
    Calculate reviewedness metric.

    Parameters
    ----------
    code_url : str
        code_url for github code repo.

    Returns
    -------
    tuple[float, float]
        reviewedness score between 0-1, or -1 if no code_url
        latency in ms
    """
    # start latency timer
    start = time.time()

    if not code_url:
        end = time.time()
        latency = (end - start) * 1000
        return -1, latency

    if 'github.com' not in code_url.lower():
        print(f"ERROR Reviewedness: not given github code url, {code_url}")

    # Extract owner and repo name from GitHub URL.
    path_parts = urlparse(code_url).path.strip("/").split("/")
    owner = path_parts[0]
    repo = path_parts[1]

    # Need github token to use github api
    token = get_github_token()
    headers = {"Authorization": f"token {token}"} if token else {}

    # Look at pull requests
    prs = get_pull_requests(owner, repo, headers)
    if not prs:
        end = time.time()
        latency = (end - start) * 1000
        return 0.0, latency

    total_lines = 0
    reviewed_lines = 0

    # Use ThreadPoolExecutor to fetch PR info concurrently
    with ThreadPoolExecutor(max_workers=15) as executor:
        # Map each PR to pr_info; returns results in the same order
        results = executor.map(lambda pr: pr_info(pr, owner, repo, headers), prs)
        for pr_lines, reviewed in results:
            total_lines += pr_lines
            if reviewed:
                reviewed_lines += pr_lines

    if total_lines == 0:
        end = time.time()
        latency = (end - start) * 1000
        return 0.0, latency

    end = time.time()
    latency = (end - start) * 1000
    reviewedness = round(reviewed_lines / total_lines, 2)
    return (reviewedness, int(latency))


if __name__ == "__main__":
    # code_url = "https://github.com/google-research/bert"  # example with 0
    code_url = "https://github.com/psf/requests"  # example with 1
    reviewedness, latency = reviewedness_score(code_url)
    print("Reviewedness score: ", reviewedness)
    print("Reviewedness latency: ", latency)
