"""API wrapper functions for Drown Platform."""

import requests
from drown.config import get_api_base


def _make_request(method, endpoint, token=None, data=None):
    """
    Make an HTTP request to the API.
    
    Returns: (success: bool, result: dict)
    """
    api_base = get_api_base()
    url = f"{api_base}{endpoint}"
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return False, {"error": f"Unsupported HTTP method: {method}"}
        
        # Handle different status codes
        if response.status_code == 200:
            try:
                return True, response.json()
            except ValueError:
                return True, {"message": response.text}
        elif response.status_code == 201:
            try:
                return True, response.json()
            except ValueError:
                return True, {"message": "Created successfully"}
        elif response.status_code == 401:
            return False, {"error": "Invalid credentials. Please run 'drown login' again."}
        elif response.status_code == 403:
            return False, {"error": "Forbidden: You don't have access to this resource."}
        elif response.status_code == 404:
            return False, {"error": "Not found. The app or resource doesn't exist."}
        elif response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "Bad request")
            except ValueError:
                error_msg = "Bad request"
            return False, {"error": error_msg}
        elif response.status_code >= 500:
            return False, {"error": "Server error. Please try again later."}
        else:
            return False, {"error": f"Unexpected response: {response.status_code}"}
    
    except requests.exceptions.ConnectionError:
        return False, {"error": f"Unable to connect to {api_base}. Please check your internet connection."}
    except requests.exceptions.Timeout:
        return False, {"error": "Request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return False, {"error": f"Network error: {str(e)}"}


def login(username, password):
    """
    Authenticate with the platform.
    
    Returns: (success: bool, result: dict)
    result contains: {"token": "...", "username": "..."} or {"error": "..."}
    """
    return _make_request("POST", "/api/auth/login", data={
        "username": username,
        "password": password
    })


def get_apps(token):
    """
    Get list of all apps.
    
    Returns: (success: bool, result: dict)
    result contains: {"apps": [...]} or {"error": "..."}
    """
    return _make_request("GET", "/api/apps", token=token)


def create_app(token, app_name):
    """
    Create a new app.
    
    Returns: (success: bool, result: dict)
    result contains: {"app": {...}, "domain": "...", "git_remote": "...", "push_instructions": "..."} or {"error": "..."}
    """
    return _make_request("POST", "/api/apps/create", token=token, data={
        "name": app_name
    })


def scale_app(token, app_name, replicas):
    """
    Scale an app to specified replica count.
    
    Returns: (success: bool, result: dict)
    result contains: {"app": {...}, "replicas": ...} or {"error": "..."}
    """
    return _make_request("POST", f"/api/apps/{app_name}/scale", token=token, data={
        "replicas": replicas
    })


def get_logs(token, app_name):
    """
    Get logs for an app.
    
    Returns: (success: bool, result: dict)
    result contains: {"app": "...", "logs": "..."} or {"error": "..."}
    """
    return _make_request("GET", f"/api/apps/{app_name}/logs", token=token)


def get_metrics(token, app_name):
    """
    Get metrics for an app.
    
    Returns: (success: bool, result: dict)
    result contains: {"app": "...", "replicas": [...]} or {"error": "..."}
    """
    return _make_request("GET", f"/api/apps/{app_name}/metrics", token=token)
