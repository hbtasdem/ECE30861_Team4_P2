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
    'gpl-2.0', 'gpl-3.0', 'lgpl-2.1', 'artistic-2.0', 'mit', 'bsl-1.0',
    'bsd-3-clause', 'cc0-1.0', 'cc-by-4.0', 'wtfpl', 'isc', 'ncsa',
    'unlicense', 'zlib', 'apache-2.0',
}


"""
Fetch the README.md text from a Hugging Face model repository. Uses the
model ID (e.g., "baidu/ERNIE-4.5-21B-A3B-Thinking").
"""


def fetch_readme(model_id: str) -> Optional[str]:
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


"""
Extract license information from a Hugging Face README.md file.
Handles both YAML front matter and '## License' sections.
"""


def extract_license(readme_text: str) -> Optional[str]:
    # Case 1: YAML front matter
    yaml_match = re.search(r"^---[\s\S]*?license:\s*([^\n]+)",
                           readme_text, re.IGNORECASE | re.MULTILINE)
    if yaml_match:
        return yaml_match.group(1).strip().lower()

    # Case 2: Markdown heading '## License'
    lines = readme_text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^#+\s*License\s*$", line.strip(), re.IGNORECASE):
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    return lines[j].strip().lower()

    return None


"""
Calculate license sub-score:
- 1 if license is present and compatible with LGPL v2.1
- 0 if not found or incompatible
Input: model_id (e.g., "baidu/ERNIE-4.5-21B-A3B-Thinking")
"""


def license_sub_score(model_id: str) -> tuple[int, float]:
    start_time = time.time()
    readme = fetch_readme(model_id)
    if not readme:
        end_time = time.time()
        return (0, end_time - start_time)

    license_str = extract_license(readme)
    if not license_str:
        end_time = time.time()
        return (0, end_time - start_time)

    # Normalize
    normalized = license_str.lower().replace(
        " ", "").replace("-", "").replace("license", "")

    for comp in COMPATIBLE_LICENSES:
        if comp.replace("-", "").replace(" ", "") in normalized:
            end_time = time.time()
            return (1, end_time - start_time)
    end_time = time.time()
    return (0, end_time - start_time)


if __name__ == "__main__":
    model_id = "baidu/ERNIE-4.5-21B-A3B-Thinking"
    print(license_sub_score(model_id))  # -> 1 if compatible, 0 otherwise
