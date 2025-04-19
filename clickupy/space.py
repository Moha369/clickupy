# space.py
from .base import ClickUpResource
from .folder import Folder # Required for type hinting and object creation
from .list import List   # Required for type hinting and object creation

class Space(ClickUpResource):
    """
    Represents an individual Space in ClickUp.
    Provides methods for managing the Space itself (get, update, delete),
    its Folders (list_folders, create_folder, get_folder),
    and its folderless Lists (list_lists, create_list).
    """
    def __init__(self, client, space_id, name=None, data=None):
        """
        Initializes the Space object.

        Args:
            client (ClickUpClient): The client object for API communication.
            space_id (str | int): The ID of the space.
            name (str, optional): The name of the space. Defaults to None.
            data (dict, optional): Raw space data as received from the API. Defaults to None.
        """
        super().__init__(client)
        self.id = str(space_id)
        self.name = name
        self._data = data if data else {}
        # Caches for contained items, initialized to None
        self._folders_cache = None
        self._folderless_lists_cache = None

        # Populate attributes from data if provided
        if data:
            self._populate_attributes(data)
        # Fallback: Ensure name is set if passed directly and not in initial data
        elif name is None and data and 'name' in data:
             self.name = data['name']

    def _populate_attributes(self, data):
        """Helper method to populate instance attributes from a data dictionary."""
        self.name = data.get('name', self.name)
        # Add other relevant space attributes here if needed
        # self.features = data.get('features')
        # self.statuses = data.get('statuses')

    def __repr__(self):
        """String representation for the Space object."""
        return f"<Space(id='{self.id}', name='{self.name}')>"

    # --- Space Management Methods ---
    def get(self):
        """
        Fetches the latest details for this space from the API and updates the object.
        Ref: https://clickup.com/api/clickupreference/operation/GetSpace/

        Returns:
            Space: The instance itself after updating its data.
        """
        print(f"Getting details for Space ID: {self.id}...")
        endpoint = f"/space/{self.id}"
        response_data = self._request("GET", endpoint)
        self._data = response_data
        self._populate_attributes(self._data) # Update attributes
        print(f"Space details retrieved for '{self.name}'.")
        return self

    def update(self, name=None, **features_to_update):
        """
        Updates this space in ClickUp (e.g., name, enabled features).
        Only provided fields are sent in the request.
        Ref: https://clickup.com/api/clickupreference/operation/UpdateSpace/

        Args:
            name (str, optional): The new name for the space.
            **features_to_update: Keyword arguments for features (e.g., multiple_assignees=True).
                                  Check API docs for valid feature keys.

        Returns:
            Space: The instance itself after updating data from the API response.
        """
        endpoint = f"/space/{self.id}"
        payload = {}
        if name is not None:
            payload["name"] = name.strip() if isinstance(name, str) else name
        # API expects features nested under a 'features' key
        if features_to_update:
            payload["features"] = features_to_update

        if not payload:
            print("Warning: No update data provided for Space.")
            return self

        print(f"Updating Space ID: {self.id}...")
        response_data = self._request("PUT", endpoint, json=payload)
        self._data = response_data
        self._populate_attributes(self._data) # Update attributes
        print(f"Space updated. Current name from API: '{self.name}'.")
        return self

    def delete(self):
        """
        Deletes this space from ClickUp. Warning: Irreversible.
        Ref: https://clickup.com/api/clickupreference/operation/DeleteSpace/

        Returns:
            dict: The response from the API (often empty on success).
        """
        print(f"Deleting Space ID: {self.id} ('{self.name}')...")
        endpoint = f"/space/{self.id}"
        response_data = self._request("DELETE", endpoint)
        print(f"Space deletion request sent for ID: {self.id}.")
        return response_data

    # --- Folder Management Methods within Space ---

    def list_folders(self, archived=False, force_refresh=False):
        """
        Fetches Folders within this Space. Caches results locally.
        Ref: https://clickup.com/api/clickupreference/operation/GetFolders/

        Args:
            archived (bool): Include archived folders. Defaults to False.
            force_refresh (bool): Bypass cache and fetch fresh data. Defaults to False.

        Returns:
            list[Folder]: A list of Folder objects belonging to this Space.
        """
        if self._folders_cache is not None and not force_refresh:
            print(f"Using cached folders list for Space {self.id}.")
            return self._folders_cache

        print(f"Fetching folders list from API for Space {self.id} (Archived: {archived})...")
        endpoint = f"/space/{self.id}/folder"
        params = {'archived': str(archived).lower()}
        response_data = self._request("GET", endpoint, params=params)
        folder_list_data = response_data.get("folders", [])

        # Create Folder objects and update cache
        self._folders_cache = [Folder(self.client, fldr['id'], fldr.get('name'), data=fldr) for fldr in folder_list_data]
        print(f"Found and cached {len(self._folders_cache)} folders in Space {self.id}.")
        return self._folders_cache

    def create_folder(self, name):
        """
        Creates a new Folder within this Space.
        Ref: https://clickup.com/api/clickupreference/operation/CreateFolder/

        Args:
            name (str): The name for the new folder. Must be non-empty.

        Returns:
            Folder: A Folder object representing the created Folder.

        Raises:
            ValueError: If the provided name is empty or invalid.
        """
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Folder name must be a non-empty string.")

        folder_name_cleaned = name.strip()
        print(f"Creating folder '{folder_name_cleaned}' in Space '{self.name}' (ID: {self.id})...")
        endpoint = f"/space/{self.id}/folder"
        payload = {"name": folder_name_cleaned}

        response_data = self._request("POST", endpoint, json=payload)
        # Create Folder object from response
        new_folder = Folder(self.client, response_data['id'], response_data.get('name'), data=response_data)
        print(f"Folder '{new_folder.name}' created successfully (ID: {new_folder.id}).")

        # Update cache if it exists
        if self._folders_cache is not None:
            self._folders_cache = [f for f in self._folders_cache if f.id != new_folder.id] # Avoid duplicates
            self._folders_cache.append(new_folder)

        return new_folder

    def get_folder(self, folder_name, force_refresh=False):
        """
        Finds a Folder within this Space by name (case-insensitive). Returns first match.
        Lists folders if not cached or if force_refresh is True.

        Args:
            folder_name (str): The name of the folder to find. Must be non-empty.
            force_refresh (bool): Force refresh folder cache before searching. Defaults to False.

        Returns:
            Folder | None: The found Folder object, or None if not found.
        """
        if not folder_name or not isinstance(folder_name, str) or not folder_name.strip():
            # Consider raising ValueError instead of printing and returning None
            print("Error: Folder name must be a non-empty string.")
            return None

        folder_name_cleaned = folder_name.strip()
        print(f"Searching for folder by name: '{folder_name_cleaned}' in Space '{self.name}'...")

        try:
            # Ensure the folder list is loaded for searching
            folder_list = self.list_folders(force_refresh=force_refresh) # Use the result directly
        except Exception as e:
             print(f"Error listing folders while searching by name: {e}")
             return None # Cannot search if listing fails

        # Search the retrieved list
        search_name_lower = folder_name_cleaned.lower()
        for folder in folder_list:
            # Check if folder object has a name attribute before comparing
            if hasattr(folder, 'name') and folder.name and folder.name.lower() == search_name_lower:
                print(f"Found folder: '{folder.name}' (ID: {folder.id})")
                return folder # Return the first match

        print(f"Folder with name '{folder_name_cleaned}' not found in Space '{self.name}'.")
        return None

    # --- Folderless List Management Methods within Space ---

    def list_lists(self, archived=False, force_refresh=False):
        """
        Fetches folderless Lists within this Space. Caches results locally.
        Ref: https://clickup.com/api/clickupreference/operation/GetFolderlessLists/

        Args:
            archived (bool): Include archived lists. Defaults to False.
            force_refresh (bool): Bypass cache and fetch fresh data. Defaults to False.

        Returns:
            list[List]: A list of folderless List objects belonging to this Space.
        """
        if self._folderless_lists_cache is not None and not force_refresh:
            print(f"Using cached folderless lists for Space {self.id}.")
            return self._folderless_lists_cache

        print(f"Fetching folderless lists from API for Space {self.id} (Archived: {archived})...")
        endpoint = f"/space/{self.id}/list" # Endpoint for folderless lists
        params = {'archived': str(archived).lower()}
        response_data = self._request("GET", endpoint, params=params)
        list_data = response_data.get("lists", [])

        # Create List objects and update cache
        self._folderless_lists_cache = [List(self.client, lst['id'], lst.get('name'), data=lst) for lst in list_data]
        print(f"Found and cached {len(self._folderless_lists_cache)} folderless lists in Space {self.id}.")
        return self._folderless_lists_cache

    def create_list(self, name):
        """
        Creates a new folderless List within this Space.
        Ref: https://clickup.com/api/clickupreference/operation/CreateFolderlessList/

        Args:
            name (str): The name for the new list. Must be non-empty.

        Returns:
            List: A List object representing the created List.

        Raises:
            ValueError: If the provided name is empty or invalid.
        """
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("List name must be a non-empty string.")

        list_name_cleaned = name.strip()
        print(f"Creating folderless list '{list_name_cleaned}' in Space '{self.name}' (ID: {self.id})...")
        endpoint = f"/space/{self.id}/list" # Endpoint for folderless lists
        payload = {"name": list_name_cleaned}

        response_data = self._request("POST", endpoint, json=payload)
        # Create List object from response
        new_list = List(self.client, response_data['id'], response_data.get('name'), data=response_data)
        print(f"Folderless List '{new_list.name}' created successfully (ID: {new_list.id}).")

        # Update cache if it exists
        if self._folderless_lists_cache is not None:
            # Remove potential stale entry and add new one
            self._folderless_lists_cache = [l for l in self._folderless_lists_cache if l.id != new_list.id]
            self._folderless_lists_cache.append(new_list)

        return new_list
    # --- End Folderless List Management Methods ---