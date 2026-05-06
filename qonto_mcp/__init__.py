import os
from mcp.server.fastmcp import FastMCP
from requests.exceptions import RequestException

# Qonto API configuration
thirdparty_host = None
api_key = None
organization_id = None
staging_token = None
headers = {}

# Single MCP instance
mcp = FastMCP("Qonto MCP")

def setup_qonto_config():
    """Initialize Qonto API configuration with environment variables"""
    global thirdparty_host, api_key, organization_id, staging_token, headers
    
    thirdparty_host = os.getenv("QONTO_THIRDPARTY_HOST")
    if not thirdparty_host:
        raise ValueError("QONTO_THIRDPARTY_HOST environment variable is not set.")

    api_key = os.getenv("QONTO_API_KEY")
    if not api_key:
        raise ValueError("QONTO_API_KEY environment variable is not set.")

    organization_id = os.getenv("QONTO_ORGANIZATION_ID")
    if not organization_id:
        raise ValueError("QONTO_ORGANIZATION_ID environment variable is not set.")

    staging_token = os.getenv("QONTO_STAGING_TOKEN")

    headers = {
        "Accept": "application/json",
        "Authorization": f"{organization_id}:{api_key}",
    }

    if staging_token:
        headers["X-Qonto-Staging-Token"] = staging_token


def format_qonto_error(action: str, e: RequestException) -> str:
    """Build an error string that includes the Qonto response body.

    Without this, a 401/403/422 surfaces only as
    "401 Client Error: Unauthorized for url: …" — the JSON body that explains
    *which* scope is missing or *which* field is invalid is dropped on the
    floor. Surfacing the body makes scope/permission/validation issues
    self-diagnosing for the caller.
    """
    base = f"Failed to {action}: {str(e)}"
    if e.response is not None:
        try:
            body = e.response.text
        except Exception:
            body = ""
        if body:
            return f"{base} | response body: {body}"
    return base