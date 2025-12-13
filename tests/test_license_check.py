# test phase 2 license check functions
from src.license_check import get_github_license, get_model_license


def test_get_github_license() -> None:
    gitub_url = "https://github.com/google-research/bert"
    github_license = get_github_license(gitub_url)
    assert github_license.lower() == "apache-2.0"


def test_get_model_license() -> None:
    model_url = "https://huggingface.co/google-bert/bert-base-uncased"
    model_license = get_model_license(model_url)
    assert model_license.lower() == "apache-2.0"
