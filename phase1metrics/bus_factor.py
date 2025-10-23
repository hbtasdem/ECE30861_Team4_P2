import re
import time

import requests


def get_huggingface_contributors(model_id: str) -> int:
    """
    Get the number of contributors directly from the Hugging Face Files page.

    Args:
        model_id: The Hugging Face model ID

    Returns:
        int: Number of contributors as shown in the Hugging Face UI
    """
    try:
        # Scrape the Files tab to get contributor count
        files_url = f"https://huggingface.co/{model_id}/tree/main"
        response = requests.get(files_url, timeout=15)

        if response.status_code == 200:
            content = response.text

            # Look for contributor count patterns in the Files page
            contributor_patterns = [
                r'(\d+)\s+contributors?',
                r'contributors?\s+(\d+)',
                r'\"contributors?\":\s*(\d+)',
            ]

            for pattern in contributor_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Return the first valid number found
                    for match in matches:
                        try:
                            count = int(match)
                            if count > 0:  # Valid contributor count
                                return count
                        except ValueError:
                            continue

        return 0

    except Exception as e:
        print(f"Error getting Hugging Face contributors for {model_id}: {e}")
        return 0


def bus_factor_score(model_id: str) -> tuple[int, float]:
    """
    Calculate the bus factor score based on the number of unique contributors
    to a Hugging Face model as shown in the Hugging Face UI.

    Args:
        model_id: The Hugging Face model ID
                 (e.g., "moonshotai/Kimi-K2-Instruct-0905")

    Returns:
        tuple[int, float]: (Number of unique contributors, execution time)
    """
    start_time = time.time()
    contributors = get_huggingface_contributors(model_id)
    end_time = time.time()
    execution_time = end_time - start_time

    return round(contributors,2), execution_time


# Test the function
if __name__ == "__main__":

    print("Testing bus factor calculation...")

    # Time the function call from outside
    start_time = time.time()
    result = bus_factor_score("moonshotai/Kimi-K2-Instruct-0905")
    end_time = time.time()

    execution_time = end_time - start_time
    print(f"Bus factor score: {result}")
    print(f"Execution time: {execution_time:.3f} seconds")
