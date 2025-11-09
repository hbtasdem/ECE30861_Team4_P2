"""URL validation and accessibility testing for model URLs.

This module provides functions to validate and test model URLs before
they are registered in the system. It checks URL format validity and
tests whether URLs are actually accessible (can reach the server).

Key features:
- Validate URL format (scheme, structure, etc.)
- Test URL accessibility with HTTP requests
- Handle timeouts and connection errors gracefully
- Return detailed validation results for user feedback
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
