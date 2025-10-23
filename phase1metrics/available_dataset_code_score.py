import os
import re
import time
from typing import Tuple, Optional, Set

from license_sub_score import fetch_readme


def detect_dataset_links(readme_text: str) -> bool:
    """
    Detect if README contains dataset links or references.
    Looks for common dataset hosting platforms and file extensions.
    """
    if not readme_text:
        return False

    # Common dataset hosting platforms and patterns
    dataset_patterns = [
        r'https?://[^\s]*\.(csv|json|jsonl|parquet|tsv|txt|zip|tar\.gz|'
        r'tar\.bz2)',
        r'https?://[^\s]*(dataset|data)[^\s]*',
        r'https?://[^\s]*(kaggle|huggingface\.co/datasets|zenodo|figshare|'
        r'drive\.google\.com)',
        r'\[.*\]\([^)]*\.(csv|json|jsonl|parquet|tsv|txt|zip|tar\.gz|'
        r'tar\.bz2)',
        r'##?\s*Dataset',
        r'##?\s*Data',
        r'dataset[:\s]',
        r'training\s+data',
        r'test\s+data',
        r'validation\s+data',
    ]

    readme_lower = readme_text.lower()

    for pattern in dataset_patterns:
        if re.search(pattern, readme_lower, re.IGNORECASE):
            return True

    return False


def detect_code_examples(readme_text: str) -> bool:
    """
    Detect if README contains code examples or script references.
    Looks for code blocks, script files, and usage examples.
    """
    if not readme_text:
        return False

    # Patterns for code examples and scripts
    code_patterns = [
        r'```[a-zA-Z]*\n.*\n```',  # Code blocks
        r'```[a-zA-Z]*\n.*',       # Incomplete code blocks
        r'\.py\b',                  # Python files
        r'\.js\b',                  # JavaScript files
        r'\.java\b',                # Java files
        r'\.cpp\b',                 # C++ files
        r'\.c\b',                   # C files
        r'\.sh\b',                  # Shell scripts
        r'\.ipynb\b',               # Jupyter notebooks
        r'##?\s*Usage',
        r'##?\s*Example',
        r'##?\s*Code',
        r'##?\s*Installation',
        r'##?\s*Quick\s+start',
        r'pip\s+install',
        r'python\s+',
        r'import\s+',
        r'from\s+',
        r'def\s+',
        r'class\s+',
        r'function\s*\(',
        r'<code>',
        r'<pre>',
    ]

    readme_lower = readme_text.lower()

    for pattern in code_patterns:
        if re.search(pattern, readme_lower, re.IGNORECASE | re.MULTILINE):
            return True

    return False


def extract_code_identifier(code_link: str) -> str:
    """Extract a unique identifier from a code link."""
    if not code_link:
        return ""

    # Handle GitHub links
    if "github.com" in code_link:
        # Extract repo name from URL like
        # https://github.com/google-research/bert
        parts = code_link.split("github.com/")
        if len(parts) > 1:
            return parts[1].strip("/")

    # Handle other code links - use domain + path
    try:
        from urllib.parse import urlparse
        parsed = urlparse(code_link)
        return f"{parsed.netloc}{parsed.path}".strip("/")
    except Exception:
        return code_link.lower().strip()


def extract_dataset_identifier_code(dataset_link: str) -> str:
    """Extract a unique identifier from a dataset link."""
    if not dataset_link:
        return ""

    # Handle Hugging Face dataset links
    if "huggingface.co/datasets/" in dataset_link:
        # Extract dataset name from URL like
        # https://huggingface.co/datasets/bookcorpus/bookcorpus
        parts = dataset_link.split("/datasets/")
        if len(parts) > 1:
            return parts[1].strip("/")

    # Handle other dataset links - use domain + path
    try:
        from urllib.parse import urlparse
        parsed = urlparse(dataset_link)
        return f"{parsed.netloc}{parsed.path}".strip("/")
    except Exception:
        return dataset_link.lower().strip()


def check_readme_for_known_resources(readme: str,
                                     encountered_datasets: set[str],
                                     encountered_code: set[str]
                                     ) -> tuple[bool, bool]:
    """Check if README mentions previously encountered datasets or code."""
    if not readme:
        return False, False

    readme_lower = readme.lower()

    # Check for datasets
    has_known_dataset = False
    if encountered_datasets:
        for dataset_id in encountered_datasets:
            dataset_lower = dataset_id.lower()
            if dataset_lower in readme_lower:
                has_known_dataset = True
                break
            # Check for parts of the dataset name
            dataset_parts = dataset_lower.replace("/", " ").replace(
                "-", " ").replace("_", " ").split()
            if len(dataset_parts) >= 2:
                parts_found = sum(1 for part in dataset_parts
                                  if len(part) > 3 and part in readme_lower)
                if parts_found >= 2:
                    has_known_dataset = True
                    break

    # Check for code
    has_known_code = False
    if encountered_code:
        for code_id in encountered_code:
            code_lower = code_id.lower()
            if code_lower in readme_lower:
                has_known_code = True
                break
            # Check for parts of the code repo name
            code_parts = code_lower.replace("/", " ").replace(
                "-", " ").replace("_", " ").split()
            if len(code_parts) >= 2:
                parts_found = sum(1 for part in code_parts
                                  if len(part) > 3 and part in readme_lower)
                if parts_found >= 2:
                    has_known_code = True
                    break

    return has_known_dataset, has_known_code


def available_dataset_code_score(model_id: str, code_link: str = "",
                                 dataset_link: str = "",
                                 encountered_datasets: Optional[Set[str]] = None,
                                 encountered_code: Optional[Set[str]] = None
                                 ) -> Tuple[float, float]:
    """
    Calculate Available Dataset and Code Score.

    Uses external links when provided, checks for references to previously
    encountered datasets/code, or returns 0.
    Args:
        model_id: Hugging Face model ID (e.g., "tencent/SRPO")
        code_link: External GitHub/code repository link (optional)
        dataset_link: External dataset link (optional)
        encountered_datasets: Set of previously encountered dataset identifiers
        encountered_code: Set of previously encountered code identifiers

    Returns:
        Tuple of (score, execution_time)
    """
    start_time = time.time()

    if not model_id or not model_id.strip():
        end_time = time.time()
        return (0.0, end_time - start_time)

    if encountered_datasets is None:
        encountered_datasets = set()
    if encountered_code is None:
        encountered_code = set()

    # Check if dataset is available (external link OR reference to earlier)
    has_external_dataset = bool(dataset_link and dataset_link.strip())
    dataset_available = has_external_dataset

    # Check if code is available (external link OR reference to earlier)
    has_external_code = bool(code_link and code_link.strip())
    code_available = has_external_code

    # Initialize known references
    has_known_dataset = False
    has_known_code = False
    # If no external links, check README for references to known resources
    if not has_external_dataset or not has_external_code:
        readme_text = fetch_readme(model_id.strip())

        if readme_text:
            # First check for direct dataset/code links in README
            if not has_external_dataset:
                dataset_available = detect_dataset_links(readme_text)
            if not has_external_code:
                code_available = detect_code_examples(readme_text)
            # Also check for references to known resources
            has_known_dataset, has_known_code = (
                check_readme_for_known_resources(
                    readme_text, encountered_datasets, encountered_code))

            # Update availability based on references (if not already found)
            if not has_external_dataset and not dataset_available:
                dataset_available = has_known_dataset
            if not has_external_code and not code_available:
                code_available = has_known_code

    # Add external resources to tracking sets for future models
    if has_external_code:
        code_id = extract_code_identifier(code_link)
        if code_id:
            encountered_code.add(code_id)
    if has_external_dataset:
        dataset_id = extract_dataset_identifier_code(dataset_link)
        if dataset_id:
            encountered_datasets.add(dataset_id)

    # Calculate final score based on availability
    if dataset_available and code_available:
        score = 1.0  # Both available
    elif dataset_available or code_available:
        score = 0.5  # One available
    else:
        score = 0.0  # Neither available

    end_time = time.time()
    execution_time = end_time - start_time

    if int(os.getenv("LOG_LEVEL", "0")) > 0:
        print(f"[INFO] External links: code={has_external_code}, "
              f"dataset={has_external_dataset}")
        print(f"[INFO] Known references: dataset={has_known_dataset}, "
              f"code={has_known_code}, Score: {score}")

    return (score, execution_time)


if __name__ == "__main__":
    # Test with the example model
    model_id = "tencent/SRPO"
    score, exec_time = available_dataset_code_score(model_id)
    print(f"Model: {model_id}")
    print(f"Available Dataset and Code Score: {score}")
    print(f"Execution time: {exec_time:.3f}s")
