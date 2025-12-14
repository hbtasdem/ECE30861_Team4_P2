import os
import re
import time
from typing import Optional

import requests

# Define which licenses are compatible with LGPL v2.1
# This list is from two websites:
# https://huggingface.co/docs/hub/en/repositories-licenses for the codes
# https://www.gnu.org/licenses/license-list.html for compatibility
COMPATIBLE_LICENSES = {
    "gpl-2.0",
    "gpl-3.0",
    "lgpl-2.1",
    "lgpl-3.0",
    "artistic-2.0",
    "mit",
    "bsl-1.0",
    "bsd-3-clause",
    "bsd-2-clause",
    "bsd",
    "cc0-1.0",
    "cc-by-4.0",
    "cc-by-3.0",
    "cc-by-sa-4.0",
    "wtfpl",
    "isc",
    "ncsa",
    "unlicense",
    "zlib",
    "apache-2.0",
    "apache-1.1",
    "mpl-2.0",
    "openrail",
    "bigscience-openrail-m",
    "bigscience-bloom-rail-1.0",
    "llama2",
    "llama3",
    "llama3.1",
    "llama3.2",
    "gemma",
}

# Common permissive license indicators
PERMISSIVE_INDICATORS = [
    "open source",
    "permissive",
    "free to use",
    "freely available",
    "no restrictions",
    "public domain",
    "open access",
    "unrestricted",
]


def fetch_readme(model_id: str) -> Optional[str]:
    """
    Fetch the README.md text from a Hugging Face model repository. Uses the
    model ID (e.g., "baidu/ERNIE-4.5-21B-A3B-Thinking").
    """
    # Construct raw README URL from model ID
    raw_url = f"https://huggingface.co/{model_id}/resolve/main/README.md"
    try:
        response = requests.get(raw_url, timeout=10)
        response.raise_for_status()
        return str(response.text)
    except Exception as e:
        if int(os.getenv("LOG_LEVEL", "0")) > 0:
            print(f"[ERROR] Failed to fetch README: {e}")
        return None


def extract_license(readme_text: str) -> Optional[str]:
    """
    Extract license information from a Hugging Face README.md file.
    Handles both YAML front matter and '## License' sections.
    """
    # Case 1: YAML front matter
    yaml_match = re.search(
        r"^---[\s\S]*?license:\s*([^\n]+)", readme_text, re.IGNORECASE | re.MULTILINE
    )
    if yaml_match:
        return yaml_match.group(1).strip().lower()

    # Case 2: Markdown heading '## License'
    lines = readme_text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^#+\s*License\s*$", line.strip(), re.IGNORECASE):
            # Look for license info in next few lines
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip():
                    return lines[j].strip().lower()

    return None


def check_license_mentions(readme_text: str) -> bool:
    """Check if README has any license-related mentions."""
    readme_lower = readme_text.lower()
    license_keywords = [
        "license",
        "licence",
        "licensed under",
        "terms of use",
        "usage terms",
        "copyright",
        "legal",
        "permissions",
    ]
    return any(keyword in readme_lower for keyword in license_keywords)


def check_permissive_language(readme_text: str) -> bool:
    """Check if README suggests permissive usage."""
    readme_lower = readme_text.lower()
    return any(indicator in readme_lower for indicator in PERMISSIVE_INDICATORS)


def license_sub_score(model_id: str) -> tuple[float, float]:
    """
    Calculate license sub-score with granular scoring:
    - 1.0: Compatible license found
    - 0.7: Unrecognized but specific license mentioned
    - 0.5: License section exists or permissive language found
    - 0.3: Any license-related mention
    - 0.0: No license information

    Input: model_id (e.g., "baidu/ERNIE-4.5-21B-A3B-Thinking")
    Returns: (score, elapsed_time)
    """
    start_time = time.time()
    readme = fetch_readme(model_id)

    if not readme:
        end_time = time.time()
        return (0.0, end_time - start_time)

    # Try to extract specific license
    license_str = extract_license(readme)

    if license_str:
        # Normalize the license string
        normalized = (
            license_str.lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
            .replace("license", "")
            .replace("v", "")
            .replace(".", "")
        )

        # Check if it matches a compatible license
        for comp in COMPATIBLE_LICENSES:
            comp_normalized = comp.replace("-", "").replace("_", "").replace(".", "")
            if comp_normalized in normalized or normalized in comp_normalized:
                end_time = time.time()
                return (1.0, end_time - start_time)

        # Specific license found but not in our list - still good!
        # This means they documented it clearly
        if len(license_str) > 2:  # Not just a letter/number
            end_time = time.time()
            return (0.7, end_time - start_time)

    # Check for permissive language (common in AI models)
    if check_permissive_language(readme):
        end_time = time.time()
        return (0.5, end_time - start_time)

    # Check for any license mention at all
    if check_license_mentions(readme):
        end_time = time.time()
        return (0.3, end_time - start_time)

    # No license information found
    end_time = time.time()
    return (0.0, end_time - start_time)


if __name__ == "__main__":
    model_id = "baidu/ERNIE-4.5-21B-A3B-Thinking"
    score, elapsed = license_sub_score(model_id)
    print(f"License score: {score} (elapsed: {elapsed:.3f}s)")
