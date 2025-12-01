# phase 2 license check
import json
from enum import Enum
from typing import Dict, Tuple

import boto3
import httpx

BUCKET_NAME = "phase2-s3-bucket"


class LicenseCategory(Enum):
    """License categories based on permissiveness"""
    PERMISSIVE = 1  # MIT, Apache-2.0, BSD
    WEAK_COPYLEFT = 2  # LGPL, MPL
    STRONG_COPYLEFT = 3  # GPL, AGPL
    RESTRICTED = 4  # CC-BY-NC, proprietary
    RAIL = 5  # Responsible AI Licenses (OpenRAIL, etc.)
    UNKNOWN = 6


# License compatibility matrix for fine-tuning + inference
# Based on ModelGo paper findings
LICENSE_COMPATIBILITY: Dict[Tuple[LicenseCategory, LicenseCategory], bool] = {
    # Format: (code_license, model_license) -> is_compatible
    (LicenseCategory.PERMISSIVE, LicenseCategory.PERMISSIVE): True,
    (LicenseCategory.PERMISSIVE, LicenseCategory.WEAK_COPYLEFT): True,
    (LicenseCategory.PERMISSIVE, LicenseCategory.STRONG_COPYLEFT): True,
    (LicenseCategory.PERMISSIVE, LicenseCategory.RESTRICTED): True,
    (LicenseCategory.PERMISSIVE, LicenseCategory.RAIL): True,

    (LicenseCategory.WEAK_COPYLEFT, LicenseCategory.PERMISSIVE): True,
    (LicenseCategory.WEAK_COPYLEFT, LicenseCategory.WEAK_COPYLEFT): True,
    (LicenseCategory.WEAK_COPYLEFT, LicenseCategory.STRONG_COPYLEFT): False,
    (LicenseCategory.WEAK_COPYLEFT, LicenseCategory.RESTRICTED): True,
    (LicenseCategory.WEAK_COPYLEFT, LicenseCategory.RAIL): False,

    (LicenseCategory.STRONG_COPYLEFT, LicenseCategory.PERMISSIVE): True,
    (LicenseCategory.STRONG_COPYLEFT, LicenseCategory.WEAK_COPYLEFT): False,
    (LicenseCategory.STRONG_COPYLEFT, LicenseCategory.STRONG_COPYLEFT): True,
    (LicenseCategory.STRONG_COPYLEFT, LicenseCategory.RESTRICTED): False,
    (LicenseCategory.STRONG_COPYLEFT, LicenseCategory.RAIL): False,

    (LicenseCategory.RESTRICTED, LicenseCategory.PERMISSIVE): False,
    (LicenseCategory.RESTRICTED, LicenseCategory.WEAK_COPYLEFT): False,
    (LicenseCategory.RESTRICTED, LicenseCategory.STRONG_COPYLEFT): False,
    (LicenseCategory.RESTRICTED, LicenseCategory.RESTRICTED): True,
    (LicenseCategory.RESTRICTED, LicenseCategory.RAIL): False,

    (LicenseCategory.RAIL, LicenseCategory.PERMISSIVE): True,
    (LicenseCategory.RAIL, LicenseCategory.WEAK_COPYLEFT): False,
    (LicenseCategory.RAIL, LicenseCategory.STRONG_COPYLEFT): False,
    (LicenseCategory.RAIL, LicenseCategory.RESTRICTED): False,
    (LicenseCategory.RAIL, LicenseCategory.RAIL): True,
}


def categorize_license(license_name: str) -> LicenseCategory:
    """
    Categorize a license string into a LicenseCategory.

    Parameters
    ----------
    license_name: str The license identifier (e.g., "MIT", "apache-2.0", "gpl-3.0")

    Returns
    -------
    LicenseCategory The category of the license
    """
    license_lower = license_name.lower().strip()

    # Permissive licenses
    if any(x in license_lower for x in ["mit", "apache", "bsd", "isc", "unlicense"]):
        return LicenseCategory.PERMISSIVE

    # Weak copyleft
    if any(x in license_lower for x in ["lgpl", "mpl", "epl", "cpl"]):
        return LicenseCategory.WEAK_COPYLEFT

    # Strong copyleft
    if any(x in license_lower for x in ["gpl", "agpl"]):
        return LicenseCategory.STRONG_COPYLEFT

    # Restricted (non-commercial, no-derivatives)
    if any(x in license_lower for x in ["cc-by-nc", "cc-by-nd", "proprietary", "custom"]):
        return LicenseCategory.RESTRICTED

    # Responsible AI Licenses
    if any(x in license_lower for x in ["openrail", "rail", "llama", "bloom"]):
        return LicenseCategory.RAIL

    return LicenseCategory.UNKNOWN


def check_compatibility(github_license: str, model_license: str) -> bool:
    """
    Check if github code and hf model have compatible license for "fine-tune + inference/generation"

    Parameters
    ----------
    github_license: str
    model_license: str

    Returns
    -------
    Boolean if github license is compatible with model license
    """
    # gave claude Sonnet 4.5 the paper and it got the categories and compatabilities from that
    code_cat = categorize_license(github_license)
    model_cat = categorize_license(model_license)

    # Fail on unknown licenses
    if code_cat == LicenseCategory.UNKNOWN or model_cat == LicenseCategory.UNKNOWN:
        return False

    # Check compatibility matrix
    compatibility_key = (code_cat, model_cat)
    is_compatible = LICENSE_COMPATIBILITY.get(compatibility_key, False)
    return is_compatible


def get_model_license(model_url: str) -> str:
    """
    Fetch the license from a hugging face model.

    Parameters
    ----------
    model_url: str HF model URL

    Returns
    -------
    str License identifier or "" if not found
    """
    try:
        # Extract model_id from HF URL
        # Example: https://huggingface.co/bert-base-uncased
        model_id = model_url.split("huggingface.co/")[-1].strip("/")

        # Use HF API to get model info
        api_url = f"https://huggingface.co/api/models/{model_id}"

        with httpx.Client(timeout=10.0) as client:
            response = client.get(api_url)
            response.raise_for_status()

            data = response.json()

            # Try to get license from cardData or model info
            card_data = data.get("cardData", {})
            license_info = card_data.get("license")

            if license_info:
                return str(license_info)

            # Fallback: check tags for license info
            tags = data.get("tags", [])
            for tag in tags:
                if "license:" in tag:
                    return tag.replace("license:", "").strip()

            return ""

    except Exception:
        return ""


def get_github_license(github_url: str) -> str:
    """
    Fetch the license from a GitHub repository.

    Parameters
    ----------
    github_url: str GitHub repository URL

    Returns
    -------
    str License identifier or "" if not found
    """
    try:
        # Extract owner and repo from URL
        parts = github_url.rstrip("/").split("/")
        if len(parts) < 2:
            return ""
        owner, repo = parts[-2], parts[-1]

        # Use GitHub API to get license
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        with httpx.Client(timeout=10.0) as client:
            response = client.get(api_url)
            response.raise_for_status()

            data = response.json()
            license_info = data.get("license")

            if license_info and isinstance(license_info, dict):
                return license_info.get("spdx_id") or license_info.get("key")

            return ""

    except Exception:
        return None


def license_check(github_url: str, artifact_id) -> bool:
    """
    Check if github code and hf model have compatible license for "fine-tune + inference/generation"

    Parameters
    ----------
    github_url: str from user request body
    artifact_id: str model artifact id

    Returns
    -------
    Boolean if github license is compatible with model license
    """
    s3_client = boto3.client("s3")
    key = f"model/{artifact_id}.json"

    try:
        # get url from artifact
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        model_artifact = obj["Body"].read().decode("utf-8")
        artifact_data = json.loads(model_artifact)
        model_url = artifact_data["data"]["url"]

        # get licenses
        github_license = get_github_license(github_url)
        model_license = get_model_license(model_url)

        if not github_license or not model_license:
            return False

        # check compatability
        return check_compatibility(github_license, model_license)

    except Exception:
        return False
