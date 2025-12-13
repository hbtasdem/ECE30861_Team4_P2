import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src/metrics"))

# Import after path modification
from available_dataset_code_score import (  # noqa: E402
    available_dataset_code_score,
    detect_code_examples,
    detect_dataset_links,
)

# Test data for different README scenarios
README_EMPTY = ""

README_BASIC = """
# My Model
This is a simple model description.
Nothing else here.
"""

README_DATASET_ONLY_CSV = """
# My Model
## Dataset
Download the training data from: https://example.com/data.csv
The dataset contains 1000 samples.
"""

README_DATASET_ONLY_KAGGLE = """
# My Model
Training data available at kaggle.com/dataset
"""

README_DATASET_ONLY_HF = """
# My Model
## Dataset
Download from: https://huggingface.co/datasets/my-dataset
"""

README_CODE_ONLY_PYTHON = """
# My Model
## Usage
```python
import torch
model = torch.load('model.pth')
```
"""

README_CODE_ONLY_INSTALL = """
# My Model
Use: pip install mypackage
"""

README_CODE_ONLY_SECTIONS = """
# My Model
## Installation
```bash
pip install transformers
```

## Quick Start
```python
from transformers import AutoModel
model = AutoModel.from_pretrained('my-model')
```
"""

README_BOTH_COMPLETE = """
# My Model
## Dataset
Download from: https://example.com/dataset.zip

## Usage
```python
import torch
model = torch.load('model.pth')
```
"""

README_BOTH_MINIMAL = """
# My Model
Data: kaggle.com/dataset
Code: pip install mypackage
"""

README_COMPLEX_DATASET = """
# My Model
## Dataset
- Training data: https://huggingface.co/datasets/my-dataset
- Validation data: https://example.com/val.json
- Test data: https://example.com/test.parquet

## Data Format
The dataset contains 10,000 samples in JSON format.
"""

README_COMPLEX_CODE = """
# My Model
## Installation
```bash
pip install transformers
pip install torch
```

## Usage
```python
from transformers import AutoModel
model = AutoModel.from_pretrained('my-model')
```

## Examples
See example.py for more details.
"""

README_MIXED_FORMATS = """
# My Model
## Data Sources
- CSV files: https://example.com/data.csv
- JSON data: https://example.com/data.json
- Parquet: https://example.com/data.parquet

## Code Examples
```python
import pandas as pd
df = pd.read_csv('data.csv')
```

```javascript
const model = await loadModel('my-model');
```
"""

README_MARKDOWN_LINKS = """
# My Model
## Dataset
[Download training data](https://example.com/train.csv)
[Download validation data](https://example.com/val.csv)

## Usage
[See example script](example.py)
"""

README_SPECIAL_CHARS = """
# My Model
## Dataset
Data available at: https://example.com/data.tar.gz
Also check: https://example.com/data.tar.bz2

## Code
```python
import os
os.system('pip install mypackage')
```
"""


class TestDetectDatasetLinks(unittest.TestCase):
    """Test cases for detect_dataset_links function."""

    def test_detect_dataset_links_empty(self) -> None:
        """Test dataset detection with empty README."""
        result = detect_dataset_links(README_EMPTY)
        self.assertFalse(result)

    def test_detect_dataset_links_basic(self) -> None:
        """Test dataset detection with basic README."""
        result = detect_dataset_links(README_BASIC)
        self.assertFalse(result)

    def test_detect_dataset_links_csv(self) -> None:
        """Test dataset detection with CSV link."""
        result = detect_dataset_links(README_DATASET_ONLY_CSV)
        self.assertTrue(result)

    def test_detect_dataset_links_kaggle(self) -> None:
        """Test dataset detection with Kaggle reference."""
        result = detect_dataset_links(README_DATASET_ONLY_KAGGLE)
        self.assertTrue(result)

    def test_detect_dataset_links_hf(self) -> None:
        """Test dataset detection with Hugging Face dataset."""
        result = detect_dataset_links(README_DATASET_ONLY_HF)
        self.assertTrue(result)

    def test_detect_dataset_links_code_only(self) -> None:
        """Test dataset detection with code-only README."""
        result = detect_dataset_links(README_CODE_ONLY_PYTHON)
        self.assertFalse(result)

    def test_detect_dataset_links_install_only(self) -> None:
        """Test dataset detection with install-only README."""
        result = detect_dataset_links(README_CODE_ONLY_INSTALL)
        self.assertFalse(result)

    def test_detect_dataset_links_both_complete(self) -> None:
        """Test dataset detection with both dataset and code."""
        result = detect_dataset_links(README_BOTH_COMPLETE)
        self.assertTrue(result)

    def test_detect_dataset_links_both_minimal(self) -> None:
        """Test dataset detection with minimal both."""
        result = detect_dataset_links(README_BOTH_MINIMAL)
        self.assertTrue(result)

    def test_detect_dataset_links_complex_dataset(self) -> None:
        """Test dataset detection with complex dataset info."""
        result = detect_dataset_links(README_COMPLEX_DATASET)
        self.assertTrue(result)

    def test_detect_dataset_links_complex_code(self) -> None:
        """Test dataset detection with complex code info."""
        result = detect_dataset_links(README_COMPLEX_CODE)
        self.assertFalse(result)

    def test_detect_dataset_links_mixed_formats(self) -> None:
        """Test dataset detection with mixed formats."""
        result = detect_dataset_links(README_MIXED_FORMATS)
        self.assertTrue(result)

    def test_detect_dataset_links_markdown_links(self) -> None:
        """Test dataset detection with markdown links."""
        result = detect_dataset_links(README_MARKDOWN_LINKS)
        self.assertTrue(result)

    def test_detect_dataset_links_special_chars(self) -> None:
        """Test dataset detection with special characters."""
        result = detect_dataset_links(README_SPECIAL_CHARS)
        self.assertTrue(result)

    def test_detect_dataset_links_none_input(self) -> None:
        """Test dataset detection with None input."""
        result = detect_dataset_links(None)
        self.assertFalse(result)

    def test_detect_dataset_links_empty_string(self) -> None:
        """Test dataset detection with empty string."""
        result = detect_dataset_links("")
        self.assertFalse(result)

    def test_detect_dataset_links_whitespace_only(self) -> None:
        """Test dataset detection with whitespace-only string."""
        result = detect_dataset_links("   \n\t   ")
        self.assertFalse(result)


class TestDetectCodeExamples(unittest.TestCase):
    """Test cases for detect_code_examples function."""

    def test_detect_code_examples_empty(self) -> None:
        """Test code detection with empty README."""
        result = detect_code_examples(README_EMPTY)
        self.assertFalse(result)

    def test_detect_code_examples_basic(self) -> None:
        """Test code detection with basic README."""
        result = detect_code_examples(README_BASIC)
        self.assertFalse(result)

    def test_detect_code_examples_dataset_only_csv(self) -> None:
        """Test code detection with dataset-only README."""
        result = detect_code_examples(README_DATASET_ONLY_CSV)
        self.assertFalse(result)

    def test_detect_code_examples_dataset_only_kaggle(self) -> None:
        """Test code detection with Kaggle-only README."""
        result = detect_code_examples(README_DATASET_ONLY_KAGGLE)
        self.assertFalse(result)

    def test_detect_code_examples_python_code(self) -> None:
        """Test code detection with Python code."""
        result = detect_code_examples(README_CODE_ONLY_PYTHON)
        self.assertTrue(result)

    def test_detect_code_examples_install_command(self) -> None:
        """Test code detection with install command."""
        result = detect_code_examples(README_CODE_ONLY_INSTALL)
        self.assertTrue(result)

    def test_detect_code_examples_sections(self) -> None:
        """Test code detection with multiple code sections."""
        result = detect_code_examples(README_CODE_ONLY_SECTIONS)
        self.assertTrue(result)

    def test_detect_code_examples_both_complete(self) -> None:
        """Test code detection with both dataset and code."""
        result = detect_code_examples(README_BOTH_COMPLETE)
        self.assertTrue(result)

    def test_detect_code_examples_both_minimal(self) -> None:
        """Test code detection with minimal both."""
        result = detect_code_examples(README_BOTH_MINIMAL)
        self.assertTrue(result)

    def test_detect_code_examples_complex_dataset(self) -> None:
        """Test code detection with complex dataset info."""
        result = detect_code_examples(README_COMPLEX_DATASET)
        self.assertFalse(result)

    def test_detect_code_examples_complex_code(self) -> None:
        """Test code detection with complex code info."""
        result = detect_code_examples(README_COMPLEX_CODE)
        self.assertTrue(result)

    def test_detect_code_examples_mixed_formats(self) -> None:
        """Test code detection with mixed formats."""
        result = detect_code_examples(README_MIXED_FORMATS)
        self.assertTrue(result)

    def test_detect_code_examples_markdown_links(self) -> None:
        """Test code detection with markdown links."""
        result = detect_code_examples(README_MARKDOWN_LINKS)
        self.assertTrue(result)

    def test_detect_code_examples_special_chars(self) -> None:
        """Test code detection with special characters."""
        result = detect_code_examples(README_SPECIAL_CHARS)
        self.assertTrue(result)

    def test_detect_code_examples_none_input(self) -> None:
        """Test code detection with None input."""
        result = detect_code_examples(None)
        self.assertFalse(result)

    def test_detect_code_examples_empty_string(self) -> None:
        """Test code detection with empty string."""
        result = detect_code_examples("")
        self.assertFalse(result)

    def test_detect_code_examples_whitespace_only(self) -> None:
        """Test code detection with whitespace-only string."""
        result = detect_code_examples("   \n\t   ")
        self.assertFalse(result)


class TestAvailableDatasetCodeScore(unittest.TestCase):
    """Test cases for available_dataset_code_score function."""

    def test_score_empty_readme(self) -> None:
        """Test scoring with empty README."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_EMPTY
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.0)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_basic_readme(self) -> None:
        """Test scoring with basic README."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_BASIC
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.0)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_dataset_only_csv(self) -> None:
        """Test scoring with dataset-only README."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_DATASET_ONLY_CSV
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.5)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_dataset_only_kaggle(self) -> None:
        """Test scoring with Kaggle-only README."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_DATASET_ONLY_KAGGLE
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.5)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_code_only_python(self) -> None:
        """Test scoring with Python code-only README."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_CODE_ONLY_PYTHON
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.5)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_code_only_install(self) -> None:
        """Test scoring with install-only README."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_CODE_ONLY_INSTALL
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.5)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_both_complete(self) -> None:
        """Test scoring with both dataset and code."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_BOTH_COMPLETE
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 1.0)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_both_minimal(self) -> None:
        """Test scoring with minimal both."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_BOTH_MINIMAL
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 1.0)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_complex_dataset(self) -> None:
        """Test scoring with complex dataset info."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_COMPLEX_DATASET
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.5)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_complex_code(self) -> None:
        """Test scoring with complex code info."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_COMPLEX_CODE
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.5)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_mixed_formats(self) -> None:
        """Test scoring with mixed formats."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_MIXED_FORMATS
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 1.0)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_none_readme(self) -> None:
        """Test scoring when README fetch returns None."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = None
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.0)
            self.assertGreaterEqual(elapsed, 0)

    def test_score_empty_model_id(self) -> None:
        """Test scoring with empty model ID."""
        score, elapsed = available_dataset_code_score("")
        self.assertEqual(score, 0.0)
        self.assertGreaterEqual(elapsed, 0)

    def test_score_none_model_id(self) -> None:
        """Test scoring with None model ID."""
        score, elapsed = available_dataset_code_score(None)
        self.assertEqual(score, 0.0)
        self.assertGreaterEqual(elapsed, 0)

    def test_score_whitespace_model_id(self) -> None:
        """Test scoring with whitespace-only model ID."""
        score, elapsed = available_dataset_code_score("   \n\t   ")
        self.assertEqual(score, 0.0)
        self.assertGreaterEqual(elapsed, 0)

    def test_score_timing(self) -> None:
        """Test that timing is measured correctly."""
        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = README_BOTH_COMPLETE
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 1.0)
            self.assertGreaterEqual(elapsed, 0)
            # Should be very fast with mocked function
            self.assertLess(elapsed, 1.0)

    @patch("os.getenv")
    def test_score_logging(self, mock_getenv: Mock) -> None:
        """Test that logging works when LOG_LEVEL is set."""
        mock_getenv.return_value = "1"

        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = None
            # This should not raise an exception even with logging enabled
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.0)
            self.assertGreaterEqual(elapsed, 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and special scenarios."""

    def test_very_long_readme(self) -> None:
        """Test with a very long README."""
        long_readme = (
            "A" * 10000 + "\n## Dataset\nhttps://example.com/"
            "data.csv\n" + "B" * 10000
        )

        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = long_readme
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 0.5)  # Should detect dataset
            self.assertGreaterEqual(elapsed, 0)

    def test_unicode_readme(self) -> None:
        """Test with Unicode characters in README."""
        unicode_readme = """
        # 模型名称
        ## 数据集
        https://example.com/数据.csv

        ## 使用
        ```python
        import torch
        model = torch.load('模型.pth')
        ```
        """

        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = unicode_readme
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 1.0)  # Should detect both dataset and code
            self.assertGreaterEqual(elapsed, 0)

    def test_html_in_readme(self) -> None:
        """Test with HTML content in README."""
        html_readme = """
        # My Model
        <h2>Dataset</h2>
        <a href="https://example.com/data.csv">Download data</a>

        <h2>Code</h2>
        <pre><code>
        import torch
        model = torch.load('model.pth')
        </code></pre>
        """

        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = html_readme
            score, elapsed = available_dataset_code_score("test-model")
            self.assertEqual(score, 1.0)  # Should detect both dataset and code
            self.assertGreaterEqual(elapsed, 0)

    def test_case_insensitive_detection(self) -> None:
        """Test that detection is case-insensitive."""
        case_readme = """
        # My Model
        ## DATASET
        https://example.com/DATA.CSV

        ## USAGE
        ```PYTHON
        import torch
        model = torch.load('model.pth')
        ```
        """

        with patch("available_dataset_code_score.fetch_readme") as mock_fetch:
            mock_fetch.return_value = case_readme
            score, elapsed = available_dataset_code_score("test-model")
            # Should detect both despite case differences
            self.assertEqual(score, 1.0)
            self.assertGreaterEqual(elapsed, 0)


if __name__ == "__main__":
    unittest.main()
