import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import docker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src/metrics"))
from reproducibility import ReproducibilityChecker


@pytest.fixture
def mock_genai():
    """Mock Google GenAI client"""
    with patch('google.generativeai.configure') as mock_configure, \
         patch('google.generativeai.GenerativeModel') as mock_model:
        
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        
        yield mock_instance


@pytest.fixture
def mock_docker():
    """Mock Docker client"""
    with patch('docker.from_env') as mock_docker_client:
        mock_client = MagicMock()
        mock_docker_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def checker(mock_genai, mock_docker):
    """Create ReproducibilityChecker instance with mocked dependencies"""
    return ReproducibilityChecker(genai_api_key="test-api-key")


class TestExtractCodeFromModelCard:
    """Test code extraction from model cards"""
    
    def test_extract_python_code_block(self, checker):
        """Should extract Python code from markdown"""
        model_card = """
# Model Card

## Usage

```python
import numpy as np
print("Hello World")
```
"""
        code = checker.extract_code_from_model_card(model_card)
        assert code is not None
        assert "import numpy" in code
        assert "print" in code
    
    def test_extract_generic_code_block(self, checker):
        """Should extract generic code blocks if no python blocks"""
        model_card = """
# Model Card

```
import torch
model = torch.load('model.pt')
```
"""
        code = checker.extract_code_from_model_card(model_card)
        assert code is not None
        assert "import torch" in code
    
    def test_no_code_found(self, checker):
        """Should return None if no code blocks"""
        model_card = """
# Model Card

This model has no code examples.
"""
        code = checker.extract_code_from_model_card(model_card)
        assert code is None
    
    def test_ignore_short_code_blocks(self, checker):
        """Should ignore code blocks that are too short"""
        model_card = """
# Model Card

```python
import x
```

```python
import numpy as np
arr = np.array([1, 2, 3])
print(arr.mean())
```
"""
        code = checker.extract_code_from_model_card(model_card)
        assert code is not None
        assert "numpy" in code
        assert "mean()" in code


class TestCreateTestScript:
    """Test test script generation"""
    
    def test_basic_script_creation(self, checker):
        """Should create valid test script"""
        code = "print('hello')"
        script = checker.create_test_script(code)
        
        assert "import sys" in script
        assert "import traceback" in script
        assert "print('hello')" in script
        assert "CODE EXECUTED SUCCESSFULLY" in script
        assert "ERROR OCCURRED" in script
    
    def test_script_with_requirements(self, checker):
        """Should include requirements in script"""
        code = "import numpy"
        requirements = "numpy==1.21.0"
        script = checker.create_test_script(code, requirements)
        
        assert requirements in script


class TestIndentCode:
    """Test code indentation helper"""
    
    def test_indent_single_line(self, checker):
        """Should indent single line"""
        code = "print('test')"
        indented = checker._indent_code(code, 4)
        assert indented == "    print('test')"
    
    def test_indent_multiple_lines(self, checker):
        """Should indent all lines"""
        code = "line1\nline2\nline3"
        indented = checker._indent_code(code, 2)
        assert indented == "  line1\n  line2\n  line3"


class TestRunCodeInDocker:
    """Test Docker execution"""
    
    def test_successful_execution(self, checker, mock_docker):
        """Should return success when code runs"""
        # Mock successful container execution
        mock_container = b"some output\n=== CODE EXECUTED SUCCESSFULLY ===\n"
        mock_docker.containers.run.return_value = mock_container
        
        success, output = checker.run_code_in_docker("print('test')")
        
        assert success is True
        assert "CODE EXECUTED SUCCESSFULLY" in output
        
        # Verify Docker was called with correct params
        mock_docker.containers.run.assert_called_once()
        call_kwargs = mock_docker.containers.run.call_args[1]
        assert call_kwargs['image'] == 'python:3.9-slim'
        assert call_kwargs['mem_limit'] == '512m'
        assert call_kwargs['remove'] is True
    
    def test_failed_execution(self, checker, mock_docker):
        """Should return failure when code errors"""
        # Mock container error
        error = docker.errors.ContainerError(
            container="test",
            exit_status=1,
            command="python",
            image="python:3.9-slim",
            stderr=b"NameError: name 'x' is not defined"
        )
        mock_docker.containers.run.side_effect = error
        
        success, output = checker.run_code_in_docker("print(x)")
        
        assert success is False
        assert "NameError" in output
    
    def test_docker_timeout(self, checker, mock_docker):
        """Should handle Docker timeout"""
        mock_docker.containers.run.side_effect = Exception("Timeout")
        
        success, output = checker.run_code_in_docker("while True: pass")
        
        assert success is False
        assert "Timeout" in output


class TestGetAIFix:
    """Test AI debugging functionality"""
    
    def test_successful_ai_fix(self, checker, mock_genai):
        """Should return fixed code from Gemini"""
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = """```python
import numpy as np
arr = np.array([1, 2, 3])
print(arr.mean())
```"""
        mock_genai.generate_content.return_value = mock_response
        
        code = "print(undefined_var)"
        error = "NameError: name 'undefined_var' is not defined"
        
        fixed = checker.get_ai_fix(code, error, attempt=1)
        
        assert fixed is not None
        assert "import numpy" in fixed
        assert "```" not in fixed  # Should strip markdown
    
    def test_ai_fix_without_markdown(self, checker, mock_genai):
        """Should handle responses without code blocks"""
        mock_response = MagicMock()
        mock_response.text = "import os\nprint('fixed')"
        mock_genai.generate_content.return_value = mock_response
        
        fixed = checker.get_ai_fix("bad code", "error", attempt=1)
        
        assert fixed == "import os\nprint('fixed')"
    
    def test_ai_api_error(self, checker, mock_genai):
        """Should handle API errors gracefully"""
        mock_genai.generate_content.side_effect = Exception("API Error")
        
        fixed = checker.get_ai_fix("code", "error", attempt=1)
        
        assert fixed is None


class TestFetchModelCard:
    """Test fetching model cards from HuggingFace"""
    
    @patch('requests.get')
    def test_fetch_with_full_url(self, mock_get, checker):
        """Should fetch README from full URL"""
        mock_response = Mock()
        mock_response.text = "# Model Card\n\nThis is a test"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        content = checker.fetch_model_card("https://huggingface.co/microsoft/DialoGPT-medium")
        
        assert content == "# Model Card\n\nThis is a test"
        mock_get.assert_called_once()
        assert "microsoft/DialoGPT-medium/raw/main/README.md" in mock_get.call_args[0][0]
    
    @patch('requests.get')
    def test_fetch_with_model_path(self, mock_get, checker):
        """Should fetch README from model path"""
        mock_response = Mock()
        mock_response.text = "# Model"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        content = checker.fetch_model_card("google-bert/bert-base-uncased")
        
        assert content == "# Model"
        assert "google-bert/bert-base-uncased/raw/main/README.md" in mock_get.call_args[0][0]
    
    @patch('requests.get')
    def test_fetch_failure(self, mock_get, checker):
        """Should return None on fetch failure"""
        mock_get.side_effect = Exception("Network error")
        
        content = checker.fetch_model_card("invalid/model")
        
        assert content is None


class TestCheckReproducibility:
    """Integration tests for full reproducibility check"""
    
    @patch('requests.get')
    def test_no_model_card_found(self, mock_get, checker):
        """Should return 0 if model card cannot be fetched from HuggingFace"""
        mock_get.side_effect = Exception("404")
        
        # Pass HuggingFace model identifier (URL or path)
        score, explanation = checker.check_reproducibility("invalid/model")
        
        assert score == 0.0
        assert "Could not fetch" in explanation
    
    @patch('requests.get')
    def test_no_code_in_model_card(self, mock_get, checker):
        """Should return 0 if no code in model card"""
        mock_response = Mock()
        mock_response.text = "# Model\n\nNo code here"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        score, explanation = checker.check_reproducibility("test/model")
        
        assert score == 0.0
        assert "No demonstration code found" in explanation
    
    @patch('requests.get')
    def test_code_runs_perfectly(self, mock_get, checker, mock_docker):
        """Should return 1.0 if code runs without changes"""
        # Mock model card fetch
        mock_response = Mock()
        mock_response.text = """
# Model

```python
import numpy as np
print(np.array([1,2,3]).mean())
```
"""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock successful Docker run
        mock_docker.containers.run.return_value = b"2.0\n=== CODE EXECUTED SUCCESSFULLY ===\n"
        
        score, explanation = checker.check_reproducibility("test/model")
        
        assert score == 1.0
        assert "without modifications" in explanation
    
    @patch('requests.get')
    def test_code_runs_after_ai_fix(self, mock_get, checker, mock_docker, mock_genai):
        """Should return 0.5 if code runs after AI debugging"""
        # Mock model card
        mock_response = Mock()
        mock_response.text = """
```python
print(undefined_variable)
```
"""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock Docker: first fail, then succeed
        error = docker.errors.ContainerError(
            container="test", exit_status=1, command="python",
            image="python:3.9-slim", stderr=b"NameError"
        )
        mock_docker.containers.run.side_effect = [
            error,  # First attempt fails
            b"fixed\n=== CODE EXECUTED SUCCESSFULLY ===\n"  # Second attempt succeeds
        ]
        
        # Mock AI fix
        mock_ai_response = MagicMock()
        mock_ai_response.text = "print('fixed')"
        mock_genai.generate_content.return_value = mock_ai_response
        
        score, explanation = checker.check_reproducibility("test/model")
        
        assert score == 0.5
        assert "AI debugging" in explanation
    
    @patch('requests.get')
    def test_code_fails_after_retries(self, mock_get, checker, mock_docker, mock_genai):
        """Should return 0 if code fails even after AI attempts"""
        # Mock model card
        mock_response = Mock()
        mock_response.text = """
```python
import broken_package_that_doesnt_exist
```
"""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock Docker: always fail
        error = docker.errors.ContainerError(
            container="test", exit_status=1, command="python",
            image="python:3.9-slim", stderr=b"ModuleNotFoundError"
        )
        mock_docker.containers.run.side_effect = error
        
        # Mock AI fixes (that don't work)
        mock_ai_response = MagicMock()
        mock_ai_response.text = "still broken code"
        mock_genai.generate_content.return_value = mock_ai_response
        
        score, explanation = checker.check_reproducibility("test/model")
        
        assert score == 0.0
        assert "does not run" in explanation
        assert "3" in explanation  # Mentions 3 attempts


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_model_card(self, checker):
        """Should handle empty model card"""
        code = checker.extract_code_from_model_card("")
        assert code is None
    
    def test_malformed_markdown(self, checker):
        """Should handle malformed markdown"""
        model_card = "```python\nno closing backticks"
        code = checker.extract_code_from_model_card(model_card)
        assert code is None
    
    @patch('requests.get')
    def test_timeout_on_fetch(self, mock_get, checker):
        """Should handle fetch timeout"""
        import requests
        mock_get.side_effect = requests.Timeout()
        
        content = checker.fetch_model_card("test/model")
        assert content is None


# Run with: pytest test_reproducibility_checker.py -v