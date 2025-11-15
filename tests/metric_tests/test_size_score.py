import os
import sys
from typing import Any, Dict, Tuple
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "metrics"))

import size_score  # noqa: E402


# Test data for different model scenarios
MOCK_MODEL_INFO_SMALL = MagicMock()
MOCK_MODEL_INFO_SMALL.safetensors = MagicMock()
MOCK_MODEL_INFO_SMALL.safetensors.total = 500 * 1024**3  # 500MB in bytes

MOCK_MODEL_INFO_MEDIUM = MagicMock()
MOCK_MODEL_INFO_MEDIUM.safetensors = MagicMock()
MOCK_MODEL_INFO_MEDIUM.safetensors.total = 2 * 1024**3  # 2GB in bytes

MOCK_MODEL_INFO_LARGE = MagicMock()
MOCK_MODEL_INFO_LARGE.safetensors = MagicMock()
MOCK_MODEL_INFO_LARGE.safetensors.total = 10 * 1024**3  # 10GB in bytes

MOCK_MODEL_INFO_NO_SAFETENSORS = MagicMock()
MOCK_MODEL_INFO_NO_SAFETENSORS.safetensors = None


class TestExtractModelId:
    """Tests for extract_model_id_from_url function."""

    @pytest.mark.parametrize(
        "input_url,expected_output",
        [
            (
                "https://huggingface.co/google-bert/bert-base-uncased",
                "google-bert/bert-base-uncased",
            ),
            (
                "https://huggingface.co/openai/whisper-tiny?param=value",
                "openai/whisper-tiny",
            ),
            (
                "huggingface.co/microsoft/DialoGPT-medium",
                "microsoft/DialoGPT-medium",
            ),
            ("google-bert/bert-base-uncased", "google-bert/bert-base-uncased"),
            ("openai/whisper-tiny", "openai/whisper-tiny"),
            ("simple-model-name", "simple-model-name"),
        ],
    )
    def test_extract_model_id_variations(
        self, input_url: str, expected_output: str
    ) -> None:
        """Test extraction of model ID from various URL formats."""
        result = size_score.extract_model_id_from_url(input_url)
        assert result == expected_output

    def test_extract_model_id_with_protocol(self) -> None:
        """Test URL with https protocol."""
        url = "https://huggingface.co/meta-llama/Llama-2-7b"
        result = size_score.extract_model_id_from_url(url)
        assert result == "meta-llama/Llama-2-7b"


class TestEstimateModelMemory:
    """Tests for estimate_model_memory function."""

    def test_estimate_model_memory_with_file_size_gpt(self) -> None:
        """Test memory estimation using file size for GPT models."""
        result = size_score.estimate_model_memory("gpt-custom", file_size_gb=1.0)
        assert result == 1.0 * 12  # GPT has 12x multiplier

    def test_estimate_model_memory_generic_fallback(self) -> None:
        """Test fallback memory estimation for unknown model types."""
        result = size_score.estimate_model_memory("unknown-model", file_size_gb=1.5)
        assert result == 1.5 * 10  # Default 10x multiplier

    def test_estimate_model_memory_no_info(self) -> None:
        """Test memory estimation with no information."""
        result = size_score.estimate_model_memory("completely-unknown-model")
        assert result == 1.0  # Default fallback


class TestCalculateDeviceScores:
    """Tests for calculate_device_scores function."""

    def test_calculate_device_scores_tiny_model(self) -> None:
        """Test device scores for a tiny model (0.5GB)."""
        scores = size_score.calculate_device_scores(0.5)
        assert scores["raspberry_pi"] == 0.75  # 1.0 - (0.5 / 2.0)
        assert scores["jetson_nano"] == 0.88  # 1.0 - (0.5 / 4.0)
        assert scores["desktop_pc"] == 0.97  # 1.0 - (0.5 / 16.0)
        assert scores["aws_server"] == 1.0

    def test_calculate_device_scores_medium_model(self) -> None:
        """Test device scores for a medium model (2GB)."""
        scores = size_score.calculate_device_scores(2.0)
        assert scores["raspberry_pi"] == 0.0  # 1.0 - (2.0 / 2.0)
        assert scores["jetson_nano"] == 0.5  # 1.0 - (2.0 / 4.0)
        assert scores["desktop_pc"] == 0.88  # 1.0 - (2.0 / 16.0)
        assert scores["aws_server"] == 1.0

    def test_calculate_device_scores_large_model(self) -> None:
        """Test device scores for a large model (10GB)."""
        scores = size_score.calculate_device_scores(10.0)
        assert scores["raspberry_pi"] == 0.0  # Exceeds threshold
        assert scores["jetson_nano"] == 0.0  # Exceeds threshold
        assert scores["desktop_pc"] == 0.38  # 1.0 - (10.0 / 16.0)
        assert scores["aws_server"] == 1.0

    def test_calculate_device_scores_huge_model(self) -> None:
        """Test device scores for a huge model (20GB)."""
        scores = size_score.calculate_device_scores(20.0)
        assert scores["raspberry_pi"] == 0.0
        assert scores["jetson_nano"] == 0.0
        assert scores["desktop_pc"] == 0.0  # Exceeds threshold
        assert scores["aws_server"] == 1.0

    def test_calculate_device_scores_zero_size(self) -> None:
        """Test device scores for zero size model."""
        scores = size_score.calculate_device_scores(0.0)
        assert scores["raspberry_pi"] == 1.0
        assert scores["jetson_nano"] == 1.0
        assert scores["desktop_pc"] == 1.0
        assert scores["aws_server"] == 1.0


class TestCalculateNetSizeScore:
    """Tests for calculate_net_size_score function."""

    def test_calculate_net_size_score_perfect(self) -> None:
        """Test net score calculation with perfect scores."""
        size_scores = {
            "raspberry_pi": 1.0,
            "jetson_nano": 1.0,
            "desktop_pc": 1.0,
            "aws_server": 1.0,
        }
        net_score = size_score.calculate_net_size_score(size_scores)
        assert net_score == 1.0

    def test_calculate_net_size_score_zero(self) -> None:
        """Test net score calculation with zero scores."""
        size_scores = {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.0,
            "desktop_pc": 0.0,
            "aws_server": 0.0,
        }
        net_score = size_score.calculate_net_size_score(size_scores)
        assert net_score == 0.0

    def test_calculate_net_size_score_mixed(self) -> None:
        """Test net score calculation with mixed scores."""
        size_scores = {
            "raspberry_pi": 0.5,
            "jetson_nano": 0.75,
            "desktop_pc": 0.9,
            "aws_server": 1.0,
        }
        # Expected: 0.5*0.35 + 0.75*0.25 + 0.9*0.20 + 1.0*0.20
        # = 0.175 + 0.1875 + 0.18 + 0.20 = 0.7425
        net_score = size_score.calculate_net_size_score(size_scores)
        assert 0.74 <= net_score <= 0.75

    def test_calculate_net_size_score_weights_sum(self) -> None:
        """Test that weights sum to 1.0."""
        total_weight = sum(size_score.SIZE_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.01


class TestCalculateSizeScores:
    """Tests for calculate_size_scores function."""

    @patch("size_score.HfApi")
    def test_calculate_size_scores_with_api_data(self, mock_hf_api: Any) -> None:
        """Test size score calculation with API data available."""
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.return_value = MOCK_MODEL_INFO_SMALL
        mock_hf_api.return_value = mock_api_instance

        scores, net_score, latency = size_score.calculate_size_scores(
            "test-model/bert-base"
        )

        assert isinstance(scores, dict)
        assert "raspberry_pi" in scores
        assert "jetson_nano" in scores
        assert "desktop_pc" in scores
        assert "aws_server" in scores
        assert 0.0 <= net_score <= 1.0
        assert latency >= 0

    @patch("size_score.HfApi")
    def test_calculate_size_scores_api_error(self, mock_hf_api: Any) -> None:
        """Test size score calculation when API fails."""
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api_instance

        scores, net_score, latency = size_score.calculate_size_scores(
            "test-model/bert-base"
        )

        # Should fall back to estimation
        assert isinstance(scores, dict)
        assert 0.0 <= net_score <= 1.0
        assert latency >= 0

    @patch("size_score.HfApi")
    def test_calculate_size_scores_no_safetensors(self, mock_hf_api: Any) -> None:
        """Test size score calculation when model has no safetensors."""
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.return_value = MOCK_MODEL_INFO_NO_SAFETENSORS
        mock_hf_api.return_value = mock_api_instance

        scores, net_score, latency = size_score.calculate_size_scores(
            "test-model/bert-base"
        )

        # Should fall back to estimation
        assert isinstance(scores, dict)
        assert 0.0 <= net_score <= 1.0
        assert latency >= 0

    @patch("size_score.HfApi")
    def test_calculate_size_scores_with_url(self, mock_hf_api: Any) -> None:
        """Test size score calculation with full URL."""
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.return_value = MOCK_MODEL_INFO_SMALL
        mock_hf_api.return_value = mock_api_instance

        scores, net_score, latency = size_score.calculate_size_scores(
            "https://huggingface.co/test-model/bert-base"
        )

        assert isinstance(scores, dict)
        assert 0.0 <= net_score <= 1.0
        assert latency >= 0


class TestSizeScoreMainFunction:
    """Tests for the main size_score function."""

    @patch("size_score.calculate_size_scores")
    def test_size_score_string_input(self, mock_calc: Any) -> None:
        """Test size_score with string model ID."""
        mock_calc.return_value = (
            {
                "raspberry_pi": 0.8,
                "jetson_nano": 0.9,
                "desktop_pc": 0.95,
                "aws_server": 1.0,
            },
            0.9,
            100,
        )

        scores, net_score, latency = size_score.size_score("test-model/bert-base")

        assert scores["raspberry_pi"] == 0.8
        assert net_score == 0.9
        assert latency == 100
        mock_calc.assert_called_once_with("test-model/bert-base")

    @patch("size_score.calculate_size_scores")
    def test_size_score_dict_input_with_model_id(self, mock_calc: Any) -> None:
        """Test size_score with dictionary input containing model_id."""
        mock_calc.return_value = (
            {
                "raspberry_pi": 0.7,
                "jetson_nano": 0.8,
                "desktop_pc": 0.9,
                "aws_server": 1.0,
            },
            0.85,
            150,
        )

        model_dict = {"model_id": "test-model/bert-base"}
        scores, net_score, latency = size_score.size_score(model_dict)

        assert net_score == 0.85
        mock_calc.assert_called_once_with("test-model/bert-base")

    @patch("size_score.calculate_size_scores")
    def test_size_score_dict_input_with_name(self, mock_calc: Any) -> None:
        """Test size_score with dictionary input containing name."""
        mock_calc.return_value = (
            {
                "raspberry_pi": 0.6,
                "jetson_nano": 0.7,
                "desktop_pc": 0.85,
                "aws_server": 1.0,
            },
            0.8,
            120,
        )

        model_dict = {"name": "test-model/gpt2"}
        scores, net_score, latency = size_score.size_score(model_dict)

        assert net_score == 0.8
        mock_calc.assert_called_once_with("test-model/gpt2")

    @patch("size_score.calculate_size_scores")
    def test_size_score_dict_input_with_url(self, mock_calc: Any) -> None:
        """Test size_score with dictionary input containing url."""
        mock_calc.return_value = (
            {
                "raspberry_pi": 0.5,
                "jetson_nano": 0.6,
                "desktop_pc": 0.8,
                "aws_server": 1.0,
            },
            0.75,
            130,
        )

        model_dict = {"url": "https://huggingface.co/test-model/whisper-tiny"}
        scores, net_score, latency = size_score.size_score(model_dict)

        assert net_score == 0.75
        mock_calc.assert_called_once()

    def test_size_score_empty_dict(self) -> None:
        """Test size_score with empty dictionary."""
        scores, net_score, latency = size_score.size_score({})

        assert scores == {}
        assert net_score == 0.0
        assert latency == 0

    @patch("size_score.calculate_size_scores")
    def test_size_score_exception_handling(self, mock_calc: Any) -> None:
        """Test size_score handles exceptions gracefully."""
        mock_calc.side_effect = Exception("Unexpected error")

        scores, net_score, latency = size_score.size_score("test-model/bert-base")

        assert scores == {}
        assert net_score == 0.0
        assert latency == 0


class TestIntegration:
    """Integration tests for complete workflows."""

    @patch("size_score.HfApi")
    @pytest.mark.parametrize(
        "model_id,expected_min_net_score",
        [
            ("openai/whisper-tiny", 0.7),  # Small model, good scores
            ("bert-base-uncased", 0.4),  # Medium model
            ("llama-7b", 0.2),  # Large model, only AWS scores well
        ],
    )
    def test_end_to_end_scoring(
        self, mock_hf_api: Any, model_id: str, expected_min_net_score: float
    ) -> None:
        """Test complete scoring workflow for different model sizes."""
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.side_effect = Exception("No API")
        mock_hf_api.return_value = mock_api_instance

        scores, net_score, latency = size_score.size_score(model_id)

        assert isinstance(scores, dict)
        assert len(scores) == 4
        assert net_score >= expected_min_net_score
        assert latency >= 0
        assert 0.0 <= net_score <= 1.0

    @patch("size_score.HfApi")
    def test_latency_measurement(self, mock_hf_api: Any) -> None:
        """Test that latency is properly measured."""
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.return_value = MOCK_MODEL_INFO_SMALL
        mock_hf_api.return_value = mock_api_instance

        _, _, latency = size_score.size_score("test-model/bert-base")

        assert isinstance(latency, int)
        assert latency >= 0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_device_score_at_threshold(self) -> None:
        """Test device scores exactly at threshold values."""
        # Raspberry Pi threshold: 2GB
        scores = size_score.calculate_device_scores(2.0)
        assert scores["raspberry_pi"] == 0.0

        # Jetson Nano threshold: 4GB
        scores = size_score.calculate_device_scores(4.0)
        assert scores["jetson_nano"] == 0.0

        # Desktop PC threshold: 16GB
        scores = size_score.calculate_device_scores(16.0)
        assert scores["desktop_pc"] == 0.0

    def test_device_score_just_below_threshold(self) -> None:
        """Test device scores just below threshold values."""
        # Just below Raspberry Pi threshold
        scores = size_score.calculate_device_scores(1.99)
        assert scores["raspberry_pi"] > 0.0

    def test_device_score_far_above_threshold(self) -> None:
        """Test device scores far above threshold values."""
        scores = size_score.calculate_device_scores(100.0)
        assert scores["raspberry_pi"] == 0.0
        assert scores["jetson_nano"] == 0.0
        assert scores["desktop_pc"] == 0.0
        assert scores["aws_server"] == 1.0  # Always 1.0

    def test_aws_server_always_one(self) -> None:
        """Test that AWS server always scores 1.0 regardless of size."""
        for size_gb in [0.1, 1.0, 10.0, 100.0, 1000.0]:
            scores = size_score.calculate_device_scores(size_gb)
            assert scores["aws_server"] == 1.0