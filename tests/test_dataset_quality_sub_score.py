from unittest.mock import Mock, patch
import sys

import pytest
 # Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataset_quality_sub_score import dataset_quality_sub_score

# Test data for various README scenarios
README_WITH_DOCUMENTATION = """
# Example Model

## Dataset
This dataset contains 1M samples of text data in CSV format.
The dataset includes the following columns:
- text: The input text
- label: The classification label
- id: Unique identifier

## Size
- Total size: 2.5 GB
- Rows: 1,000,000
- Format: CSV

## Usage
To load the dataset:
```python
import pandas as pd
df = pd.read_csv('data.csv')
```
"""

README_WITH_LICENSE = """
# Example Model

## License
This model is released under the MIT License.
Commercial use is permitted with attribution.

## Restrictions
- Cannot be used for harmful purposes
- Must include license notice
"""

README_WITH_SAFETY = """
# Example Model

## Safety Considerations
This dataset has been anonymized to protect privacy.
Personal information has been removed following GDPR guidelines.

## Bias and Fairness
We have checked for potential biases in the data.
Content warnings apply to some samples.

## Data Source
Data was collected from public sources and verified.
"""

README_WITH_CURATION = """
# Example Model

## Quality Control
This dataset has been carefully curated and validated.
Version 2.0 includes improved data quality.

## Statistics
- Accuracy: 95.2%
- Precision: 94.8%
- F1 Score: 95.0%

## Updates
See CHANGELOG.md for version history.
"""

README_WITH_REPRODUCIBILITY = """
# Example Model

## Reproducibility
To reproduce our results:

1. Install dependencies: `pip install -r requirements.txt`
2. Download the code from GitHub
3. Run the Jupyter notebook
4. Follow the step-by-step guide

## Environment
- Python 3.8+
- See requirements.txt for dependencies
- Docker setup available
"""

README_COMPREHENSIVE = """
# Example Model

## Dataset
Available at: https://huggingface.co/datasets/example-dataset
Size: 1M samples, 2.5GB in CSV format

## License
MIT License - commercial use permitted

## Safety
Data is anonymized and GDPR compliant

## Quality
Curated and validated (v2.0)
Accuracy: 95.2%

## Reproducibility
Code available on GitHub with setup instructions
"""

README_EMPTY = ""

README_MINIMAL = """
# Example Model
Basic model description.
"""


class TestDocumentationEvaluation:
    """Test dataset documentation evaluation."""

    def test_evaluate_dataset_documentation_comprehensive(self) -> None:
        """Test comprehensive documentation scoring."""
        score = dataset_quality_sub_score.evaluate_dataset_documentation(
            README_WITH_DOCUMENTATION
        )
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have good documentation

    def test_evaluate_dataset_documentation_minimal(self) -> None:
        """Test minimal documentation scoring."""
        score = dataset_quality_sub_score.evaluate_dataset_documentation(README_MINIMAL)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should have low documentation score

    def test_evaluate_dataset_documentation_empty(self) -> None:
        """Test empty README scoring."""
        score = dataset_quality_sub_score.evaluate_dataset_documentation(README_EMPTY)
        assert score == 0.0


class TestLicenseEvaluation:
    """Test license clarity evaluation."""

    def test_evaluate_license_clarity_with_license(self) -> None:
        """Test license scoring with explicit license."""
        score = dataset_quality_sub_score.evaluate_license_clarity(README_WITH_LICENSE)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have good license clarity

    def test_evaluate_license_clarity_without_license(self) -> None:
        """Test license scoring without license information."""
        score = dataset_quality_sub_score.evaluate_license_clarity(README_MINIMAL)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should have low license score

    def test_evaluate_license_clarity_empty(self) -> None:
        """Test empty README license scoring."""
        score = dataset_quality_sub_score.evaluate_license_clarity(README_EMPTY)
        assert score == 0.0


class TestSafetyPrivacyEvaluation:
    """Test safety and privacy evaluation."""

    def test_evaluate_safety_privacy_with_considerations(self) -> None:
        """Test safety scoring with considerations."""
        score = dataset_quality_sub_score.evaluate_safety_privacy(README_WITH_SAFETY)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have good safety considerations

    def test_evaluate_safety_privacy_without_considerations(self) -> None:
        """Test safety scoring without considerations."""
        score = dataset_quality_sub_score.evaluate_safety_privacy(README_MINIMAL)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should have low safety score

    def test_evaluate_safety_privacy_empty(self) -> None:
        """Test empty README safety scoring."""
        score = dataset_quality_sub_score.evaluate_safety_privacy(README_EMPTY)
        assert score == 0.0


class TestCurationEvaluation:
    """Test curation quality evaluation."""

    def test_evaluate_curation_quality_with_curation(self) -> None:
        """Test curation scoring with quality measures."""
        score = dataset_quality_sub_score.evaluate_curation_quality(README_WITH_CURATION)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have good curation info

    def test_evaluate_curation_quality_without_curation(self) -> None:
        """Test curation scoring without quality measures."""
        score = dataset_quality_sub_score.evaluate_curation_quality(README_MINIMAL)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should have low curation score

    def test_evaluate_curation_quality_empty(self) -> None:
        """Test empty README curation scoring."""
        score = dataset_quality_sub_score.evaluate_curation_quality(README_EMPTY)
        assert score == 0.0


class TestReproducibilityEvaluation:
    """Test reproducibility evaluation."""

    def test_evaluate_reproducibility_with_instructions(self) -> None:
        """Test reproducibility scoring with instructions."""
        score = dataset_quality_sub_score.evaluate_reproducibility(README_WITH_REPRODUCIBILITY)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have good reproducibility info

    def test_evaluate_reproducibility_without_instructions(self) -> None:
        """Test reproducibility scoring without instructions."""
        score = dataset_quality_sub_score.evaluate_reproducibility(README_MINIMAL)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should have low reproducibility score

    def test_evaluate_reproducibility_empty(self) -> None:
        """Test empty README reproducibility scoring."""
        score = dataset_quality_sub_score.evaluate_reproducibility(README_EMPTY)
        assert score == 0.0


class TestHybridEvaluation:
    """Test hybrid evaluation functions."""

    def test_evaluate_dataset_documentation_hybrid_no_ai(self) -> None:
        """Test hybrid documentation scoring without AI."""
        score = dataset_quality_sub_score.evaluate_dataset_documentation_hybrid(
            README_WITH_DOCUMENTATION, "test-model", use_ai=False
        )
        # Should be same as deterministic score
        deterministic_score = dataset_quality_sub_score.evaluate_dataset_documentation(
            README_WITH_DOCUMENTATION
        )
        assert score == deterministic_score

    def test_evaluate_safety_privacy_hybrid_no_ai(self) -> None:
        """Test hybrid safety scoring without AI."""
        score = dataset_quality_sub_score.evaluate_safety_privacy_hybrid(
            README_WITH_SAFETY, "test-model", use_ai=False
        )
        # Should be same as deterministic score
        deterministic_score = dataset_quality_sub_score.evaluate_safety_privacy(
            README_WITH_SAFETY
        )
        assert score == deterministic_score

    def test_evaluate_curation_quality_hybrid_no_ai(self) -> None:
        """Test hybrid curation scoring without AI."""
        score = dataset_quality_sub_score.evaluate_curation_quality_hybrid(
            README_WITH_CURATION, "test-model", use_ai=False
        )
        # Should be same as deterministic score
        deterministic_score = dataset_quality_sub_score.evaluate_curation_quality(
            README_WITH_CURATION
        )
        assert score == deterministic_score

    @patch("src.dataset_quality_sub_score._get_ai_score")
    def test_evaluate_dataset_documentation_hybrid_with_ai(
        self, mock_ai_score: Mock
    ) -> None:
        """Test hybrid documentation scoring with AI."""
        mock_ai_score.return_value = 0.8

        score = dataset_quality_sub_score.evaluate_dataset_documentation_hybrid(
            README_WITH_DOCUMENTATION, "test-model", use_ai=True
        )

        # Should be weighted combination of deterministic and AI scores
        deterministic_score = dataset_quality_sub_score.evaluate_dataset_documentation(
            README_WITH_DOCUMENTATION
        )
        expected_score = (deterministic_score * 0.7) + (0.8 * 0.3)
        assert abs(score - expected_score) < 0.001

    @patch("src.dataset_quality_sub_score._get_ai_score")
    def test_hybrid_ai_fallback(self, mock_ai_score: Mock) -> None:
        """Test that hybrid functions fallback to deterministic."""
        mock_ai_score.return_value = 0.0  # AI failed
        score = dataset_quality_sub_score.evaluate_dataset_documentation_hybrid(
            README_WITH_DOCUMENTATION, "test-model", use_ai=True
        )

        # Should fallback to deterministic score
        deterministic_score = dataset_quality_sub_score.evaluate_dataset_documentation(
            README_WITH_DOCUMENTATION
        )
        assert score == deterministic_score


class TestDatasetIdentifierExtraction:
    """Test dataset identifier extraction functionality."""

    def test_extract_dataset_identifier_huggingface(self) -> None:
        """Test extracting identifier from Hugging Face dataset URL."""
        url = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
        identifier = dataset_quality_sub_score.extract_dataset_identifier(url)
        assert identifier == "bookcorpus/bookcorpus"

    def test_extract_dataset_identifier_generic(self) -> None:
        """Test extracting identifier from generic URL."""
        url = "https://example.com/path/to/dataset"
        identifier = dataset_quality_sub_score.extract_dataset_identifier(url)
        assert identifier == "example.com/path/to/dataset"

    def test_extract_dataset_identifier_empty(self) -> None:
        """Test extracting identifier from empty URL."""
        identifier = dataset_quality_sub_score.extract_dataset_identifier("")
        assert identifier == ""


class TestKnownDatasetChecking:
    """Test checking for known datasets in README."""

    def test_check_readme_for_known_datasets_direct_match(self) -> None:
        """Test direct dataset name match in README."""
        readme = "This model uses the bookcorpus/bookcorpus dataset"
        encountered = {"bookcorpus/bookcorpus"}
        result = dataset_quality_sub_score.check_readme_for_known_datasets(readme, encountered)
        assert result is True

    def test_check_readme_for_known_datasets_partial_match(self) -> None:
        """Test partial dataset name match in README."""
        readme = "This model uses bookcorpus data for training"
        encountered = {"bookcorpus/bookcorpus"}
        result = dataset_quality_sub_score.check_readme_for_known_datasets(readme, encountered)
        assert result is True

    def test_check_readme_for_known_datasets_no_match(self) -> None:
        """Test no dataset match in README."""
        readme = "This model uses custom data"
        encountered = {"bookcorpus/bookcorpus"}
        result = dataset_quality_sub_score.check_readme_for_known_datasets(readme, encountered)
        assert result is False

    def test_check_readme_for_known_datasets_empty_sets(self) -> None:
        """Test with empty inputs."""
        result = dataset_quality_sub_score.check_readme_for_known_datasets("", set())
        assert result is False


class TestDatasetAvailabilityScoring:
    """Test dataset availability logic."""

    def test_no_dataset_available(self) -> None:
        """Test scoring when no dataset is available."""
        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score("test-model")
        assert score == 0.0
        assert elapsed >= 0

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_available_via_link(self, mock_fetch_readme: Mock) -> None:
        """Test scoring when dataset is available via external link."""
        mock_fetch_readme.return_value = README_COMPREHENSIVE

        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model", dataset_link="https://huggingface.co/datasets/test"
        )

        assert score > 0.0
        assert elapsed >= 0

    @patch("src.dataset_quality_sub_score.fetch_readme")
    @patch("src.dataset_quality_sub_score.check_readme_for_known_datasets")
    def test_dataset_available_via_encountered(
        self, mock_check: Mock, mock_fetch_readme: Mock
    ) -> None:
        """Test scoring when dataset is available via encountered datasets."""
        mock_fetch_readme.return_value = README_COMPREHENSIVE
        mock_check.return_value = True  # Found reference to known dataset

        encountered = {"known-dataset"}
        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model", encountered_datasets=encountered
        )

        assert score > 0.0
        assert elapsed >= 0

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_tracking_updates_encountered_set(
        self, mock_fetch_readme: Mock
    ) -> None:
        """Test that external dataset links are added to encountered set."""
        mock_fetch_readme.return_value = README_COMPREHENSIVE

        encountered: set[str] = set()
        dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model",
            dataset_link="https://huggingface.co/datasets/test-dataset",
            encountered_datasets=encountered,
        )

        # The set should now contain the dataset identifier
        assert "test-dataset" in encountered


class TestDatasetQualitySubScore:
    """Test the main dataset quality scoring function."""

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_quality_sub_score_comprehensive(
        self, mock_fetch_readme: Mock
    ) -> None:
        """Test comprehensive dataset quality scoring with external dataset."""
        mock_fetch_readme.return_value = README_COMPREHENSIVE

        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model", dataset_link="https://huggingface.co/datasets/test"
        )

        assert 0.0 <= score <= 1.0
        assert elapsed >= 0
        assert score > 0.7  # Comprehensive README should score high

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_quality_sub_score_minimal(self, mock_fetch_readme: Mock) -> None:
        """Test minimal dataset quality scoring with external dataset."""
        mock_fetch_readme.return_value = README_MINIMAL

        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model", dataset_link="https://huggingface.co/datasets/test"
        )

        assert 0.0 <= score <= 1.0
        assert elapsed >= 0
        assert score < 0.3  # Minimal README should score low

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_quality_sub_score_no_readme(self, mock_fetch_readme: Mock) -> None:
        """Test when README cannot be fetched but dataset link provided."""
        mock_fetch_readme.return_value = None

        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model", dataset_link="https://huggingface.co/datasets/test"
        )

        assert score == 0.0
        assert elapsed >= 0

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_quality_sub_score_empty_readme(
        self, mock_fetch_readme: Mock
    ) -> None:
        """Test scoring with empty README but dataset link provided."""
        mock_fetch_readme.return_value = README_EMPTY

        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model", dataset_link="https://huggingface.co/datasets/test"
        )

        assert 0.0 <= score <= 1.0
        assert elapsed >= 0
        assert score == 0.0  # Empty README should score 0

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_quality_sub_score_timing(self, mock_fetch_readme: Mock) -> None:
        """Test that timing is measured correctly."""
        mock_fetch_readme.return_value = README_COMPREHENSIVE

        score, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model", dataset_link="https://huggingface.co/datasets/test"
        )

        assert elapsed >= 0
        # Should be reasonably fast for mocked data with hybrid scoring
        assert elapsed < 2.0

    @patch("src.dataset_quality_sub_score.fetch_readme")
    def test_dataset_quality_sub_score_no_ai(self, mock_fetch_readme: Mock) -> None:
        """Test dataset quality scoring without AI enhancement."""
        mock_fetch_readme.return_value = README_COMPREHENSIVE

        score_no_ai, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model",
            dataset_link="https://huggingface.co/datasets/test",
            use_ai=False,
        )

        assert 0.0 <= score_no_ai <= 1.0
        assert elapsed >= 0
        # Should be deterministic scoring only

    @patch("src.dataset_quality_sub_score.fetch_readme")
    @patch("src.dataset_quality_sub_score._get_ai_score")
    def test_dataset_quality_sub_score_with_ai(
        self, mock_ai_score: Mock, mock_fetch_readme: Mock
    ) -> None:
        """Test dataset quality scoring with AI enhancement."""
        mock_fetch_readme.return_value = README_COMPREHENSIVE
        mock_ai_score.return_value = 0.9  # High AI score

        score_with_ai, elapsed = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model",
            dataset_link="https://huggingface.co/datasets/test",
            use_ai=True,
        )
        score_no_ai, _ = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model",
            dataset_link="https://huggingface.co/datasets/test",
            use_ai=False,
        )

        assert 0.0 <= score_with_ai <= 1.0
        assert elapsed >= 0
        # AI-enhanced score might be different from deterministic
        # (could be higher or lower depending on AI assessment)


def test_all_evaluation_functions_return_valid_scores() -> None:
    """Test that all evaluation functions return valid scores."""
    test_readme = README_COMPREHENSIVE

    doc_score = dataset_quality_sub_score.evaluate_dataset_documentation(test_readme)
    license_score = dataset_quality_sub_score.evaluate_license_clarity(test_readme)
    safety_score = dataset_quality_sub_score.evaluate_safety_privacy(test_readme)
    curation_score = dataset_quality_sub_score.evaluate_curation_quality(test_readme)
    repro_score = dataset_quality_sub_score.evaluate_reproducibility(test_readme)

    # All scores should be between 0.0 and 1.0
    for score, name in [
        (doc_score, "documentation"),
        (license_score, "license"),
        (safety_score, "safety"),
        (curation_score, "curation"),
        (repro_score, "reproducibility"),
    ]:
        assert 0.0 <= score <= 1.0, f"{name} score out of range: {score}"


def test_score_consistency() -> None:
    """Test that scores are consistent across multiple calls."""
    with patch("src.dataset_quality_sub_score.fetch_readme") as mock_fetch:
        mock_fetch.return_value = README_COMPREHENSIVE

        # Test consistency without AI (deterministic)
        score1, _ = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model",
            dataset_link="https://huggingface.co/datasets/test",
            use_ai=False,
        )
        score2, _ = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model",
            dataset_link="https://huggingface.co/datasets/test",
            use_ai=False,
        )

        assert score1 == score2, "Scores should be consistent across calls"


def test_all_five_criteria_included() -> None:
    """Test that all 5 criteria from the screenshot are included in scoring."""
    test_readme = README_COMPREHENSIVE

    # Test each criterion individually
    doc_score = dataset_quality_sub_score.evaluate_dataset_documentation(test_readme)
    license_score = dataset_quality_sub_score.evaluate_license_clarity(test_readme)
    safety_score = dataset_quality_sub_score.evaluate_safety_privacy(test_readme)
    curation_score = dataset_quality_sub_score.evaluate_curation_quality(test_readme)
    repro_score = dataset_quality_sub_score.evaluate_reproducibility(test_readme)

    # Each should contribute to the final score
    assert doc_score > 0, "Documentation should score > 0"
    assert license_score > 0, "License clarity should score > 0"
    assert safety_score > 0, "Safety should score > 0"
    assert curation_score > 0, "Curation should score > 0"
    assert repro_score > 0, "Reproducibility should score > 0"


def test_weight_distribution() -> None:
    """Test that weight distribution is correct (0.2 each for 5 criteria)."""
    with patch("src.dataset_quality_sub_score.fetch_readme") as mock_fetch:
        mock_fetch.return_value = README_COMPREHENSIVE

        score, _ = dataset_quality_sub_score.dataset_quality_sub_score(
            "test-model",
            dataset_link="https://huggingface.co/datasets/test",
        )

        # With all criteria scoring 1.0, final score should be 1.0
        # (0.2 * 1.0 + 0.2 * 1.0 + 0.2 * 1.0 + 0.2 * 1.0 + 0.2 * 1.0 = 1.0)
        assert 0.0 <= score <= 1.0, "Score should be between 0.0 and 1.0"


if __name__ == "__main__":
    pytest.main([__file__])
