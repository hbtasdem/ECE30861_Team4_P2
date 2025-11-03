
import sys
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

# Add the src directory to the path so we can import main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import calculate_all_scores, extract_model_name, main  # noqa: E402


class TestMain(unittest.TestCase):
    """Unit tests for main.py functions."""

    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        self.test_urls = [
            "https://huggingface.co/google-bert/bert-base-uncased",
            "https://huggingface.co/parvk11/audience_classifier_model",
            "https://huggingface.co/openai/whisper-tiny/tree/main",
        ]

    def test_extract_model_name(self) -> None:
        """Test model name extraction from URLs."""
        test_cases = [
            (
                "https://huggingface.co/google-bert/bert-base-uncased",
                "bert-base-uncased",
            ),
            (
                "https://huggingface.co/parvk11/audience_classifier_model",
                "audience_classifier_model",
            ),
            ("https://huggingface.co/openai/whisper-tiny/tree/main", "whisper-tiny"),
            ("", "unknown"),
            ("invalid-url", "invalid-url"),
        ]
        for url, expected in test_cases:
            with self.subTest(url=url):
                result = extract_model_name(url)
                self.assertEqual(result, expected)

    @patch("main.code_quality.code_quality_score")
    @patch("main.license_sub_score.license_sub_score")
    @patch("main.bus_factor.bus_factor_score")
    @patch("main.ramp_up_sub_score.ramp_up_time_score")
    @patch("main.performance_claims_sub_score.performance_claims_sub_score")
    @patch("main.dataset_quality_sub_score.dataset_quality_sub_score")
    @patch("main.available_dataset_code_score.available_dataset_code_score")
    @patch("main.net_score_calculator.calculate_net_score")
    def test_calculate_all_scores(
        self,
        mock_net_score: Any,
        mock_code_score: Any,
        mock_dataset_score: Any,
        mock_perf_score: Any,
        mock_ramp_score: Any,
        mock_bus_score: Any,
        mock_license_score: Any,
        mock_code_quality: Any,
    ) -> None:
        """Test calculate_all_scores function with mocked dependencies."""
        # Set up mock return values
        mock_license_score.return_value = (1.0, 0.1)
        mock_bus_score.return_value = (16, 0.1)  # Will be normalized: 16/20 = 0.8
        mock_ramp_score.return_value = (0.9, 0.1)
        mock_perf_score.return_value = (0.7, 0.1)
        mock_dataset_score.return_value = (0.6, 0.1)
        mock_code_score.return_value = (0.5, 0.2)
        mock_code_quality.return_value = (0.5, 0.1)
        mock_net_score.return_value = {"net_score": 0.75}
        # Test with a sample model URL
        result = calculate_all_scores("", "", "https://huggingface.co/test/model", set(), set())
        # Verify the result structure
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("category", result)
        self.assertIn("net_score", result)
        self.assertIn("license", result)
        self.assertIn("bus_factor", result)
        self.assertIn("ramp_up_time", result)
        self.assertIn("performance_claims", result)
        self.assertIn("dataset_quality", result)
        self.assertIn("code_quality", result)
        self.assertIn("size_score", result)
        # Verify values
        self.assertEqual(result["category"], "MODEL")
        self.assertEqual(result["license"], 1.0)
        self.assertEqual(result["bus_factor"], 0.8)
        self.assertEqual(result["ramp_up_time"], 0.9)
        self.assertEqual(result["performance_claims"], 0.7)
        self.assertEqual(result["dataset_quality"], 0.6)
        self.assertEqual(result["code_quality"], 0.5)
        self.assertEqual(result["net_score"], 0.75)

    def test_calculate_all_scores_with_bert_model(self) -> None:
        """Test calculate_all_scores with BERT model for size score logic."""
        # Define patch paths as variables to avoid long lines
        license_path = "main.license_sub_score.license_sub_score"
        bus_path = "main.bus_factor.bus_factor_score"
        ramp_path = "main.ramp_up_sub_score.ramp_up_time_score"
        perf_path = "main.performance_claims_sub_score." "performance_claims_sub_score"
        dataset_path = "main.dataset_quality_sub_score." "dataset_quality_sub_score"
        code_path = "main.available_dataset_code_score." "available_dataset_code_score"
        net_path = "main.net_score_calculator.calculate_net_score"

        with patch(license_path) as mock_license, patch(bus_path) as mock_bus, patch(
            ramp_path
        ) as mock_ramp, patch(perf_path) as mock_perf, patch(
            dataset_path
        ) as mock_dataset, patch(
            code_path
        ) as mock_code, patch(
            net_path
        ) as mock_net:
            # Set up mock return values
            mock_license.return_value = 1.0
            mock_bus.return_value = 0.8
            mock_ramp.return_value = (0.9, 0.1)
            mock_perf.return_value = 0.7
            mock_dataset.return_value = 0.6
            mock_code.return_value = (0.5, 0.2)
            mock_net.return_value = {"net_score": 0.75}
            # Test with BERT model
            result = calculate_all_scores(
                "", "", "https://huggingface.co/google-bert/bert-base-uncased",
                set(), set()
            )
            # Verify BERT-specific size scores
            self.assertEqual(result["size_score"]["raspberry_pi"], 0.2)
            self.assertEqual(result["size_score"]["jetson_nano"], 0.4)
            self.assertEqual(result["size_score"]["desktop_pc"], 0.95)
            self.assertEqual(result["size_score"]["aws_server"], 1.0)
            self.assertEqual(result["size_score_latency"], 50)

    def test_calculate_all_scores_with_whisper_model(self) -> None:
        """Test calculate_all_scores with Whisper model size score logic."""
        # Define patch paths as variables to avoid long lines
        license_path = "main.license_sub_score.license_sub_score"
        bus_path = "main.bus_factor.bus_factor_score"
        ramp_path = "main.ramp_up_sub_score.ramp_up_time_score"
        perf_path = "main.performance_claims_sub_score." "performance_claims_sub_score"
        dataset_path = "main.dataset_quality_sub_score." "dataset_quality_sub_score"
        code_path = "main.available_dataset_code_score." "available_dataset_code_score"
        net_path = "main.net_score_calculator.calculate_net_score"

        with patch(license_path) as mock_license, patch(bus_path) as mock_bus, patch(
            ramp_path
        ) as mock_ramp, patch(perf_path) as mock_perf, patch(
            dataset_path
        ) as mock_dataset, patch(
            code_path
        ) as mock_code, patch(
            net_path
        ) as mock_net:
            # Set up mock return values
            mock_license.return_value = 1.0
            mock_bus.return_value = 0.8
            mock_ramp.return_value = (0.9, 0.1)
            mock_perf.return_value = 0.7
            mock_dataset.return_value = 0.6
            mock_code.return_value = (0.5, 0.2)
            mock_net.return_value = {"net_score": 0.75}
            # Test with Whisper model
            result = calculate_all_scores(
                "", "", "https://huggingface.co/openai/whisper-tiny/tree/main",
                set(), set()
            )
            # Verify Whisper-specific size scores
            self.assertEqual(result["size_score"]["raspberry_pi"], 0.9)
            self.assertEqual(result["size_score"]["jetson_nano"], 0.95)
            self.assertEqual(result["size_score"]["desktop_pc"], 1.0)
            self.assertEqual(result["size_score"]["aws_server"], 1.0)
            self.assertEqual(result["size_score_latency"], 15)

    def test_main_with_valid_file(self) -> None:
        """Test main function with a valid CSV input file."""
        # Create a temporary file with test CSV data
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(
                "https://github.com/test/code,"
                "https://huggingface.co/datasets/test,"
                "https://huggingface.co/google-bert/"
                "bert-base-uncased\n"
            )
            f.write(",,https://huggingface.co/parvk11/" "audience_classifier_model\n")
            temp_file = f.name

        try:
            with patch("main.calculate_all_scores") as mock_calculate:
                mock_calculate.return_value = {
                    "name": "test-model",
                    "category": "MODEL",
                    "net_score": 0.5,
                    "net_score_latency": 100,
                    "ramp_up_time": 0.5,
                    "ramp_up_time_latency": 50,
                    "bus_factor": 0.5,
                    "bus_factor_latency": 25,
                    "performance_claims": 0.5,
                    "performance_claims_latency": 30,
                    "license": 1.0,
                    "license_latency": 10,
                    "size_score": {
                        "raspberry_pi": 0.5,
                        "jetson_nano": 0.6,
                        "desktop_pc": 0.8,
                        "aws_server": 1.0,
                    },
                    "size_score_latency": 20,
                    "dataset_and_code_score": 0.5,
                    "dataset_and_code_score_latency": 15,
                    "dataset_quality": 0.5,
                    "dataset_quality_latency": 20,
                    "code_quality": 0.5,
                    "code_quality_latency": 15,
                }
                # Capture stdout
                with patch("sys.argv", ["main.py", temp_file]):
                    with patch("builtins.print") as mock_print:
                        result = main()
                        self.assertEqual(result, 0)
                        # Verify JSON was printed
                        self.assertTrue(mock_print.called)
        finally:
            os.unlink(temp_file)

    def test_main_with_invalid_file(self) -> None:
        """Test main function with a non-existent file."""
        with patch("sys.argv", ["main.py", "nonexistent.txt"]):
            result = main()
            self.assertEqual(result, 1)

    def test_main_with_wrong_args(self) -> None:
        """Test main function with wrong number of arguments."""
        with patch("sys.argv", ["main.py"]):
            result = main()
            self.assertEqual(result, 1)

    def test_main_with_github_url_only(self) -> None:
        """Test main function skips rows with only GitHub URLs (no link)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("https://github.com/test/repo,,\n")
            temp_file = f.name

        try:
            with patch("sys.argv", ["main.py", temp_file]):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 0)
                    # Should not print anything since no model link is provided
                    self.assertFalse(mock_print.called)
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
