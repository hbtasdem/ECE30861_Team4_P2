# NOTE FROM GEORGIA: this doesn't test anything. Test isn't in the function names so pytest doesn't see them.
# There's errors with them, so phase1 team probably just took out "test" to ignore it?
import os
import re
import sys
import time
from typing import Optional, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src/metrics"))
from license_score import fetch_readme  # noqa: E402


def _get_ai_score(readme_text: str, model_id: str, aspect: str) -> float:
    """
    Get AI score for a specific aspect of dataset quality.

    Args:
        readme_text: README content
        model_id: Model identifier
        aspect: What to assess ('documentation', 'safety', or 'curation')

    Returns:
        float: Score between 0.0 and 1.0, or 0.0 if AI unavailable
    """
    try:
        import purdue_api

        PurdueGenAI = purdue_api.PurdueGenAI

        # Create prompts for different aspects
        prompts = {
            "documentation": f"""
Analyze the documentation quality of this ML model README for "{model_id}".
Rate 0.0-1.0 based on: dataset description, size/format info, usage
instructions, technical details.
README: {readme_text[:1500]}{'...' if len(readme_text) > 1500 else ''}
Respond with only a number (e.g., 0.75):""",
            "safety": f"""
Analyze safety/privacy considerations in this ML model README for
"{model_id}".
Rate 0.0-1.0 based on: privacy mentions, bias discussions, safety
warnings, ethical considerations.
README: {readme_text[:1500]}{'...' if len(readme_text) > 1500 else ''}
Respond with only a number (e.g., 0.65):""",
            "curation": f"""
Analyze curation/quality control in this ML model README for
"{model_id}".
Rate 0.0-1.0 based on: quality processes, validation methods,
performance metrics, standards.
README: {readme_text[:1500]}{'...' if len(readme_text) > 1500 else ''}
Respond with only a number (e.g., 0.80):""",
        }

        if aspect not in prompts:
            return 0.0

        # Make AI call
        client = PurdueGenAI()
        response = client.chat(prompts[aspect])

        # Extract score from response
        import re

        match = re.search(r"(\d+\.?\d*)", response.strip())
        if match:
            score = float(match.group(1))
            return min(1.0, max(0.0, score))
        return 0.0
    except Exception:
        # AI unavailable or failed, return 0.0
        return 0.0


def evaluate_dataset_documentation(readme_text: Optional[str]) -> float:
    """
    Evaluate dataset documentation quality based on README content.

    Args:
        readme_text: The README content as string

    Returns:
        float: Score between 0.0 and 1.0 for documentation quality
    """
    if not readme_text:
        return 0.0

    score = 0.0
    readme_lower = readme_text.lower()

    # Check for dataset description (0.2 points) - more specific with
    # word boundaries
    dataset_patterns = [
        r"\bdataset\b",
        r"\btraining data\b",
        r"\btraining set\b",
        r"\bdata set\b",
        r"\bcorpus\b",
        r"\bcollection\b",
        r"\bspecification\b",
    ]

    for pattern in dataset_patterns:
        if re.search(pattern, readme_lower):
            score += 0.2
            break

    # Check for size information (0.2 points) - enhanced patterns
    size_patterns = [
        r"\d+\s*(gb|mb|kb|tb)",
        r"\d+\s*(gigabytes?|megabytes?|kilobytes?|terabytes?)",
        r"\d+\s*rows?",
        r"\d+\s*samples?",
        r"\d+\s*examples?",
        r"\d+\s*instances?",
        r"\d+\s*records?",
        r"size[:\s]+\d+",
        r"contains?\s+\d+",
    ]

    for pattern in size_patterns:
        if re.search(pattern, readme_text, re.IGNORECASE):
            score += 0.2
            break

    # Check for format information (0.2 points) - more comprehensive
    format_keywords = [
        "csv",
        "json",
        "jsonl",
        "parquet",
        "tsv",
        "txt",
        "hdf5",
        "feather",
        "format",
        "structure",
        "file format",
        "data format",
    ]
    if any(keyword in readme_lower for keyword in format_keywords):
        score += 0.2

    # Check for column/field descriptions (0.2 points) - with word boundaries
    schema_patterns = [
        r"\bcolumn\b",
        r"\bfield\b",
        r"\battribute\b",
        r"\bfeature\b",
        r"\bschema\b",
        r"\bmetadata\b",
        r"\bannotation\b",
        r"\blabel\b",
    ]

    for pattern in schema_patterns:
        if re.search(pattern, readme_lower):
            score += 0.2
            break

    # Check for usage instructions (0.2 points) - more comprehensive
    usage_keywords = [
        "usage",
        "how to",
        "load",
        "download",
        "access",
        "install",
        "tutorial",
        "guide",
        "example",
        "quickstart",
        "getting started",
    ]
    if any(keyword in readme_lower for keyword in usage_keywords):
        score += 0.2

    return min(1.0, score)


def evaluate_license_clarity(readme_text: Optional[str]) -> float:
    """
    Evaluate license clarity for the dataset (different from license
    compatibility).

    Args:
        readme_text: The README content as string

    Returns:
        float: Score between 0.0 and 1.0 for license clarity
    """
    if not readme_text:
        return 0.0

    score = 0.0
    readme_lower = readme_text.lower()

    # Check for explicit license mention (0.5 points) - more comprehensive
    license_keywords = [
        "license",
        "licence",
        "terms",
        "agreement",
        "permission",
        "copyright",
        "legal",
        "rights",
        "usage rights",
    ]
    if any(keyword in readme_lower for keyword in license_keywords):
        score += 0.5

    # Check for specific license types (0.3 points) - more comprehensive
    specific_licenses = [
        "mit",
        "apache",
        "gpl",
        "lgpl",
        "bsd",
        "cc0",
        "cc-by",
        "public domain",
        "open source",
        "free to use",
        "commercial use",
        "academic use",
        "creative commons",
        "attribution",
        "redistribution",
    ]

    for license_type in specific_licenses:
        if license_type in readme_lower:
            score += 0.3
            break

    # Check for usage restrictions (0.2 points) - more comprehensive
    restriction_keywords = [
        "restriction",
        "limitation",
        "prohibited",
        "not allowed",
        "forbidden",
        "cannot",
        "must not",
        "restricted use",
    ]
    if any(keyword in readme_lower for keyword in restriction_keywords):
        score += 0.2

    return min(1.0, score)


def evaluate_safety_privacy(readme_text: Optional[str]) -> float:
    """
    Evaluate safety and privacy considerations mentioned in the dataset.

    Args:
        readme_text: The README content as string

    Returns:
        float: Score between 0.0 and 1.0 for safety/privacy considerations
    """
    if not readme_text:
        return 0.0

    score = 0.0
    readme_lower = readme_text.lower()

    # Check for privacy considerations (0.4 points) - more comprehensive
    privacy_keywords = [
        "privacy",
        "personal",
        "pii",
        "anonymized",
        "anonymised",
        "de-identified",
        "confidential",
        "sensitive",
        "data protection",
        "gdpr",
        "ccpa",
        "personal information",
        "private data",
        "data privacy",
    ]

    if any(keyword in readme_lower for keyword in privacy_keywords):
        score += 0.4

    # Check for safety considerations (0.3 points) - more comprehensive
    safety_keywords = [
        "safety",
        "bias",
        "fairness",
        "ethical",
        "responsible",
        "harmful",
        "content warning",
        "disclaimer",
        "risks",
        "limitations",
        "toxicity",
        "hate speech",
        "inappropriate",
        "offensive content",
        "safety guidelines",
        "ethical considerations",
    ]

    if any(keyword in readme_lower for keyword in safety_keywords):
        score += 0.3

    # Check for data source information (0.3 points) - more comprehensive
    source_keywords = [
        "source",
        "origin",
        "collected",
        "gathered",
        "obtained",
        "derived",
        "data source",
        "origin of data",
        "data collection",
        "data gathering",
    ]
    if any(keyword in readme_lower for keyword in source_keywords):
        score += 0.3

    return min(1.0, score)


def evaluate_curation_quality(readme_text: Optional[str]) -> float:
    """
    Evaluate curation and quality control measures mentioned.

    Args:
        readme_text: The README content as string

    Returns:
        float: Score between 0.0 and 1.0 for curation quality
    """
    if not readme_text:
        return 0.0

    score = 0.0
    readme_lower = readme_text.lower()

    # Check for quality control measures (0.4 points) - with word boundaries
    quality_patterns = [
        r"\bquality\b",
        r"\bcurated\b",
        r"\bverified\b",
        r"\bvalidated\b",
        r"\bchecked\b",
        r"\breviewed\b",
        r"\bfiltered\b",
        r"\bcleaned\b",
        r"\bprocessed\b",
        r"\bpreprocessed\b",
        r"\bstandardized\b",
        r"\bnormalized\b",
    ]

    for pattern in quality_patterns:
        if re.search(pattern, readme_lower):
            score += 0.4
            break

    # Check for version information (0.3 points) - more comprehensive
    version_keywords = [
        "version",
        "v1",
        "v2",
        "v3",
        "update",
        "changelog",
        "release",
        "revision",
        "iteration",
        "edition",
        "dataset version",
    ]
    if any(keyword in readme_lower for keyword in version_keywords):
        score += 0.3

    # Check for statistics or metrics (0.3 points) - more comprehensive
    stats_keywords = [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "bleu",
        "rouge",
        "metric",
        "statistic",
        "benchmark",
        "baseline",
        "performance",
        "evaluation",
        "assessment",
        "measurement",
    ]
    if any(keyword in readme_lower for keyword in stats_keywords):
        score += 0.3

    return min(1.0, score)


def evaluate_reproducibility(readme_text: Optional[str]) -> float:
    """
    Evaluate reproducibility aspects of the dataset.

    Args:
        readme_text: The README content as string

    Returns:
        float: Score between 0.0 and 1.0 for reproducibility
    """
    if not readme_text:
        return 0.0

    score = 0.0
    readme_lower = readme_text.lower()

    # Check for code availability (0.3 points) - more comprehensive
    code_keywords = [
        "code",
        "github",
        "repository",
        "script",
        "notebook",
        "jupyter",
        "source code",
        "implementation",
        "codebase",
        "repository",
    ]
    if any(keyword in readme_lower for keyword in code_keywords):
        score += 0.3

    # Check for environment setup (0.3 points) - more comprehensive
    env_keywords = [
        "environment",
        "requirements",
        "dependencies",
        "install",
        "setup",
        "docker",
        "conda",
        "pip",
        "package",
        "library",
        "framework",
        "configuration",
    ]
    if any(keyword in readme_lower for keyword in env_keywords):
        score += 0.3

    # Check for reproducibility instructions (0.4 points) - more comprehensive
    repro_keywords = [
        "reproduce",
        "reproducibility",
        "replicate",
        "replication",
        "recreate",
        "step by step",
        "instructions",
        "tutorial",
        "guide",
        "experiment",
        "reproduce results",
        "replication study",
    ]

    if any(keyword in readme_lower for keyword in repro_keywords):
        score += 0.4

    return min(1.0, score)


def extract_dataset_identifier(dataset_link: str) -> str:
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


def check_readme_for_known_datasets(
    readme: str, encountered_datasets: set[str]
) -> bool:
    """Check if README mentions any previously encountered datasets."""
    if not readme or not encountered_datasets:
        return False

    readme_lower = readme.lower()

    for dataset_id in encountered_datasets:
        # Check for various forms of the dataset identifier
        dataset_lower = dataset_id.lower()

        # Direct mention
        if dataset_lower in readme_lower:
            return True

        # Check for parts of the dataset name
        dataset_parts = (
            dataset_lower.replace("/", " ").replace("-", " ").replace("_", " ").split()
        )
        if len(dataset_parts) >= 2:
            # Check if multiple parts are mentioned
            parts_found = sum(
                1 for part in dataset_parts if len(part) > 3 and part in readme_lower
            )
            if parts_found >= 2:
                return True

    return False


def evaluate_dataset_documentation_hybrid(
    readme_text: Optional[str], model_id: str, use_ai: bool = True
) -> float:
    """
    Hybrid evaluation of dataset documentation quality using deterministic +
    AI scoring.

    Args:
        readme_text: The README content as string
        model_id: Model identifier for AI context
        use_ai: Whether to use AI enhancement

    Returns:
        float: Score between 0.0 and 1.0 for documentation quality
    """
    # Get deterministic score
    deterministic_score = evaluate_dataset_documentation(readme_text)

    # If no AI requested or no text, return deterministic score
    if not use_ai or not readme_text:
        return deterministic_score

    # Get AI score
    ai_score = _get_ai_score(readme_text, model_id, "documentation")

    # If AI failed (returned 0.0), use deterministic only
    if ai_score == 0.0:
        return deterministic_score

    # Weighted combination: 70% deterministic (reliable baseline),
    # 30% AI (enhanced understanding)
    hybrid_score = (deterministic_score * 0.7) + (ai_score * 0.3)
    return min(1.0, hybrid_score)


def evaluate_safety_privacy_hybrid(
    readme_text: Optional[str], model_id: str, use_ai: bool = True
) -> float:
    """
    Hybrid evaluation of safety and privacy considerations using
    deterministic + AI scoring.

    Args:
        readme_text: The README content as string
        model_id: Model identifier for AI context
        use_ai: Whether to use AI enhancement

    Returns:
        float: Score between 0.0 and 1.0 for safety/privacy considerations
    """
    # Get deterministic score
    deterministic_score = evaluate_safety_privacy(readme_text)

    # If no AI requested or no text, return deterministic score
    if not use_ai or not readme_text:
        return deterministic_score

    # Get AI score
    ai_score = _get_ai_score(readme_text, model_id, "safety")

    # If AI failed (returned 0.0), use deterministic only
    if ai_score == 0.0:
        return deterministic_score

    # Weighted combination: 60% deterministic, 40% AI
    # (AI is better at nuanced safety assessment)
    hybrid_score = (deterministic_score * 0.6) + (ai_score * 0.4)
    return min(1.0, hybrid_score)


def evaluate_curation_quality_hybrid(
    readme_text: Optional[str], model_id: str, use_ai: bool = True
) -> float:
    """
    Hybrid evaluation of curation and quality control measures using
    deterministic + AI scoring.

    Args:
        readme_text: The README content as string
        model_id: Model identifier for AI context
        use_ai: Whether to use AI enhancement

    Returns:
        float: Score between 0.0 and 1.0 for curation quality
    """
    # Get deterministic score
    deterministic_score = evaluate_curation_quality(readme_text)

    # If no AI requested or no text, return deterministic score
    if not use_ai or not readme_text:
        return deterministic_score

    # Get AI score
    ai_score = _get_ai_score(readme_text, model_id, "curation")

    # If AI failed (returned 0.0), use deterministic only
    if ai_score == 0.0:
        return deterministic_score

    # Weighted combination: 65% deterministic, 35% AI
    # (AI can better assess quality descriptions)
    hybrid_score = (deterministic_score * 0.65) + (ai_score * 0.35)
    return min(1.0, hybrid_score)


def dataset_quality_sub_score(
    model_id: str,
    dataset_link: str = "",
    encountered_datasets: Optional[Set[str]] = None,
    use_ai: bool = True,
) -> Tuple[float, float]:
    """
    Calculate dataset quality sub-score based on README analysis with
    optional AI enhancement.

    Evaluates the 5 criteria from the dataset quality requirements:
    - Documentation of the dataset (0.2 weight) - AI-enhanced if available
    - Clarity of the license (0.2 weight) - deterministic only
    - Safety/privacy considerations (0.2 weight) - AI-enhanced if available
    - Curation/quality control measures (0.2 weight) - AI-enhanced if
      available
    - Reproducibility (0.2 weight) - deterministic only

    Args:
        model_id: The Hugging Face model ID
        dataset_link: External dataset link (optional)
        encountered_datasets: Set of previously encountered dataset IDs
        use_ai: Whether to use AI enhancement (default: True)

    Returns:
        Tuple[float, float]: (score, elapsed_time) where score is between
        0.0 and 1.0
    """
    start_time = time.time()

    if encountered_datasets is None:
        encountered_datasets = set()

    # Check if dataset is available (external link OR reference to earlier)
    has_external_dataset = bool(dataset_link and dataset_link.strip())
    dataset_available = has_external_dataset

    # If no external dataset link, check README for references to known
    # datasets
    if not has_external_dataset:
        readme = fetch_readme(model_id)
        if readme and encountered_datasets:
            # Check if README references any previously encountered datasets
            dataset_available = check_readme_for_known_datasets(
                readme, encountered_datasets
            )

    # If no dataset is available, return 0.0
    if not dataset_available:
        end_time = time.time()
        return (0.0, end_time - start_time)

    # Add external dataset to encountered set for future models
    if has_external_dataset:
        dataset_id = extract_dataset_identifier(dataset_link)
        if dataset_id:
            encountered_datasets.add(dataset_id)

    # Fetch README
    readme = fetch_readme(model_id)
    if not readme:
        end_time = time.time()
        return (0.0, end_time - start_time)

    # Calculate all 5 dataset quality scores
    # Use hybrid scoring for documentation, safety/privacy, and curation
    # Keep deterministic for license clarity and reproducibility
    # (regex works well for these)
    doc_score = evaluate_dataset_documentation_hybrid(readme, model_id, use_ai)
    license_score = evaluate_license_clarity(readme)  # Keep deterministic
    safety_score = evaluate_safety_privacy_hybrid(readme, model_id, use_ai)
    curation_score = evaluate_curation_quality_hybrid(readme, model_id, use_ai)
    repro_score = evaluate_reproducibility(readme)  # Keep deterministic

    # Equal weighted combination (0.2 each for the 5 criteria)
    final_score = (
        doc_score * 0.2
        + license_score * 0.2
        + safety_score * 0.2
        + curation_score * 0.2
        + repro_score * 0.2
    )
    final_score = round(final_score, 2)
    end_time = time.time()
    return (final_score, end_time - start_time)


if __name__ == "__main__":
    # Test with a sample model
    model_id = "google/gemma-2b"

    print("=" * 60)
    print("DATASET QUALITY SCORING TEST")
    print("=" * 60)
    print(f"Testing model: {model_id}")
    print()

    # Test deterministic scoring
    print("Deterministic scoring (regex-based):")
    score_det, elapsed_det = dataset_quality_sub_score(model_id, use_ai=False)
    print(f"  Score: {score_det:.3f}")
    print(f"  Time: {elapsed_det:.3f}s")
    print()

    # Test AI-enhanced scoring
    print("AI-enhanced hybrid scoring:")
    try:
        score_ai, elapsed_ai = dataset_quality_sub_score(model_id, use_ai=True)
        print(f"  Score: {score_ai:.3f}")
        print(f"  Time: {elapsed_ai:.3f}s")
        print(f"  Improvement: {score_ai - score_det:+.3f}")

        if score_ai > score_det:
            print("  AI enhancement improved the score")
        elif score_ai < score_det:
            print("  WARNING: AI enhancement lowered the score")
        else:
            print("  AI enhancement had no effect (likely AI unavailable)")

    except Exception as e:
        print(f"  AI enhancement failed: {e}")
        print("  Make sure GEN_AI_STUDIO_API_KEY is set in your environment")
