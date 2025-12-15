#!/usr/bin/env python3
"""
Local test script for regex endpoint functionality.
Tests the regex search logic without needing the full server.
"""

import re
from typing import List, Dict, Any

# Mock artifact data (simulating what would come from S3)
MOCK_ARTIFACTS = [
    {
        "metadata": {"name": "bert-base-uncased", "id": "01ABC123", "type": "model"},
        "data": {"url": "https://huggingface.co/bert-base-uncased"}
    },
    {
        "metadata": {"name": "distilbert-base-uncased-distilled-squad", "id": "01ABC124", "type": "model"},
        "data": {"url": "https://huggingface.co/distilbert-base-uncased-distilled-squad"}
    },
    {
        "metadata": {"name": "audience_classifier_model", "id": "01ABC125", "type": "model"},
        "data": {"url": "https://huggingface.co/some/model"}
    },
    {
        "metadata": {"name": "bert", "id": "01ABC126", "type": "code"},
        "data": {"url": "https://github.com/user/bert"}
    },
    {
        "metadata": {"name": "my-dataset", "id": "01ABC127", "type": "dataset"},
        "data": {"url": "https://example.com/dataset"}
    },
]


def test_regex_search(pattern: str) -> List[Dict[str, Any]]:
    """
    Test regex search against mock artifacts.
    
    Args:
        pattern: Regex pattern to test
        
    Returns:
        List of matching artifacts
    """
    try:
        regex_pattern = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(f"❌ Invalid regex: {e}")
        return []
    
    matching = []
    for artifact in MOCK_ARTIFACTS:
        name = artifact["metadata"]["name"]
        
        # Match name
        if regex_pattern.search(name):
            matching.append(artifact)
            print(f"  ✅ Matched: {name} (type: {artifact['metadata']['type']})")
    
    return matching


def main():
    """Run test cases."""
    print("=" * 60)
    print("REGEX ENDPOINT LOCAL TESTS")
    print("=" * 60)
    
    test_cases = [
        ("bert", "Match 'bert' - should find 3 items"),
        (".*", "Match all - should find all 5 items"),
        ("^bert", "Start with 'bert' - should find 2 items"),
        ("model$", "End with 'model' - should find 1 item"),
        ("distil.*squad", "Complex pattern - should find 1 item"),
        ("[invalid", "Invalid regex - should error"),
        ("BERT", "Case insensitive - should find 3 items"),
        ("xyz123", "No matches - should find 0 items"),
    ]
    
    for pattern, description in test_cases:
        print(f"\n📝 Test: {description}")
        print(f"   Pattern: '{pattern}'")
        matches = test_regex_search(pattern)
        print(f"   Result: {len(matches)} matches")
        
        if len(matches) == 0 and pattern != "[invalid" and pattern != "xyz123":
            print("   ⚠️  Expected matches but found none!")
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()