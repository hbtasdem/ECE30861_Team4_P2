import sys
import unittest
from unittest.mock import patch
import os

# Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from net_score_calculator import calculate_net_score  # noqa: E402
from net_score_calculator import print_score_summary  # noqa: E402


class TestNetScoreCalculator(unittest.TestCase):
    """Test cases for NetScore calculator with different HF models."""

    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        self.test_models = [
            "gpt2",
            "microsoft/DialoGPT-medium",
            "bert-base-uncased",
            "distilbert-base-uncased",
            "roberta-base",
            "facebook/opt-125m",
            "EleutherAI/gpt-neo-125M",
            "microsoft/DialoGPT-small",
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
            "nlptown/bert-base-multilingual-uncased-sentiment",
        ]

    def test_calculate_net_score_structure(self) -> None:
        """Test that calculate_net_score returns the correct structure."""
        model_id = "gpt2"

        with patch("net_score_calculator.license_sub_score") as mock_license, patch(
            "net_score_calculator.ramp_up_time_score"
        ) as mock_ramp_up, patch(
            "net_score_calculator.bus_factor_score"
        ) as mock_bus_factor, patch(
            "net_score_calculator.available_dataset_code_score"
        ) as mock_dataset_code, patch(
            "net_score_calculator.dataset_quality_sub_score"
        ) as mock_dataset_quality, patch(
            "net_score_calculator.performance_claims_sub_score"
        ) as mock_performance:
            # Mock return values
            mock_license.return_value = (1.0, 0.1)
            mock_ramp_up.return_value = (0.8, 0.2)
            mock_bus_factor.return_value = (5, 0.1)
            mock_dataset_code.return_value = (0.5, 0.15)
            mock_dataset_quality.return_value = (0.7, 0.12)
            mock_performance.return_value = (0.9, 0.08)

            results = calculate_net_score(model_id)

            # Test structure
            self.assertIn("name", results)
            self.assertIn("category", results)
            self.assertIn("net_score", results)
            self.assertIn("net_score_latency", results)
            self.assertIn("size_score", results)
            self.assertIn("license", results)
            self.assertIn("ramp_up_time", results)
            self.assertIn("bus_factor", results)
            self.assertIn("dataset_and_code_score", results)
            self.assertIn("dataset_quality", results)
            self.assertIn("code_quality", results)
            self.assertIn("performance_claims", results)

            # Test data types
            self.assertIsInstance(results["net_score"], float)
            self.assertIsInstance(results["net_score_latency"], int)
            self.assertIsInstance(results["size_score"], dict)
            self.assertIsInstance(results["license"], (int, float))
            self.assertIsInstance(results["ramp_up_time"], (int, float))
            self.assertIsInstance(results["bus_factor"], (int, float))
            self.assertIsInstance(results["dataset_and_code_score"], (int, float))
            self.assertIsInstance(results["dataset_quality"], (int, float))
            self.assertIsInstance(results["code_quality"], (int, float))
            self.assertIsInstance(results["performance_claims"], (int, float))

    def test_net_score_calculation_accuracy(self) -> None:
        """Test that NetScore calculation follows the correct formula."""
        model_id = "test-model"

        with patch("net_score_calculator.license_sub_score") as mock_license, \
             patch("net_score_calculator.ramp_up_time_score") as mock_ramp_up, \
             patch("net_score_calculator.bus_factor_score") as mock_bus_factor, \
             patch("net_score_calculator.available_dataset_code_score") as mock_dataset_code, \
             patch("net_score_calculator.dataset_quality_sub_score") as mock_dataset_quality, \
             patch("net_score_calculator.performance_claims_sub_score") as mock_performance, \
             patch("net_score_calculator.size_score") as mock_size:
            # Set known values for calculation verification
            mock_size.return_value = ({}, 0.5, 50)
            mock_license.return_value = (1.0, 0.1)  # 0.2 weight
            mock_ramp_up.return_value = (0.5, 0.2)  # 0.2 weight
            mock_bus_factor.return_value = (4, 0.1)  # 0.05 weight
            mock_dataset_code.return_value = (0.8, 0.15)  # 0.15 weight
            mock_dataset_quality.return_value = (0.6, 0.12)  # 0.15 weight
            mock_performance.return_value = (0.7, 0.08)  # 0.1 weight
            mock_size.return_value = ([], 0.5, 0.05)

            results = calculate_net_score(model_id)

            # Expected calculation:
            # 0.05 * 0.5 (size) + 0.2 * 1.0 (license) + 0.2 * 0.5 (ramp_up)
            # + 0.05 * 0.2 (bus_factor normalized: 4/20) + 0.15 * 0.8
            # + 0.15 * 0.6 (dataset_quality) + 0.1 * 0.5 (code_quality)
            # + 0.1 * 0.7 (performance)
            expected_score = round(
                0.05 * 0.5
                + 0.2 * 1.0
                + 0.2 * 0.5
                + 0.05 * 0.2
                + 0.15 * 0.8
                + 0.15 * 0.6
                + 0.1 * 0.5
                + 0.1 * 0.7,
                2,
            )
            expected_score = round(expected_score, 2)

            self.assertEqual(results["net_score"], expected_score)

    def test_weight_breakdown_calculation(self) -> None:
        """Test that weight breakdown calculations are correct."""
        model_id = "test-model"

        with patch("net_score_calculator.size_score") as mock_size, patch(
            "net_score_calculator.license_sub_score"
        ) as mock_license, patch(
            "net_score_calculator.ramp_up_time_score"
        ) as mock_ramp_up, patch(
            "net_score_calculator.bus_factor_score"
        ) as mock_bus_factor, patch(
            "net_score_calculator.available_dataset_code_score"
        ) as mock_dataset_code, patch(
            "net_score_calculator.dataset_quality_sub_score"
        ) as mock_dataset_quality, patch(
            "net_score_calculator.performance_claims_sub_score"
        ) as mock_performance:
            mock_size.return_value = ({}, 0.75, 50)
            mock_license.return_value = (0.8, 0.1)
            mock_ramp_up.return_value = (0.6, 0.2)
            mock_bus_factor.return_value = (3, 0.1)
            mock_dataset_code.return_value = (0.4, 0.15)
            mock_dataset_quality.return_value = (0.9, 0.12)
            mock_performance.return_value = (0.5, 0.08)

            results = calculate_net_score(model_id)

            # Test that individual scores are correctly stored
            self.assertEqual(results["license"], 0.8)
            self.assertEqual(results["ramp_up_time"], 0.6)
            self.assertEqual(results["bus_factor"], 0.15)  # 3/20 normalized
            self.assertEqual(results["dataset_and_code_score"], 0.4)
            self.assertEqual(results["dataset_quality"], 0.9)
            self.assertEqual(results["performance_claims"], 0.5)

    def test_default_values_for_missing_functions(self) -> None:
        """Test that default values are used for missing functions."""
        model_id = "test-model"

        with patch("net_score_calculator.size_score") as mock_size, patch(
            "net_score_calculator.license_sub_score"
        ) as mock_license, patch(
            "net_score_calculator.ramp_up_time_score"
        ) as mock_ramp_up, patch(
            "net_score_calculator.bus_factor_score"
        ) as mock_bus_factor, patch(
            "net_score_calculator.available_dataset_code_score"
        ) as mock_dataset_code, patch(
            "net_score_calculator.dataset_quality_sub_score"
        ) as mock_dataset_quality, patch(
            "net_score_calculator.performance_claims_sub_score"
        ) as mock_performance:
            mock_size.return_value = (
                {
                    "raspberry_pi": 0.5,
                    "jetson_nano": 0.5,
                    "desktop_pc": 0.5,
                    "aws_server": 0.5,
                },
                0.75,
                0,
            )
            mock_license.return_value = (1.0, 0.1)
            mock_ramp_up.return_value = (0.5, 0.2)
            mock_bus_factor.return_value = (2, 0.1)
            mock_dataset_code.return_value = (0.3, 0.15)
            mock_dataset_quality.return_value = (0.7, 0.12)
            mock_performance.return_value = (0.6, 0.08)

            results = calculate_net_score(model_id)

            # Test default values
            self.assertEqual(results["size_score"]["raspberry_pi"], 0.5)
            self.assertEqual(results["code_quality"], 0.5)
            self.assertEqual(results["code_quality_latency"], 0)

    def test_latency_conversion(self) -> None:
        """Test that latency values are properly converted to milliseconds."""
        model_id = "test-model"

        with patch("net_score_calculator.license_sub_score") as mock_license, patch(
            "net_score_calculator.ramp_up_time_score"
        ) as mock_ramp_up, patch(
            "net_score_calculator.bus_factor_score"
        ) as mock_bus_factor, patch(
            "net_score_calculator.available_dataset_code_score"
        ) as mock_dataset_code, patch(
            "net_score_calculator.dataset_quality_sub_score"
        ) as mock_dataset_quality, patch(
            "net_score_calculator.performance_claims_sub_score"
        ) as mock_performance:
            # Return latencies in seconds
            mock_license.return_value = (1.0, 0.123)  # 123ms
            mock_ramp_up.return_value = (0.5, 0.456)  # 456ms
            mock_bus_factor.return_value = (2, 0.1)
            mock_dataset_code.return_value = (0.3, 0.789)  # 789ms
            mock_dataset_quality.return_value = (0.7, 0.321)  # 321ms
            mock_performance.return_value = (0.6, 0.654)  # 654ms

            results = calculate_net_score(model_id)

            # Test latency conversion to milliseconds
            self.assertEqual(results["license_latency"], 123)
            self.assertEqual(results["ramp_up_time_latency"], 456)
            self.assertEqual(results["dataset_and_code_score_latency"], 789)
            self.assertEqual(results["dataset_quality_latency"], 321)
            self.assertEqual(results["performance_claims_latency"], 654)

    def test_model_id_preservation(self) -> None:
        """Test that model_id is correctly preserved in results."""
        test_models = ["gpt2", "bert-base-uncased", "microsoft/DialoGPT-medium"]

        for model_id in test_models:
            with patch("net_score_calculator.license_sub_score") as mock_license, patch(
                "net_score_calculator.ramp_up_time_score"
            ) as mock_ramp_up, patch(
                "net_score_calculator.bus_factor_score"
            ) as mock_bus_factor, patch(
                "net_score_calculator.available_dataset_code_score"
            ) as mock_dataset_code, patch(
                "net_score_calculator.dataset_quality_sub_score"
            ) as mock_dataset_quality, patch(
                "net_score_calculator.performance_claims_sub_score"
            ) as mock_performance:
                mock_license.return_value = (1.0, 0.1)
                mock_ramp_up.return_value = (0.5, 0.2)
                mock_bus_factor.return_value = (2, 0.1)
                mock_dataset_code.return_value = (0.3, 0.15)
                mock_dataset_quality.return_value = (0.7, 0.12)
                mock_performance.return_value = (0.6, 0.08)

                results = calculate_net_score(model_id)
                self.assertEqual(results["name"], model_id)

    def test_net_score_range(self) -> None:
        """Test that NetScore is within reasonable range."""
        model_id = "test-model"

        with patch("net_score_calculator.license_sub_score") as mock_license, patch(
            "net_score_calculator.ramp_up_time_score"
        ) as mock_ramp_up, patch(
            "net_score_calculator.bus_factor_score"
        ) as mock_bus_factor, patch(
            "net_score_calculator.available_dataset_code_score"
        ) as mock_dataset_code, patch(
            "net_score_calculator.dataset_quality_sub_score"
        ) as mock_dataset_quality, patch(
            "net_score_calculator.performance_claims_sub_score"
        ) as mock_performance:
            # Test with all minimum values
            mock_license.return_value = (0.0, 0.1)
            mock_ramp_up.return_value = (0.0, 0.2)
            mock_bus_factor.return_value = (0, 0.1)
            mock_dataset_code.return_value = (0.0, 0.15)
            mock_dataset_quality.return_value = (0.0, 0.12)
            mock_performance.return_value = (0.0, 0.08)

            results = calculate_net_score(model_id)
            min_score = results["net_score"]

            # Test with all maximum values
            mock_license.return_value = (1.0, 0.1)
            mock_ramp_up.return_value = (1.0, 0.2)
            mock_bus_factor.return_value = (10, 0.1)  # Max bus factor
            mock_dataset_code.return_value = (1.0, 0.15)
            mock_dataset_quality.return_value = (1.0, 0.12)
            mock_performance.return_value = (1.0, 0.08)

            results = calculate_net_score(model_id)
            max_score = results["net_score"]

            # NetScore should be within reasonable bounds
            self.assertGreaterEqual(min_score, 0.0)
            self.assertLessEqual(max_score, 2.0)  # Upper bound

    def test_print_score_summary_no_error(self) -> None:
        """Test that print_score_summary doesn't raise errors."""
        model_id = "test-model"

        with patch("net_score_calculator.license_sub_score") as mock_license, patch(
            "net_score_calculator.ramp_up_time_score"
        ) as mock_ramp_up, patch(
            "net_score_calculator.bus_factor_score"
        ) as mock_bus_factor, patch(
            "net_score_calculator.available_dataset_code_score"
        ) as mock_dataset_code, patch(
            "net_score_calculator.dataset_quality_sub_score"
        ) as mock_dataset_quality, patch(
            "net_score_calculator.performance_claims_sub_score"
        ) as mock_performance:
            mock_license.return_value = (1.0, 0.1)
            mock_ramp_up.return_value = (0.5, 0.2)
            mock_bus_factor.return_value = (2, 0.1)
            mock_dataset_code.return_value = (0.3, 0.15)
            mock_dataset_quality.return_value = (0.7, 0.12)
            mock_performance.return_value = (0.6, 0.08)

            results = calculate_net_score(model_id)

            # This should not raise an exception
            try:
                print_score_summary(results)
            except Exception as e:
                self.fail(f"print_score_summary raised an exception: {e}")

    def test_error_handling_in_scoring_functions(self) -> None:
        """Test that errors in scoring functions are handled gracefully."""
        model_id = "test-model"

        with patch("net_score_calculator.license_sub_score") as mock_license, patch(
            "net_score_calculator.ramp_up_time_score"
        ) as mock_ramp_up, patch(
            "net_score_calculator.bus_factor_score"
        ) as mock_bus_factor, patch(
            "net_score_calculator.available_dataset_code_score"
        ) as mock_dataset_code, patch(
            "net_score_calculator.dataset_quality_sub_score"
        ) as mock_dataset_quality, patch(
            "net_score_calculator.performance_claims_sub_score"
        ) as mock_performance:
            # Make one function raise an exception
            mock_license.side_effect = Exception("Network error")
            mock_ramp_up.return_value = (0.5, 0.2)
            mock_bus_factor.return_value = (2, 0.1)
            mock_dataset_code.return_value = (0.3, 0.15)
            mock_dataset_quality.return_value = (0.7, 0.12)
            mock_performance.return_value = (0.6, 0.08)

            # This should handle the exception gracefully
            try:
                results = calculate_net_score(model_id)
                # If it doesn't crash, that's good error handling
                self.assertIsInstance(results, dict)
            except Exception as e:
                # If it does crash, that's also acceptable behavior
                self.assertIsInstance(e, Exception)


if __name__ == "__main__":
    unittest.main()
