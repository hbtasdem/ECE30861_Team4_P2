"""
Bus Factor Score Calculator for HuggingFace Models.

This module calculates the bus factor (number of unique contributors)
for HuggingFace models using the official HuggingFace Hub API.
"""

import time
from typing import Tuple

try:
    from huggingface_hub import HfApi, list_repo_commits
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    print("Warning: huggingface_hub not installed. Install with: pip install huggingface-hub")

# Fallback to web scraping if huggingface_hub is not available
import re
import requests


def get_huggingface_contributors_api(model_id: str) -> int:
    """
    Get the number of contributors using the official HuggingFace Hub library.
    This is the preferred method as it's more reliable.

    Args:
        model_id: The Hugging Face model ID (e.g., "bert-base-uncased")

    Returns:
        int: Number of unique contributors
    """
    try:
        api = HfApi()
        
        # Get all commits for the model repository
        commits = list(list_repo_commits(model_id, repo_type="model"))
        
        # Extract unique authors from commits
        authors = set()
        for commit in commits:
            # Try different ways to get author info
            if hasattr(commit, 'authors') and commit.authors:
                authors.update(commit.authors)
            elif hasattr(commit, 'author') and commit.author:
                authors.add(commit.author)
            # Some commits might have commit_info with author data
            elif hasattr(commit, 'commit_info'):
                author = getattr(commit.commit_info, 'author', None)
                if author:
                    authors.add(author)
        
        contributor_count = len(authors)
        if contributor_count > 0:
            return contributor_count
        
        # If we got no authors from commits, return 0
        return 0

    except Exception as e:
        print(f"API Error getting contributors for {model_id}: {e}")
        return 0


def get_huggingface_contributors_scrape(model_id: str, max_retries: int = 3) -> int:
    """
    Fallback method: Get contributors by scraping HuggingFace page.
    Used only if the API method fails or huggingface_hub is not installed.

    Args:
        model_id: The Hugging Face model ID
        max_retries: Maximum number of retry attempts

    Returns:
        int: Number of contributors
    """
    for attempt in range(max_retries):
        try:
            # Add headers to look like a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            files_url = f"https://huggingface.co/{model_id}/tree/main"
            response = requests.get(
                files_url, 
                headers=headers, 
                timeout=15,
                allow_redirects=True
            )

            if response.status_code == 200:
                content = response.text

                # Try multiple regex patterns to find contributor count
                contributor_patterns = [
                    r"(\d+)\s+contributors?",  # "5 contributors"
                    r"contributors?\s*[:=]\s*(\d+)",  # "contributors: 5"
                    r'"contributors?":\s*(\d+)',  # JSON-like "contributors": 5
                    r'data-contributors="(\d+)"',  # HTML attribute
                    r'contributors.*?(\d+)',  # Loose match
                ]

                for pattern in contributor_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            try:
                                count = int(match)
                                # Sanity check: reasonable contributor count
                                if 0 < count < 10000:
                                    return count
                            except ValueError:
                                continue

                # Got a 200 response but no match found
                # This might mean the content is JavaScript-rendered
                # or the model has 0 contributors
                return 0
                
            elif response.status_code == 404:
                # Model doesn't exist
                return 0
            else:
                # Other HTTP error
                pass

        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.RequestException:
            pass
        except Exception:
            pass

        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)

    # Failed after all retries
    return 0


def get_huggingface_contributors(model_id: str) -> int:
    """
    Get the number of contributors for a HuggingFace model.
    
    Tries API method first (more reliable), falls back to scraping if needed.

    Args:
        model_id: The Hugging Face model ID (e.g., "bert-base-uncased")

    Returns:
        int: Number of unique contributors (0 if unable to determine)
    """
    # Try API method first if available
    if HF_HUB_AVAILABLE:
        try:
            count = get_huggingface_contributors_api(model_id)
            if count > 0:
                return count
        except Exception:
            # Fall through to scraping method
            pass
    
    # Fallback to scraping
    return get_huggingface_contributors_scrape(model_id)


def bus_factor_score(model_id: str) -> Tuple[int, float]:
    """
    Calculate the bus factor score based on the number of unique contributors
    to a Hugging Face model.

    The bus factor represents how many people would need to leave the project
    before it becomes unmaintainable. A higher number indicates better distribution
    of knowledge and lower project risk.

    Args:
        model_id: The Hugging Face model ID
                 (e.g., "moonshotai/Kimi-K2-Instruct-0905")

    Returns:
        tuple[int, float]: (Number of unique contributors, execution time in seconds)
        
    Examples:
        >>> contributors, latency = bus_factor_score("bert-base-uncased")
        >>> print(f"Contributors: {contributors}, Time: {latency:.3f}s")
        Contributors: 14, Time: 0.523s
    """
    start_time = time.time()
    
    try:
        contributors = get_huggingface_contributors(model_id)
    except Exception as e:
        print(f"Error calculating bus factor for {model_id}: {e}")
        contributors = 0
    
    end_time = time.time()
    execution_time = end_time - start_time

    return contributors, execution_time


# Test the function
if __name__ == "__main__":
    print("Testing bus factor calculation...")
    print("=" * 60)
    
    test_models = [
        "moonshotai/Kimi-K2-Instruct-0905",
        "microsoft/CodeBERT-base",
        "bert-base-uncased",
        "microsoft/DialoGPT-medium",
    ]
    
    for model_id in test_models:
        print(f"\nTesting: {model_id}")
        
        start_time = time.time()
        result = bus_factor_score(model_id)
        end_time = time.time()
        
        contributors, internal_latency = result
        total_time = end_time - start_time
        
        print(f"  Contributors: {contributors}")
        print(f"  Internal latency: {internal_latency:.3f}s")
        print(f"  Total time: {total_time:.3f}s")
    
    print("\n" + "=" * 60)
    print("Testing complete!")