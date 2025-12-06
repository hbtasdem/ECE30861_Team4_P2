"""Monitoring program validation for artifact downloads.

FILE PURPOSE:
Implements download rejection if external monitoring program exits with code 0 and outputs to stdout.
Per requirement: reject model downloads if monitoring program returns 0 (success indicates "no go").

SPEC CONTEXT:
While not explicitly in OpenAPI 3.4.4, this implements security controls for model downloads.
When a user attempts to download a model, an optional monitoring program can be invoked:
- If it exits with code 0 and outputs to stdout: REJECT the download (security concern flagged)
- Otherwise: ALLOW the download

USAGE:
Monitoring program configured via environment variable:
- MODEL_MONITOR_SCRIPT: Path to executable script/program
- If not set, all downloads are allowed (default behavior)

Example environment setup:
    export MODEL_MONITOR_SCRIPT=/path/to/security_check.py
    # This script should:
    # - Exit with 0 if security concern found (result: download REJECTED)
    # - Exit with non-zero if OK (result: download ALLOWED)
    # - Output validation details to stdout
"""

import logging
import os
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def run_monitoring_program(artifact_id: str, artifact_type: str) -> Tuple[bool, str]:
    """Run external monitoring program to validate artifact download.

    Args:
        artifact_id: ID of artifact being downloaded
        artifact_type: Type of artifact (model, dataset, code)

    Returns:
        Tuple of (allow_download, output_message):
        - allow_download: True if download should proceed, False to reject
        - output_message: Output from monitoring program or reason for rejection

    Raises:
        Exception: If monitoring program cannot be executed
    """
    # Check if monitoring program is configured
    monitor_script = os.getenv("MODEL_MONITOR_SCRIPT")
    if not monitor_script:
        # No monitoring configured - allow all downloads
        return True, "No monitoring program configured"

    if not os.path.exists(monitor_script):
        logger.warning(f"Monitoring script not found: {monitor_script}")
        return True, f"Monitoring script not found: {monitor_script}"

    try:
        # Run monitoring program
        result = subprocess.run(
            [monitor_script, artifact_id, artifact_type],
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
        )

        stdout_output = result.stdout.strip()
        stderr_output = result.stderr.strip()

        logger.info(
            f"Monitoring program exit code: {result.returncode} for {artifact_type}/{artifact_id}"
        )
        if stdout_output:
            logger.info(f"Monitoring stdout: {stdout_output}")
        if stderr_output:
            logger.info(f"Monitoring stderr: {stderr_output}")

        # Exit code 0 means security concern found - REJECT download
        if result.returncode == 0:
            message = f"Download rejected by monitoring program. Output: {stdout_output}"
            logger.warning(
                f"Download REJECTED for {artifact_type}/{artifact_id}: {message}"
            )
            return False, message

        # Non-zero exit code means OK - ALLOW download
        message = (
            f"Download allowed by monitoring program. Output: {stdout_output}"
            if stdout_output
            else "Download allowed by monitoring program"
        )
        logger.info(f"Download ALLOWED for {artifact_type}/{artifact_id}")
        return True, message

    except subprocess.TimeoutExpired:
        logger.error(
            f"Monitoring program timeout for {artifact_type}/{artifact_id}"
        )
        return False, "Monitoring program timeout"

    except Exception as e:
        logger.error(f"Error running monitoring program: {e}")
        raise


def validate_download(artifact_id: str, artifact_type: str) -> Optional[str]:
    """Validate if artifact download should be allowed.

    Args:
        artifact_id: ID of artifact being downloaded
        artifact_type: Type of artifact (model, dataset, code)

    Returns:
        None if download is allowed
        Error message string if download should be rejected

    This function wraps run_monitoring_program and returns formatted error
    message suitable for HTTP responses.
    """
    try:
        allow_download, message = run_monitoring_program(artifact_id, artifact_type)
        if not allow_download:
            return message
        return None
    except Exception as e:
        logger.error(f"Unexpected error during download validation: {e}")
        # In case of unexpected errors, allow download by default
        # (errors in monitoring shouldn't block legitimate downloads)
        return None
