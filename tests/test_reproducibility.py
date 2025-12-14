import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Import the class under test

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from metrics.reproducibility import ReproducibilityChecker


@pytest.fixture
def checker():
    """
    Create a ReproducibilityChecker instance with Docker mocked.
    """
    with patch("docker.from_env") as mock_docker:
        mock_docker.return_value = MagicMock()
        return ReproducibilityChecker()


# -----------------------------
# fetch_model_card
# -----------------------------


@patch("requests.get")
def test_fetch_model_card_success(mock_get, checker):
    mock_response = MagicMock()
    mock_response.text = "# Model Card\n```python\nprint('hello')\n```"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    content = checker.fetch_model_card("microsoft/DialoGPT-medium")

    assert content is not None
    assert "Model Card" in content


@patch("requests.get")
def test_fetch_model_card_failure(mock_get, checker):
    mock_get.side_effect = Exception("404")

    content = checker.fetch_model_card("nonexistent/model")

    assert content is None


def test_extract_code_from_model_card_no_code(checker):
    model_card = "No code here"

    code = checker.extract_code_from_model_card(model_card)

    assert code is None


def test_create_test_script_includes_user_code(checker):
    code = "print('hi')"
    script = checker.create_test_script(code)

    assert "print('hi')" in script
    assert "CODE EXECUTED SUCCESSFULLY" in script


def test_create_test_script_parses_pip_install(checker):
    code = """
    pip install requests
    import requests
    print("done")
    """

    script = checker.create_test_script(code)

    assert "pip" in script
    assert "requests" in script
    assert "subprocess.check_call" in script


def test_run_code_in_docker_success(checker):
    checker.client.containers.run.return_value = b"=== CODE EXECUTED SUCCESSFULLY ==="

    success, output = checker.run_code_in_docker("print('hi')")

    assert success is True
    assert "SUCCESSFULLY" in output


def test_run_code_in_docker_failure(checker):
    checker.client.containers.run.side_effect = Exception("Docker error")

    success, output = checker.run_code_in_docker("print('hi')")

    assert success is False
    assert "Docker error" in output


def test_get_ai_fix_no_model(checker):
    checker.model = None

    result = checker.get_ai_fix("print('hi')", "Error")

    assert result is None


def test_get_ai_fix_with_model(checker):
    fake_model = MagicMock()
    fake_model.chat.return_value = "pip install requests\nprint('fixed')"
    checker.model = fake_model

    fixed_code = checker.get_ai_fix("print('hi')", "ModuleNotFoundError")

    assert fixed_code is not None
    assert "pip install" in fixed_code


@patch.object(ReproducibilityChecker, "fetch_model_card")
@patch.object(ReproducibilityChecker, "extract_code_from_model_card")
@patch.object(ReproducibilityChecker, "run_code_in_docker")
def test_check_reproducibility_success(mock_run, mock_extract, mock_fetch, checker):
    mock_fetch.return_value = "```python\nprint('hi')\n```"
    mock_extract.return_value = "print('hi')"
    mock_run.return_value = (True, "=== CODE EXECUTED SUCCESSFULLY ===")

    score, explanation = checker.check_reproducibility("test/model")

    assert score == 1.0
    assert "successfully" in explanation.lower()


@patch.object(ReproducibilityChecker, "fetch_model_card")
def test_check_reproducibility_no_model_card(mock_fetch, checker):
    mock_fetch.return_value = None

    score, explanation = checker.check_reproducibility("bad/model")

    assert score == 0.0
    assert "Could not fetch model card" in explanation
