import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the phase1metrics directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'phase1metrics'))

# Import after path modification
import phase1metrics.purdue_api as purdue_api  # noqa: E402


class TestPurdueGenAI(unittest.TestCase):
    """Simple tests for PurdueGenAI client."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with provided API key."""
        client = purdue_api.PurdueGenAI(api_key="test_key")
        self.assertEqual(client.api_key, "test_key")

    @patch.dict(os.environ, {'GEN_AI_STUDIO_API_KEY': 'env_key'})
    def test_init_with_env_key(self) -> None:
        """Test initialization with environment variable."""
        client = purdue_api.PurdueGenAI()
        self.assertEqual(client.api_key, "env_key")

    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_api_key(self) -> None:
        """Test initialization without API key raises ValueError."""
        with self.assertRaises(ValueError):
            purdue_api.PurdueGenAI()

    @patch('urllib.request.urlopen')
    def test_chat_success(self, mock_urlopen: Mock) -> None:
        """Test successful chat response."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Hello!"}}]
        }).encode('utf-8')

        # Set up context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_response)
        mock_context.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_context

        client = purdue_api.PurdueGenAI(api_key="test_key")
        result = client.chat("Hello")
        self.assertEqual(result, "Hello!")

    @patch('urllib.request.urlopen')
    def test_chat_api_error(self, mock_urlopen: Mock) -> None:
        """Test chat with API error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status = 400
        mock_response.read.return_value = b"Bad Request"

        # Set up context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_response)
        mock_context.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_context

        client = purdue_api.PurdueGenAI(api_key="test_key")
        with self.assertRaises(Exception) as context:
            client.chat("Hello")
        self.assertIn("API Error 400", str(context.exception))


if __name__ == "__main__":
    unittest.main()
