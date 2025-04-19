# team.py
from .base import ClickUpResource
from .space import Space # Needed for type hints and object creation

class Workspace:
    """
    Represents a Workspace/Team in ClickUp.
    Provides methods to list and create Spaces within this Workspace.
    Note: This class does not inherit from ClickUpResource; it uses the
          client instance passed during initialization for API calls.
    """
    def __init__(self, team_id, team_name, client):
        """
        Initializes the Workspace object. Usually instantiated via Team.get_workspace().

        Args:
            team_id (str | int): The ID of the Workspace (Team ID).
            team_name (str): The name of the Workspace.
            client (ClickUpClient): The client object for API communication.
        """
        self.id = str(team_id) # Ensure ID is a string for URL parts
        self.name = team_name
        self.client = client # Store the client instance for requests
        # Local cache for Space objects belonging to this workspace
        self._spaces_cache = None

    def __repr__(self):
        """String representation for the Workspace object."""
        return f"<Workspace(id='{self.id}', name='{self.name}')>"

    def list_spaces(self, archived=False, force_refresh=False):
        """
        Fetches a list of Spaces within this Workspace. Caches results locally.
        Ref: https://clickup.com/api/clickupreference/operation/GetSpaces/

        Args:
            archived (bool): Include archived spaces. Defaults to False.
            force_refresh (bool): Bypass cache and fetch fresh data. Defaults to False.

        Returns:
            list[Space]: A list of Space objects belonging to this Workspace.
        """
        # Note: Simple cache doesn't differentiate based on 'archived' status requested.
        if self._spaces_cache is not None and not force_refresh:
            print(f"Using cached spaces list for Workspace {self.id}.")
            return self._spaces_cache

        print(f"Fetching spaces list from API for Workspace {self.id} (Archived: {archived})...")
        endpoint = f"/team/{self.id}/space"
        params = {'archived': str(archived).lower()}
        # Use the stored client instance to make the request
        response_data = self.client.request("GET", endpoint, params=params)
        spaces_list_data = response_data.get("spaces", [])

        # Create Space objects and update cache
        self._spaces_cache = [Space(self.client, space['id'], space.get('name'), data=space) for space in spaces_list_data]
        print(f"Found and cached {len(self._spaces_cache)} spaces in Workspace {self.id}.")
        return self._spaces_cache

    def create_space(self, name, **features):
        """
        Creates a new Space within this Workspace.
        Ref: https://clickup.com/api/clickupreference/operation/CreateSpace/

        Args:
            name (str): The desired name for the new space. Must be non-empty.
            **features: Optional features to enable/disable (e.g., multiple_assignees=True).
                        Refer to ClickUp API docs for available feature keys.

        Returns:
            Space: An object representing the created Space.

        Raises:
            ValueError: If the provided name is empty or invalid.
        """
        if not name or not isinstance(name, str) or not name.strip():
             raise ValueError("Space name must be a non-empty string.")

        space_name_cleaned = name.strip()
        print(f"Creating space '{space_name_cleaned}' in Workspace '{self.name}' (ID: {self.id})...")
        endpoint = f"/team/{self.id}/space"
        payload = {"name": space_name_cleaned}
        # API expects features nested under a 'features' key
        if features:
            payload["features"] = features

        response_data = self.client.request("POST", endpoint, json=payload)
        # Create Space object from response
        new_space = Space(self.client, response_data['id'], response_data.get('name'), data=response_data)
        print(f"Space '{new_space.name}' created successfully (ID: {new_space.id}).")

        # Update cache if it exists
        if self._spaces_cache is not None:
            self._spaces_cache = [s for s in self._spaces_cache if s.id != new_space.id] # Avoid duplicates
            self._spaces_cache.append(new_space)

        return new_space

    def get_space(self, space_id):
        """
        Gets a Space object instance representing a specific space by its ID.
        This method only creates the object instance; it does not fetch data.
        Call `.get()` on the returned Space object to load its details.

        Args:
            space_id (str | int): The ID of the desired space.

        Returns:
            Space: A Space object linked to this client and the given ID.
        """
        print(f"Creating Space object instance for ID: {space_id} (data not fetched yet).")
        # Creates the object instance without an API call. Assumes it belongs here contextually.
        return Space(self.client, space_id)

    # --- Optional Cache Search Methods ---
    # These search only the locally cached data from the last list_spaces call.

    def find_space_by_id_in_cache(self, space_id):
        """Search for a space in the local cache by its ID."""
        target_id = str(space_id)
        if self._spaces_cache is None:
            print("Warning: Space cache is empty. Call list_spaces() first.")
            return None
        for space in self._spaces_cache:
            if space.id == target_id:
                return space
        return None # Not found in cache

    def find_space_by_name_in_cache(self, space_name):
        """Search for a space in the local cache by name (case-insensitive). Returns first match."""
        if self._spaces_cache is None:
            print("Warning: Space cache is empty. Call list_spaces() first.")
            return None
        search_name_lower = space_name.lower()
        for space in self._spaces_cache:
            # Ensure space has name attribute before comparing
            if hasattr(space, 'name') and space.name and space.name.lower() == search_name_lower:
                return space
        return None # Not found in cache


# --- Team Class ---

class Team(ClickUpResource):
    """
    Resource primarily used as an entry point to find and instantiate Workspace objects.
    Represents the collection of Workspaces (Teams) accessible by the API token.
    Inherits from ClickUpResource to use self._request.
    """
    def get_all(self):
        """
        Fetches a list of all Workspaces (Teams) accessible by the API token.
        Ref: https://clickup.com/api/clickupreference/operation/GetAuthorizedTeams/

        Returns:
            dict: The raw API response containing a list under the 'teams' key.
                  Example: {'teams': [{'id': '123', 'name': 'My Team', ...}]}
        """
        print("Fetching all accessible Workspaces (Teams)...")
        # Uses self._request inherited from ClickUpResource
        return self._request("GET", "/team")

    def get_workspace(self, team_name):
        """
        Finds a specific Workspace by name (case-insensitive) and returns a Workspace object.

        Args:
            team_name (str): The name of the desired Workspace.

        Returns:
            Workspace | None: The Workspace object if found, otherwise None.
        """
        print(f"Searching for Workspace named '{team_name}'...")
        all_teams_data = self.get_all()
        found_workspace = None
        for team_data in all_teams_data.get("teams", []):
            # Case-insensitive comparison for the name
            if team_data.get("name", "").lower() == team_name.lower():
                print(f"Found Workspace: '{team_data.get('name')}' (ID: {team_data.get('id')})")
                # Instantiate the Workspace object, passing the client instance
                # Workspace needs the client to make its own API calls (e.g., list_spaces)
                found_workspace = Workspace(team_data["id"], team_data["name"], self.client)
                break # Stop after finding the first match

        if found_workspace is None:
             print(f"Workspace '{team_name}' not found among accessible teams.")

        return found_workspace # Returns the Workspace object or None