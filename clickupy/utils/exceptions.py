# clickupy/exceptions.py

class ClickupyException(Exception):
    """Base exception class for the clickupy library."""
    pass

class UserNotFoundByNameError(ClickupyException):
    """Raised when a user cannot be found by the provided name query within a specific list context."""
    def __init__(self, name_query, list_id):
        self.name_query = name_query
        self.list_id = list_id
        super().__init__(f"No user found matching '{name_query}' in List ID '{list_id}'.")

class AmbiguousUserNameError(ClickupyException):
    """Raised when multiple users match the provided name query within a specific list context."""
    def __init__(self, name_query, matches, list_id):
        self.name_query = name_query
        # Store only relevant info for the message, not potentially large objects
        self.matched_users_info = [
            f"'{m.get('username', 'N/A')}' (ID: {m.get('id')})" for m in matches
        ]
        self.list_id = list_id
        match_details = ", ".join(self.matched_users_info)
        super().__init__(f"Ambiguous user name '{name_query}' in List ID '{list_id}'. Matches: {match_details}. Please use User ID instead.")

# You might add other custom exceptions here later