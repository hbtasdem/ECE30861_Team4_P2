# This is to demonstrate functionality of rate

# in one powershell terminal: uvicorn src.app:app --reload
# in another powershell terminal: python src/rate/rate_cli.py https://huggingface.co/google/bert
# In browser go to http://127.0.0.1:8000/rate to see results

import requests

# Replace with your actual server URL
SERVER_URL = "http://127.0.0.1:8000"


def set_model_url(url: str) -> None:
    """
    Store the model URL on the server using a simple POST.
    We will just use the global variable on the server.
    """
    # We'll call a special "internal" endpoint to set the URL
    r = requests.post(f"{SERVER_URL}/rate", json={"model_url": url})
    if r.status_code == 200:
        print(f"Model URL set to: {url}")
    else:
        print(f"Error: {r.text}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python rate_cli.py <model_url>")
    else:
        set_model_url(sys.argv[1])
