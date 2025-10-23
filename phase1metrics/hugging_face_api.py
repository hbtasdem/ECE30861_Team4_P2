import os
import time
from typing import Any, Dict, Optional

import requests

HF_API_BASE = "https://huggingface.co/api"


def get_model_info(model_id: str) -> tuple[Optional[Dict[str, Any]], float]:
    """
    Fetch model information from Hugging Face API.
    Returns model metadata as dictionary.
    """
    start_time = time.time()

    if not model_id or not model_id.strip():
        end_time = time.time()
        return (None, end_time - start_time)

    api_url = f"{HF_API_BASE}/models/{model_id.strip()}"

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        end_time = time.time()
        return (response.json(), end_time - start_time)

    except Exception as e:
        end_time = time.time()
        if int(os.getenv("LOG_LEVEL", "0")) > 0:
            print(f"[ERROR] Failed to fetch model info: {e}")
        return (None, end_time - start_time)


if __name__ == "__main__":
    model_info, exec_time = get_model_info("gpt2")
    if model_info:
        print(f"Model ID: {model_info.get('id', 'Unknown')}")
        print(f"Execution time: {exec_time:.3f}s")
    else:
        print(f"Failed to fetch model info (took {exec_time:.3f}s)")
