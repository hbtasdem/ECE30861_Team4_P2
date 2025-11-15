import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the path so we can import bus_factor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src/metrics"))

from bus_factor_score import bus_factor_score, get_huggingface_contributors  # noqa: E402


class TestBusFactorScore(unittest.TestCase):
    """Unit tests for bus_factor_score function with timing measurements."""

    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        self.test_models = [
            "moonshotai/Kimi-K2-Instruct-0905",
            "microsoft/CodeBERT-base",
            "bert-base-uncased",
            "microsoft/DialoGPT-medium",
        ]

        # Known expected contributor counts (manually verified)
        self.expected_contributors = {
            "moonshotai/Kimi-K2-Instruct-0905": 5,
            "microsoft/CodeBERT-base": 3,
            "bert-base-uncased": 14,
            "microsoft/DialoGPT-medium": 6,
        }

    def test_bus_factor_score_timing(self) -> None:
        """Test bus_factor_score function and measure execution time."""
        print("\n" + "=" * 60)
        print("BUS FACTOR SCORE TIMING TESTS")
        print("=" * 60)

        for model_id in self.test_models:
            print(f"\nTesting model: {model_id}")

            start_time = time.time()
            result = bus_factor_score(model_id)
            end_time = time.time()

            execution_time = end_time - start_time

            print(f"  Result: {result[0]} contributors")
            print(f"  Execution time: {execution_time:.3f} seconds")

            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
            contributors, latency = result
            self.assertIsInstance(contributors, int)
            self.assertIsInstance(latency, float)
            self.assertGreaterEqual(contributors, 0)
            self.assertGreaterEqual(latency, 0)

            self.assertLess(
                execution_time, 10.0, f"Function took too long: {execution_time:.3f}s"
            )

    def test_bus_factor_score_correctness(self) -> None:
        """Test that bus_factor_score returns correct contributor counts."""
        print("\n" + "=" * 60)
        print("BUS FACTOR SCORE CORRECTNESS TESTS")
        print("=" * 60)

        for model_id in self.test_models:
            print(f"\nTesting model: {model_id}")

            start_time = time.time()
            actual_result = bus_factor_score(model_id)
            end_time = time.time()

            expected_result = self.expected_contributors.get(model_id, "Unknown")
            execution_time = end_time - start_time

            print(f"  Expected: {expected_result} contributors")
            print(f"  Actual: {actual_result[0]} contributors")
            print(f"  Execution time: {execution_time:.3f} seconds")

            contributors, latency = actual_result
            self.assertEqual(
                contributors,
                expected_result,
                f"Contributor count mismatch for {model_id}. "
                f"Expected: {expected_result}, "
                f"Got: {contributors}",
            )

            self.assertIsInstance(contributors, int)
            self.assertGreaterEqual(contributors, 0)
            self.assertIsInstance(latency, float)
            self.assertGreaterEqual(latency, 0)

    def test_get_huggingface_contributors_timing(self) -> None:
        """Test get_huggingface_contributors function and measure execution."""
        print("\n" + "=" * 60)
        print("HUGGING FACE CONTRIBUTORS TIMING TESTS")
        print("=" * 60)

        for model_id in self.test_models:
            print(f"\nTesting model: {model_id}")

            start_time = time.time()
            result = get_huggingface_contributors(model_id)
            end_time = time.time()

            execution_time = end_time - start_time

            print(f"  Result: {result} contributors")
            print(f"  Execution time: {execution_time:.3f} seconds")

            self.assertIsInstance(result, int)
            self.assertGreaterEqual(result, 0)

    def test_invalid_model(self) -> None:
        """Test that invalid model IDs return 0."""
        print("\n" + "=" * 60)
        print("INVALID MODEL TESTS")
        print("=" * 60)

        invalid_models = [
            "invalid/model-that-does-not-exist",
            "nonexistent/author",
            "fake/model/with/slashes",
            "",
        ]

        for model_id in invalid_models:
            print(f"\nTesting invalid model: '{model_id}'")

            start_time = time.time()
            result = bus_factor_score(model_id)
            end_time = time.time()

            execution_time = end_time - start_time
            print(f"  Result: {result[0]} contributors")
            print(f"  Execution time: {execution_time:.3f} seconds")

            contributors, latency = result
            self.assertEqual(contributors, 0)

    def test_performance_benchmark(self) -> None:
        """Run a performance benchmark with multiple iterations."""
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK")
        print("=" * 60)

        model_id = "moonshotai/Kimi-K2-Instruct-0905"
        iterations = 3

        print(f"Running {iterations} iterations for model: {model_id}")

        times = []
        for i in range(iterations):
            print(f"\nIteration {i+1}/{iterations}")

            start_time = time.time()
            result = bus_factor_score(model_id)
            end_time = time.time()

            execution_time = end_time - start_time
            times.append(execution_time)

            print(f"  Result: {result[0]} contributors")
            print(f"  Time: {execution_time:.3f} seconds")

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\nBenchmark Results:")
        print(f"  Average time: {avg_time:.3f} seconds")
        print(f"  Min time: {min_time:.3f} seconds")
        print(f"  Max time: {max_time:.3f} seconds")
        print(f"  All results: {[f'{t:.3f}s' for t in times]}")

        self.assertLess(avg_time, 5.0, "Average execution time too slow")
        self.assertLess(max_time, 10.0, "Maximum execution time too slow")

    # =========================
    # ADDED TESTS FOR EDGE CASES
    # =========================

    def test_regex_pattern_variations(self) -> None:
        """Ensure all regex contributor patterns are parsed correctly."""
        html_cases = [
            ("<span>15 contributors</span>", 15),
            ("some text contributors 12", 12),
            ('"contributors": 27', 27),
        ]

        for html, expected in html_cases:
            with patch("requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = html
                mock_get.return_value = mock_response

                result = get_huggingface_contributors("fake/model")
                self.assertEqual(result, expected)

    def test_requests_exception(self) -> None:
        """Simulate a requests exception and ensure 0 is returned."""
        with patch("requests.get", side_effect=Exception("Network error")):
            result = get_huggingface_contributors("any/model")
            self.assertEqual(result, 0)

    def test_no_match_returns_zero(self) -> None:
        """Ensure no regex match returns 0 contributors."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "no contributors here"
            mock_get.return_value = mock_response

            result = get_huggingface_contributors("fake/model")
            self.assertEqual(result, 0)

    def test_non_200_status_code(self) -> None:
        """Ensure non-200 status code returns 0 contributors."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_get.return_value = mock_response

            result = get_huggingface_contributors("fake/model")
            self.assertEqual(result, 0)

    def test_invalid_number_match(self) -> None:
        """Ensure invalid number strings are ignored safely."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '<span>"contributors": notanumber</span>'
            mock_get.return_value = mock_response

            result = get_huggingface_contributors("fake/model")
            self.assertEqual(result, 0)


def run_timing_tests() -> bool:
    """Run all tests with detailed timing information."""
    print("Starting Bus Factor Score Unit Tests with Timing...")
    print("=" * 80)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestBusFactorScore)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    success_rate = (
        (result.testsRun - len(result.failures) - len(result.errors))
        / result.testsRun
        * 100
    )
    print(f"Success rate: {success_rate:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_timing_tests()
    sys.exit(0 if success else 1)
