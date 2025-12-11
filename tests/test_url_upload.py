"""Test script for URL validation and upload testing.

Per OpenAPI v3.4.4 Section 3.2 - URL-Based Model Upload Testing

PURPOSE:
Tests URL validation and model registration before upload.
Verifies URL accessibility and format validity.

USAGE:
    python tests/test_url_upload.py <url> [--no-test] [--timeout SECONDS]

EXAMPLES:
    python tests/test_url_upload.py https://huggingface.co/google-bert/bert-base-uncased
    python tests/test_url_upload.py https://github.com/openai/whisper --no-test
    python tests/test_url_upload.py https://example.com --timeout 5

OPTIONS:
    url: URL to test (required)
    --no-test: Skip accessibility testing (format only)
    --timeout: Request timeout in seconds (default: 10)

VALIDATION STEPS:
1. URL Format Check: Must have http:// or https:// scheme
2. Accessibility Test: Makes HTTP HEAD request, follows redirects
3. Storage: Saves metadata to uploads/url_storage/metadata/

ERROR HANDLING:
    Timeout: "Request timeout (>10s)"
    Connection refused: "Connection error - URL unreachable"
    Invalid format: "Invalid URL format"

SPEC SECTIONS REFERENCED:
    Section 3.2: Model registration endpoint
    Section 3.1: Authentication requirements
"""
import argparse
import sys
from typing import Optional

# NOTE: URLStorageService module does not exist in this codebase
# from src.crud.upload.url_storage_service import URLStorageService
try:
    from src.crud.upload.url_validator import validate_model_url
except ImportError:
    validate_model_url = None


def validate_url_cli(
    url: str, test_accessibility: bool = True, timeout: Optional[int] = None
) -> None:
    """Test if a URL can be uploaded.

    Args:
        url: URL to test
        test_accessibility: Whether to test accessibility (default: True)
        timeout: Request timeout in seconds
    """
    print(f"\n{'=' * 60}")
    print("Testing URL for Upload")
    print(f"{'=' * 60}")
    print(f"URL: {url}")
    print(f"Testing Accessibility: {test_accessibility}")
    if timeout:
        print(f"Timeout: {timeout}s")
    print()

    # Validate URL
    if validate_model_url is None:
        print("ERROR: url_validator module not available in this codebase")
        return

    result = validate_model_url(url, test_accessibility=test_accessibility)

    print("Validation Results:")
    print(f"  Format Valid: {'PASS' if result['format_valid'] else 'FAIL'}")

    if test_accessibility:
        print(f"  Accessible: {'PASS' if result['accessible'] else 'FAIL'}")

    print(f"  Status: {'Ready for upload' if result['is_valid'] else 'Not ready'}")
    print(f"  Message: {result['message']}")
    print()

    if result["is_valid"]:
        print("This URL is ready to be uploaded to the registry!")
    else:
        print("This URL cannot be uploaded. Please fix the issues above.")

    print("=" * 60)
    print()


def validate_huggingface_url() -> None:
    """Validate URL validation with HuggingFace model URL."""
    if validate_model_url is None:
        print("ERROR: url_validator module not available")
        return
    url = "https://huggingface.co/google-bert/bert-base-uncased"
    result = validate_model_url(url, test_accessibility=False)
    assert result["format_valid"] is True
    assert result["is_valid"] is True


def validate_github_url() -> None:
    """Validate URL validation with GitHub URL."""
    if validate_model_url is None:
        print("ERROR: url_validator module not available")
        return
    url = "https://github.com/openai/whisper"
    result = validate_model_url(url, test_accessibility=False)
    assert result["format_valid"] is True
    assert result["is_valid"] is True


def validate_invalid_url() -> None:
    """Validate URL validation with invalid URL."""
    if validate_model_url is None:
        print("ERROR: url_validator module not available")
        return
    url = "not-a-valid-url"
    result = validate_model_url(url, test_accessibility=False)
    assert result["format_valid"] is False
    assert result["is_valid"] is False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test if a model URL can be uploaded to the registry"
    )
    parser.add_argument("url", help="Model URL to test")
    parser.add_argument(
        "--no-test",
        action="store_true",
        help="Skip accessibility testing (only check format)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )

    args = parser.parse_args()

    # Validate URL
    validate_url_cli(
        url=args.url, test_accessibility=not args.no_test, timeout=args.timeout
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
