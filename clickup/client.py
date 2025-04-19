# client.py
import requests
import os
from dotenv import load_dotenv
import time # For rate limiting delay

load_dotenv()

class ClickUpClient:
    """Handles authenticated requests to the ClickUp API v2."""

    def __init__(self, token=None):
        """
        Initializes the client with API token and base URL.

        Args:
            token (str, optional): ClickUp API token. If None, attempts to read from
                                   CLICKUP_TOKEN environment variable. Defaults to None.

        Raises:
            ValueError: If no API token is provided or found in environment variables.
        """
        self.base_url = "https://api.clickup.com/api/v2"
        self.token = token or os.getenv("CLICKUP_TOKEN")
        if not self.token:
             raise ValueError("API token not provided. Set CLICKUP_TOKEN environment variable or pass token to constructor.")
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
            # Optional: Add user-agent for better API etiquette
            # "User-Agent": "YourAppName/Version (contact@example.com)"
        }

    def request(self, method, endpoint, **kwargs):
        """
        Makes a request to the ClickUp API, handling auth, base URL, rate limiting delay,
        and basic error checking.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            endpoint (str): API endpoint path (e.g., '/space/123/list'). Should start with '/'.
            **kwargs: Additional arguments passed to requests.request (e.g., json, params).

        Returns:
            dict: Parsed JSON response from the API. Returns an empty dict for success responses
                  with no content (e.g., 204 No Content). Returns a dict with
                  {'raw_response_text': ...} if response is successful but not valid JSON.

        Raises:
            Exception: For API errors (non-2xx status codes). Contains status code and error text.
                       (Future improvement: Raise more specific custom exceptions).
        """
        # Add a small delay before every request to help stay within ClickUp rate limits.
        # 0.65 seconds delay allows for roughly 92 requests per minute.
        time.sleep(0.65)

        url = f"{self.base_url}{endpoint}"
        # Optional: uncomment below for verbose logging of requests
        # print(f"[API Call] -> {method} {url}")
        # if 'json' in kwargs: print(f"[API Payload] -> {kwargs.get('json')}")
        # if 'params' in kwargs: print(f"[API Params] -> {kwargs.get('params')}")

        response = requests.request(method, url, headers=self.headers, **kwargs)

        # Optional: uncomment below for verbose logging of responses
        # print(f"[API Response] <- Status: {response.status_code}")

        if not response.ok:
            # Raise an exception for non-successful status codes
            error_message = f"[{response.status_code}] Error: {response.text}"
            # Optional: uncomment below for verbose logging of errors
            # print(f"[API Error] {error_message}")
            # TODO: Consider raising more specific custom exceptions based on status code
            raise Exception(error_message)

        # Handle responses that might be empty (e.g., 204 No Content on DELETE)
        # or successful but not JSON
        if response.text and response.status_code != 204:
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                # Log warning and return raw text if response isn't valid JSON
                print(f"[API Warning] Response status {response.status_code} but not valid JSON: {response.text[:100]}...") # Log snippet
                return {"raw_response_text": response.text}

        # Return empty dict for 204 No Content or other successful responses with no body
        return {}