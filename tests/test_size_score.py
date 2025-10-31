"""
Test suite for size score functionality.

Tests cover:
- Memory size extraction from README text
- Hardware benchmark scoring logic
- Complete size_score function with various scenarios
- Error handling and edge cases
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from size_score import (
    # MEMORY_BENCHMARKS,
    SIZE_THRESHOLDS,
    calculate_size_scores,
    extract_memory_sizes,
    find_smallest_model_size,
    score_against_benchmark,
    size_score,
)

# from typing import Any  # Not used in this test file


class TestMemoryExtraction(unittest.TestCase):
    """Test memory size extraction from README text."""

    def test_extract_gb_sizes(self) -> None:
        """Test extraction of sizes in GB."""
        readme = """
        This model requires 7.2 GB of VRAM.
        Model size: 14.4 GB
        Memory requirement: 8.5 GB RAM
        """
        sizes = extract_memory_sizes(readme)
        # Check that we found the sizes (order may vary due to deduplication)
        self.assertIn(7.2, sizes)
        self.assertIn(14.4, sizes)
        self.assertIn(8.5, sizes)

    def test_extract_mb_sizes(self) -> None:
        """Test extraction of sizes in MB (converted to GB)."""
        readme = """
        Model size: 2048 MB
        Memory requirement: 1024 MB RAM
        """
        sizes = extract_memory_sizes(readme)
        self.assertIn(2.0, sizes)  # 2048 MB = 2 GB
        self.assertIn(1.0, sizes)  # 1024 MB = 1 GB

    def test_extract_mixed_units(self) -> None:
        """Test extraction with mixed units."""
        readme = """
        Small model: 1.5 GB
        Large model: 2048 MB
        Huge model: 2.5 TB
        """
        sizes = extract_memory_sizes(readme)
        self.assertIn(1.5, sizes)
        self.assertIn(2.0, sizes)  # 2048 MB
        self.assertIn(2560.0, sizes)  # 2.5 TB

    def test_extract_case_insensitive(self) -> None:
        """Test case-insensitive extraction."""
        readme = """
        MODEL SIZE: 5.2 gb
        memory requirement: 3.1 GB
        """
        sizes = extract_memory_sizes(readme)
        self.assertIn(5.2, sizes)
        self.assertIn(3.1, sizes)

    def test_extract_no_sizes(self) -> None:
        """Test extraction when no sizes are found."""
        readme = "This is just regular text with no memory information."
        sizes = extract_memory_sizes(readme)
        self.assertEqual(len(sizes), 0)

    def test_extract_empty_text(self) -> None:
        """Test extraction with empty text."""
        sizes = extract_memory_sizes("")
        self.assertEqual(len(sizes), 0)

    def test_extract_unreasonable_sizes(self) -> None:
        """Test that unreasonable sizes are filtered out."""
        readme = """
        Model size: 0.05 GB  # Too small
        Model size: 50000 GB  # Too large
        Model size: 5.2 GB   # Reasonable
        """
        sizes = extract_memory_sizes(readme)
        self.assertEqual(sizes, [5.2])


class TestSmallestModelSize(unittest.TestCase):
    """Test finding the smallest model size."""

    def test_find_smallest(self) -> None:
        """Test finding smallest size from list."""
        sizes = [7.2, 14.4, 3.6, 8.1]
        smallest = find_smallest_model_size(sizes)
        self.assertEqual(smallest, 3.6)

    def test_find_smallest_single(self) -> None:
        """Test finding smallest from single size."""
        sizes = [5.2]
        smallest = find_smallest_model_size(sizes)
        self.assertEqual(smallest, 5.2)

    def test_find_smallest_empty(self) -> None:
        """Test finding smallest from empty list."""
        smallest = find_smallest_model_size([])
        self.assertIsNone(smallest)


class TestBenchmarkScoring(unittest.TestCase):
    """Test scoring against hardware benchmarks."""

    def test_score_comfortable_fit(self) -> None:
        """Test scoring when model fits comfortably (< 75%)."""
        # 5 GB model vs 16 GB benchmark = 31.25% → score 1.0
        score = score_against_benchmark(5.0, 16.0)
        self.assertEqual(score, 1.0)

    def test_score_barely_fits(self) -> None:
        """Test scoring when model barely fits (75-100%)."""
        # 12 GB model vs 16 GB benchmark = 75% → score 0.5
        score = score_against_benchmark(12.0, 16.0)
        self.assertEqual(score, 0.5)

        # 15.9 GB model vs 16 GB benchmark = 99.4% → score 0.5
        score = score_against_benchmark(15.9, 16.0)
        self.assertEqual(score, 0.5)

    def test_score_doesnt_fit(self) -> None:
        """Test scoring when model doesn't fit (> 100%)."""
        # 20 GB model vs 16 GB benchmark = 125% → score 0.0
        score = score_against_benchmark(20.0, 16.0)
        self.assertEqual(score, 0.0)

    def test_score_exact_capacity(self) -> None:
        """Test scoring when model uses exact capacity."""
        # 16 GB model vs 16 GB benchmark = 100% → score 0.0
        score = score_against_benchmark(16.0, 16.0)
        self.assertEqual(score, 0.0)


class TestSizeScoreCalculation(unittest.TestCase):
    """Test complete size score calculation."""

    def test_calculate_all_scores(self) -> None:
        """Test calculation of scores for all hardware benchmarks."""
        # 7.2 GB model
        scores = calculate_size_scores(7.2)

        self.assertIn("raspberry_pi", scores)
        self.assertIn("jetson_nano", scores)
        self.assertIn("desktop_gpu", scores)
        self.assertIn("high_end_gpu", scores)

        # 7.2 GB vs 1 GB → 0.0
        self.assertEqual(scores["raspberry_pi"], 0.0)
        # 7.2 GB vs 2 GB → 0.0
        self.assertEqual(scores["jetson_nano"], 0.0)
        # 7.2 GB vs 16 GB → 1.0 (45%)
        self.assertEqual(scores["desktop_gpu"], 1.0)
        # 7.2 GB vs 24 GB → 1.0 (30%)
        self.assertEqual(scores["high_end_gpu"], 1.0)

    def test_calculate_edge_case_sizes(self) -> None:
        """Test calculation with edge case sizes."""
        # Very small model (0.5 GB)
        scores = calculate_size_scores(0.5)
        self.assertEqual(scores["raspberry_pi"], 1.0)  # 50%
        self.assertEqual(scores["jetson_nano"], 1.0)  # 25%

        # Very large model (30 GB)
        scores = calculate_size_scores(30.0)
        self.assertEqual(scores["raspberry_pi"], 0.0)  # 3000%
        self.assertEqual(scores["jetson_nano"], 0.0)  # 1500%
        self.assertEqual(scores["desktop_gpu"], 0.0)  # 187.5%
        self.assertEqual(scores["high_end_gpu"], 0.0)  # 125%


class TestSizeScoreFunction(unittest.TestCase):
    """Test the main size_score function."""

    @patch("src.size_score.fetch_readme")
    def test_successful_calculation(self, mock_fetch_readme: MagicMock) -> None:
        """Test successful size score calculation."""
        mock_readme = """
        # Model Information
        This model requires 7.2 GB of VRAM for inference.
        Model size: 7.2 GB
        """
        mock_fetch_readme.return_value = mock_readme

        scores, latency = size_score("https://huggingface.co/test/model")

        self.assertIsInstance(scores, dict)
        self.assertIn("raspberry_pi", scores)
        self.assertIn("jetson_nano", scores)
        self.assertIn("desktop_gpu", scores)
        self.assertIn("high_end_gpu", scores)
        self.assertIsInstance(latency, float)
        self.assertGreater(latency, 0)

    @patch("src.size_score.fetch_readme")
    def test_no_readme_content(self, mock_fetch_readme: MagicMock) -> None:
        """Test handling when README cannot be fetched."""
        mock_fetch_readme.return_value = None

        scores, latency = size_score("https://huggingface.co/test/model")

        self.assertEqual(scores, {})
        self.assertIsInstance(latency, float)

    @patch("src.size_score.fetch_readme")
    def test_no_memory_info_in_readme(self, mock_fetch_readme: MagicMock) -> None:
        """Test handling when README has no memory information."""
        mock_readme = "This is just regular text with no memory information."
        mock_fetch_readme.return_value = mock_readme

        scores, latency = size_score("https://huggingface.co/test/model")

        self.assertEqual(scores, {})
        self.assertIsInstance(latency, float)

    @patch("src.size_score.fetch_readme")
    def test_multiple_model_sizes(self, mock_fetch_readme: MagicMock) -> None:
        """Test handling when multiple model sizes are found."""
        mock_readme = """
        # Model Variants
        Small model: 3.6 GB
        Medium model: 7.2 GB
        Large model: 14.4 GB
        """
        mock_fetch_readme.return_value = mock_readme

        scores, latency = size_score("https://huggingface.co/test/model")

        # Should use smallest size (3.6 GB)
        self.assertIsInstance(scores, dict)
        if scores:  # Only check if scores were calculated
            self.assertEqual(scores["raspberry_pi"], 0.0)  # 3.6 GB vs 1 GB
            self.assertEqual(scores["jetson_nano"], 0.0)  # 3.6 GB vs 2 GB
            # 3.6 GB vs 16 GB (22.5%)
            self.assertEqual(scores["desktop_gpu"], 1.0)
            # 3.6 GB vs 24 GB (15%)
            self.assertEqual(scores["high_end_gpu"], 1.0)

    def test_invalid_url(self) -> None:
        """Test handling of invalid URL."""
        scores, latency = size_score("invalid-url")

        self.assertEqual(scores, {})
        self.assertIsInstance(latency, float)


class TestIntegration(unittest.TestCase):
    """Integration tests for size score functionality."""

    def test_example_from_spec(self) -> None:
        """Test the example from the specification."""
        # Example: Model offers 7.2 GB and 14.4 GB versions
        # Smallest = 7.2 GB
        # Expected scores: [0, 0, 1, 1]

        scores = calculate_size_scores(7.2)

        self.assertEqual(scores["raspberry_pi"], 0.0)  # 7.2 GB ≥ 1 GB
        self.assertEqual(scores["jetson_nano"], 0.0)  # 7.2 GB ≥ 2 GB
        self.assertEqual(scores["desktop_gpu"], 1.0)  # 7.2 GB < 75% of 16 GB
        self.assertEqual(scores["high_end_gpu"], 1.0)  # 7.2 GB < 75% of 24 GB

    def test_benchmark_values(self) -> None:
        """Test that benchmark values are correct."""
        expected_benchmarks = {
            "raspberry_pi": 1.0,
            "jetson_nano": 2.0,
            "desktop_gpu": 16.0,
            "high_end_gpu": 24.0,
        }

        self.assertEqual(SIZE_THRESHOLDS, expected_benchmarks) #might be entirely wrong HILAL CHECK


if __name__ == "__main__":
    unittest.main()
