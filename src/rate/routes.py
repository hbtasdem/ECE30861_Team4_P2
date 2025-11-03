from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from main import calculate_all_scores  # Import your real scoring function

router = APIRouter()
latest_model_url = None  # This stores the last URL sent via terminal


@router.get("/rate", response_class=HTMLResponse)  # type: ignore[misc]
async def rate_endpoint() -> HTMLResponse:
    if not latest_model_url:
        return "<p>No model URL provided yet. Use the terminal to set one.</p>"

    try:
        result = calculate_all_scores("", "", latest_model_url, set(), set())

        # Build HTML dynamically for all keys in the result
        html_content = f"<h1>Model Rating Result for {result.get('name')}</h1><ul>"
        for key, value in result.items():
            if isinstance(value, dict):
                # For nested dictionaries like size_score
                html_content += f"<li><strong>{key}:</strong><ul>"
                for sub_key, sub_val in value.items():
                    html_content += f"<li>{sub_key}: {sub_val}</li>"
                html_content += "</ul></li>"
            else:
                html_content += f"<li><strong>{key}:</strong> {value}</li>"
        html_content += "</ul>"

        return html_content

    except Exception as e:
        return f"<p>Error scoring model: {e}</p>"


@router.post("/rate")  # type: ignore[misc]
async def set_model_url_endpoint(request: Request) -> HTMLResponse:
    """
    Set the latest model URL via terminal/CLI. The GET /rate page will
    display the score for this URL.
    """
    global latest_model_url
    data = await request.json()
    latest_model_url = data.get("model_url")
    return {"status": "ok", "model_url": latest_model_url}
