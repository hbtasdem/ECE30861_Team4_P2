import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src/metrics"))

import dataset_quality_score as dqs

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def rich_readme():
    return """
    # Dataset Documentation

    This dataset contains 10,000 samples in CSV format.
    The dataset was collected from public sources and anonymized to remove PII.

    Columns:
    - text: input text
    - label: classification label

    License: MIT License.
    Free to use for academic and commercial use.

    Safety:
    We discuss bias, fairness, and ethical considerations.

    Curation:
    Data was curated, validated, cleaned, and versioned as v1.2.

    Reproducibility:
    Code available on GitHub.
    Use Docker and pip install -r requirements.txt.
    Follow the step by step instructions to reproduce results.
    """


@pytest.fixture
def minimal_readme():
    return "This is a dataset."


@pytest.fixture
def no_signal_readme():
    return "Hello world."


# ============================================================================
# BASIC DETERMINISTIC SCORING
# ============================================================================


def test_evaluate_dataset_documentation_full(rich_readme):
    score = dqs.evaluate_dataset_documentation(rich_readme)
    assert score == 1.0


def test_evaluate_dataset_documentation_partial(minimal_readme):
    score = dqs.evaluate_dataset_documentation(minimal_readme)
    assert 0.0 < score < 1.0


def test_evaluate_dataset_documentation_none():
    assert dqs.evaluate_dataset_documentation(None) == 0.0


def test_evaluate_license_clarity_none():
    assert dqs.evaluate_license_clarity(None) == 0.0


def test_evaluate_safety_privacy_full(rich_readme):
    score = dqs.evaluate_safety_privacy(rich_readme)
    assert score == 1.0


def test_evaluate_safety_privacy_none():
    assert dqs.evaluate_safety_privacy(None) == 0.0


def test_evaluate_reproducibility_full(rich_readme):
    score = dqs.evaluate_reproducibility(rich_readme)
    assert score == 1.0


def test_evaluate_reproducibility_none():
    assert dqs.evaluate_reproducibility(None) == 0.0


# ============================================================================
# URL + IDENTIFIER EXTRACTION
# ============================================================================


def test_extract_huggingface_dataset():
    link = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
    assert dqs.extract_dataset_identifier(link) == "bookcorpus/bookcorpus"


def test_extract_generic_url():
    link = "https://example.com/data/mydataset"
    assert dqs.extract_dataset_identifier(link) == "example.com/data/mydataset"


def test_extract_empty_url():
    assert dqs.extract_dataset_identifier("") == ""


# ============================================================================
# DATASET DETECTION LOGIC
# ============================================================================


def test_check_readme_for_known_datasets_direct():
    readme = "We use the BookCorpus dataset extensively."
    assert dqs.check_readme_for_known_datasets(readme, {"bookcorpus"})


def test_check_readme_for_known_datasets_partial_match():
    readme = "This model trains on book corpus large text data."
    assert dqs.check_readme_for_known_datasets(readme, {"book_corpus_large"})


def test_check_readme_for_known_datasets_no_match():
    readme = "This uses a proprietary dataset."
    assert not dqs.check_readme_for_known_datasets(readme, {"imagenet"})


def test_check_readme_for_known_datasets_empty():
    assert not dqs.check_readme_for_known_datasets("", {"data"})
    assert not dqs.check_readme_for_known_datasets("data", set())


# ============================================================================
# HYBRID SCORING (AI LOGIC)
# ============================================================================


def test_documentation_hybrid_no_ai(rich_readme):
    score = dqs.evaluate_dataset_documentation_hybrid(
        rich_readme, "model", use_ai=False
    )
    assert score == 1.0


def test_documentation_hybrid_ai_failure(monkeypatch, rich_readme):
    monkeypatch.setattr(dqs, "_get_ai_score", lambda *args, **kwargs: 0.0)
    score = dqs.evaluate_dataset_documentation_hybrid(rich_readme, "model", use_ai=True)
    assert score == 1.0


def test_documentation_hybrid_ai_success(monkeypatch, rich_readme):
    monkeypatch.setattr(dqs, "_get_ai_score", lambda *args, **kwargs: 0.5)
    score = dqs.evaluate_dataset_documentation_hybrid(rich_readme, "model", use_ai=True)
    assert 0.8 <= score <= 1.0


def test_safety_hybrid_ai_success(monkeypatch, rich_readme):
    monkeypatch.setattr(dqs, "_get_ai_score", lambda *args, **kwargs: 0.5)
    score = dqs.evaluate_safety_privacy_hybrid(rich_readme, "model", use_ai=True)
    assert 0.7 <= score <= 1.0


# ============================================================================
# FULL PIPELINE: dataset_quality_sub_score
# ============================================================================


def test_dataset_quality_no_dataset(monkeypatch):
    monkeypatch.setattr(dqs, "fetch_readme", lambda _: "irrelevant")
    score, elapsed = dqs.dataset_quality_sub_score(
        "model",
        dataset_link="",
        encountered_datasets=set(),
        use_ai=False,
    )
    assert score == 0.0
    assert elapsed >= 0.0


def test_dataset_quality_ai_enabled(monkeypatch, rich_readme):
    monkeypatch.setattr(dqs, "fetch_readme", lambda _: rich_readme)
    monkeypatch.setattr(dqs, "_get_ai_score", lambda *a, **k: 0.6)

    score, _ = dqs.dataset_quality_sub_score(
        "model",
        dataset_link="https://example.com/data",
        encountered_datasets=set(),
        use_ai=True,
    )
    assert 0.8 <= score <= 1.0


def test_dataset_quality_readme_missing(monkeypatch):
    monkeypatch.setattr(dqs, "fetch_readme", lambda _: None)

    score, _ = dqs.dataset_quality_sub_score(
        "model",
        dataset_link="https://example.com/data",
        encountered_datasets=set(),
        use_ai=False,
    )
    assert score == 0.0
