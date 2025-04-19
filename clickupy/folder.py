# folder.py
from .base import ClickUpResource
from .list import List # Required for type hinting and object creation

class Folder(ClickUpResource):
    """
    Represents an individual Folder in ClickUp.
    Provides methods for managing the folder itself (get, update, delete)
    and the Lists contained within it (list_lists, create_list).
    Folder objects are typically obtained via Space methods.
    """
    def __init__(self, client, folder_id, name=None, data=None):
        """
        Initializes the Folder object.

        Args:
            client (ClickUpClient): The client object for API communication.
            folder_id (str | int): The ID of the folder.
            name (str, optional): The name of the folder. Defaults to None.
            data (dict, optional): Raw folder data as received from the API. Defaults to None.
        """
        super().__init__(client)
        self.id = str(folder_id)
        self.name = name
        self._data = data if data else {}
        # Cache for lists belonging to this folder
        self._lists_cache = None

        # Attempt to set name from data if not provided
        if name is None and data and 'name' in data:
            self.name = data['name']
        # Consider populating other relevant attributes from 'data' if needed
        # e.g., self.space = data.get('space')

    def __repr__(self):
        """String representation for the Folder object."""
        return f"<Folder(id='{self.id}', name='{self.name}')>"

    def get(self):
        """
        Fetches the latest details for this specific folder from the API.
        Updates the object's attributes based on the response.
        Ref: https://clickup.com/api/clickupreference/operation/GetFolder/

        Returns:
            Folder: The instance itself after updating its data.
        """
        print(f"Getting details for Folder ID: {self.id}...")
        endpoint = f"/folder/{self.id}"
        response_data = self._request("GET", endpoint)
        # Update internal data store and primary attributes
        self._data = response_data
        self.name = response_data.get('name', self.name)
        # Optionally update other attributes like self.space etc. here
        print(f"Folder details retrieved for '{self.name}'.")
        return self # Allows for method chaining

    def update(self, name):
        """
        Updates the name of this specific folder in ClickUp.
        Ref: https://clickup.com/api/clickupreference/operation/UpdateFolder/

        Args:
            name (str): The new, non-empty name for the folder.

        Returns:
            Folder: The instance itself after updating its data.

        Raises:
            ValueError: If the provided name is empty or not a string.
        """
        if not name or not isinstance(name, str) or not name.strip():
             raise ValueError("New folder name must be a non-empty string.")

        folder_name_cleaned = name.strip()
        print(f"Updating Folder ID: {self.id} with new name: '{folder_name_cleaned}'...")
        endpoint = f"/folder/{self.id}"
        payload = {"name": folder_name_cleaned}

        response_data = self._request("PUT", endpoint, json=payload)
        # Update internal data and attributes from the API response
        self._data = response_data
        self.name = response_data.get('name', self.name)
        print(f"Folder updated. Current name from API: '{self.name}'.")
        return self

    def delete(self):
        """
        Deletes this specific folder from ClickUp.
        Warning: This action is often irreversible.
        Ref: https://clickup.com/api/clickupreference/operation/DeleteFolder/

        Returns:
            dict: The response from the API (usually empty on success).
        """
        print(f"Deleting Folder ID: {self.id} ('{self.name}')...")
        endpoint = f"/folder/{self.id}"
        response_data = self._request("DELETE", endpoint)
        # Note: The local object still exists but represents a deleted resource.
        # Consider adding internal state like self._deleted = True if needed.
        print(f"Folder deletion request sent for ID: {self.id}.")
        return response_data

    # --- List Management Methods within Folder ---

    def list_lists(self, archived=False, force_refresh=False):
        """
        Fetches a list of all Lists within this Folder. Caches results locally.
        Ref: https://clickup.com/api/clickupreference/operation/GetLists/

        Args:
            archived (bool): Set True to include archived lists. Defaults to False.
            force_refresh (bool): Set True to bypass the local cache and fetch fresh data
                                  from the API. Defaults to False.

        Returns:
            list[List]: A list of List objects belonging to this Folder.
        """
        # Use cache if available and refresh is not forced
        if self._lists_cache is not None and not force_refresh:
            print(f"Using cached lists for Folder {self.id}.")
            return self._lists_cache

        print(f"Fetching lists from API for Folder {self.id} (Archived: {archived})...")
        endpoint = f"/folder/{self.id}/list"
        params = {'archived': str(archived).lower()}
        response_data = self._request("GET", endpoint, params=params)
        list_data = response_data.get("lists", [])

        # Create List objects from response data and update cache
        self._lists_cache = [List(self.client, lst['id'], lst.get('name'), data=lst) for lst in list_data]
        print(f"Found and cached {len(self._lists_cache)} lists in Folder {self.id}.")
        return self._lists_cache

    def create_list(self, name):
        """
        Creates a new List within this Folder.
        Ref: https://clickup.com/api/clickupreference/operation/CreateList/

        Args:
            name (str): The name for the new list. Must be non-empty.

        Returns:
            List: A List object representing the newly created List.

        Raises:
            ValueError: If the provided name is empty or not a string.
        """
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("List name must be a non-empty string.")

        list_name_cleaned = name.strip()
        print(f"Creating list '{list_name_cleaned}' in Folder '{self.name}' (ID: {self.id})...")
        endpoint = f"/folder/{self.id}/list"
        payload = {"name": list_name_cleaned}

        response_data = self._request("POST", endpoint, json=payload)
        # Create a List object from the response data
        new_list = List(self.client, response_data['id'], response_data.get('name'), data=response_data)
        print(f"List '{new_list.name}' created successfully (ID: {new_list.id}).")

        # Add the new list to the cache if it has been initialized
        if self._lists_cache is not None:
            self._lists_cache = [l for l in self._lists_cache if l.id != new_list.id] # Remove potential old version
            self._lists_cache.append(new_list) # Add new list

        return new_list
    # --- End List Management Methods ---