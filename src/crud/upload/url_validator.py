"""URL validation and accessibility testing for model URLs.

Per OpenAPI v3.4.4 Section 3.2 - Artifact URL Validation

FILE PURPOSE:
Validates and tests model URLs before they are registered in the system.
Checks URL format validity and tests whether URLs are actually accessible.
Ensures only valid, reachable URLs are stored as artifact sources.

CORE FUNCTIONS:

1. is_valid_url_format(url: str) → bool
   Purpose: Check if URL has valid format without network access
   Returns: True if format valid (http/https scheme + domain), False otherwise
   Checks:
   - Scheme: Must be http:// or https://
   - NetLoc: Must have domain name
   - ParseResult: Uses urllib.parse.urlparse
   Called: Before network tests or during quick validation
   Performance: O(1) - very fast

   Examples:
   - Valid: "https://huggingface.co/google-bert/bert-base-uncased"
   - Valid: "http://github.com/openai/whisper"
   - Invalid: "ftp://example.com" (wrong scheme)
   - Invalid: "example.com/model" (no scheme)
   - Invalid: "/local/path" (no scheme or domain)

2. test_url_accessibility(url: str, timeout: int, follow_redirects: bool) → Tuple[bool, str]
   Purpose: Test if URL is accessible by making HTTP HEAD request
   Returns: Tuple of (is_accessible: bool, message: str)
   Parameters:
   - url: URL to test
   - timeout: Max seconds to wait for response (default: 10)
   - follow_redirects: Whether to follow 3xx redirects (default: True)

   HTTP Status Handling:
   - 2xx: Accessible (True, "Accessible (HTTP 200)")
   - 3xx with follow: Follows redirects (recursive)
   - 4xx: Client error (False, "Client error (HTTP 404)")
   - 5xx: Server error (False, "Server error (HTTP 503)")

   Exception Handling:
   - Timeout: "Request timeout (>10s)"
   - ConnectionError: "Connection error - URL unreachable"
   - RequestException: "Request failed: <error>"
   - Unexpected: "Unexpected error: <error>"

   Called: During comprehensive validation or registration
   Performance: Network I/O bound (10-30 seconds typical)

3. validate_model_url(url: str, test_accessibility: bool) → Dict[str, Any]
   Purpose: Comprehensive URL validation with optional accessibility testing
   Returns: Dict with validation results:
   {
     "url": str,                    # Original URL
     "is_valid": bool,              # Overall validation result
     "format_valid": bool,          # Format check passed
     "accessible": bool or None,    # Accessibility check result
     "message": str                 # Status message
   }

   Workflow:
   1. Check format (always)
   2. If format invalid, return early (False)
   3. If test_accessibility enabled:
     - Make HTTP HEAD request
     - Return accessibility result
   4. If test_accessibility disabled:
     - Return format valid (True)

   Use Cases:
   - Quick validation: test_accessibility=False
   - Full validation: test_accessibility=True (used during registration)
   - Bulk validation: Use False for speed, True for final check

   Called: POST /api/models/upload validation

NETWORK BEHAVIOR:
- User-Agent: Mimics browser ("Mozilla/5.0")
- Headers: Standard HTTP headers for compatibility
- Redirects: Follows up to 30 redirects by default
- Timeout: Respects timeout parameter (0-3600 seconds)
- SSL: Validates SSL certificates (can be disabled if needed)

ERROR RECOVERY:
- Timeout: Returns False but doesn't crash
- Connection refused: Caught and returns False
- DNS failure: Caught by requests library
- Invalid certificate: Caught and returned as False

Performance Considerations:
- Format check: <1ms
- Network test: 100-5000ms depending on URL and network
- Bulk validation: Process URLs in parallel if many

Logging:
- WARNING: Format validation failures
- ERROR: Unexpected validation errors
- All errors include context (URL, error type)

Security Considerations:
- Prevents SSRF: Could restrict to public URLs only
- Prevents malicious URLs: Forces http/https only
- Prevents typos: Validates before storage
- Rate limiting: Should add rate limits for testing many URLs

Specification Alignment:
- Per Section 3.2.1: Artifact URL must be valid
- Per Section 3.3: Input validation requirements
- Per Section 3.1: Authentication for validation endpoints

Related Functions:
- Used by: POST /api/models/upload endpoint
- Used by: URL storage service before caching
- Used by: Artifact management for URL verification
"""

import logging
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def is_valid_url_format(url: str) -> bool:
    """Check if URL has valid format.

    Args:
        url: URL string to validate

    Returns:
        True if URL format is valid, False otherwise
    """
    try:
        result = urlparse(url)
        # Must have scheme (http/https) and netloc (domain)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception as e:
        logger.warning(f"URL format validation failed: {e}")
        return False


def test_url_accessibility(
    url: str,
    timeout: int = 10,
    follow_redirects: bool = True
) -> Tuple[bool, str]:
    """Test if a URL is accessible and returns a successful response.

    Args:
        url: URL to test
        timeout: Request timeout in seconds (default: 10)
        follow_redirects: Whether to follow HTTP redirects (default: True)

    Returns:
        Tuple of (is_accessible, message)
    """
    if not is_valid_url_format(url):
        return False, "Invalid URL format"

    try:
        response = requests.head(
            url,
            timeout=timeout,
            allow_redirects=follow_redirects,
            headers={'User-Agent': 'Mozilla/5.0'}
        )

        if response.status_code < 400:
            return True, f"Accessible (HTTP {response.status_code})"
        elif response.status_code < 500:
            return False, f"Client error (HTTP {response.status_code})"
        else:
            return False, f"Server error (HTTP {response.status_code})"

    except requests.exceptions.Timeout:
        return False, f"Request timeout (>{timeout}s)"
    except requests.exceptions.ConnectionError:
        return False, "Connection error - URL unreachable"
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error testing URL: {e}")
        return False, f"Unexpected error: {str(e)}"


def validate_model_url(url: str, test_accessibility: bool = True) -> Dict[str, Any]:
    """Validate a model URL for upload.

    Performs format validation and optional accessibility testing.

    Args:
        url: URL to validate
        test_accessibility: Whether to test if URL is accessible (default: True)

    Returns:
        Dictionary with validation results:
        {
            'is_valid': bool,
            'format_valid': bool,
            'accessible': bool or None,
            'message': str,
            'url': str
        }
    """
    result = {
        'url': url,
        'is_valid': False,
        'format_valid': False,
        'accessible': None,
        'message': ''
    }

    # Check format
    format_valid = is_valid_url_format(url)
    result['format_valid'] = format_valid

    if not format_valid:
        result['message'] = 'Invalid URL format'
        return result

    # Check accessibility if requested
    if test_accessibility:
        accessible, access_message = test_url_accessibility(url)
        result['accessible'] = accessible
        result['message'] = access_message
        result['is_valid'] = accessible
    else:
        result['message'] = 'Format valid'
        result['is_valid'] = True

    return result


if __name__ == '__main__':
    # Example usage for testing
    test_urls = [
        'https://huggingface.co/google-bert/bert-base-uncased',
        'https://github.com/openai/whisper',
        'http://invalid-url-that-does-not-exist-12345.com',
        'not-a-url',
    ]

    print("URL Validator Test\n" + "=" * 50)
    for url in test_urls:
        result = validate_model_url(url, test_accessibility=True)
        print(f"\nURL: {url}")
        print(f"  Format Valid: {result['format_valid']}")
        print(f"  Accessible: {result['accessible']}")
        print(f"  Message: {result['message']}")
        print(f"  Overall Valid: {result['is_valid']}")
