# task.py
from .base import ClickUpResource
# Assuming exceptions are in a utils subdirectory as per user's code
from .utils.exceptions import ClixifyException, UserNotFoundByNameError, AmbiguousUserNameError
import urllib.parse # For encoding tag names in URLs
import time # For delays in helper methods if needed

# Note: 'List' is imported locally inside methods needing it (add/remove_watcher)
# to avoid circular dependency issues at the module level.

class Task(ClickUpResource):
    """
    Represents an individual Task in ClickUp. Provides methods for interaction
    and managing related entities like comments, tags, watchers, etc.
    """
    def __init__(self, client, task_id, name=None, data=None):
        """
        Initializes the Task object.

        Args:
            client (ClickUpClient): The client for API communication.
            task_id (str): The ID of the task (canonical or custom).
            name (str, optional): Task name. Defaults to None.
            data (dict, optional): Raw task data from API. Defaults to None.
        """
        super().__init__(client)
        self.id = str(task_id)
        self.name = name
        self._data = data if data else {} # Store raw API data internally

        self._initialize_attributes() # Ensure all attributes exist with default values
        if data:
            self._populate_attributes(data) # Populate from initial data

    def _initialize_attributes(self):
        """Sets default/None values for common task attributes for type stability."""
        self.custom_id = None
        self.text_content = None
        self.description = None
        self.status = None      # ClickUp Status object
        self.orderindex = None
        self.date_created = None
        self.date_updated = None
        self.date_closed = None
        self.archived = False
        self.creator = None     # User summary object
        self.assignees = []     # List of user summary objects
        self.watchers = []      # List of user summary objects
        self.checklists = []
        self.tags = []          # List of tag objects
        self.parent = None      # Parent Task ID (str)
        self.priority = None    # Priority object or None
        self.due_date = None    # Timestamp ms string or None
        self.start_date = None  # Timestamp ms string or None
        self.time_estimate = None
        self.time_spent = None
        self.custom_fields = []
        self.dependencies = []
        self.linked_tasks = []
        self.list = None        # Summary List object
        self.folder = None      # Summary Folder object
        self.space = None       # Summary Space object
        self.url = None

    def _populate_attributes(self, data):
        """Helper method to populate attributes from the task data dictionary."""
        self.name = data.get('name', self.name)
        self.custom_id = data.get('custom_id')
        self.text_content = data.get('text_content', data.get('description')) # Prefer text_content
        self.description = data.get('description')
        self.status = data.get('status')
        self.orderindex = data.get('orderindex')
        self.date_created = data.get('date_created')
        self.date_updated = data.get('date_updated')
        self.date_closed = data.get('date_closed')
        self.archived = data.get('archived', False)
        self.creator = data.get('creator')
        self.assignees = data.get('assignees', [])
        self.watchers = data.get('watchers', [])
        self.checklists = data.get('checklists', [])
        self.tags = data.get('tags', [])
        self.parent = data.get('parent')
        self.priority = data.get('priority')
        self.due_date = data.get('due_date')
        self.start_date = data.get('start_date')
        self.time_estimate = data.get('time_estimate')
        self.time_spent = data.get('time_spent')
        self.custom_fields = data.get('custom_fields', [])
        self.dependencies = data.get('dependencies', []) # Populated by GetTask response
        self.linked_tasks = data.get('linked_tasks', []) # Populated by GetTask response
        self.list = data.get('list')
        self.folder = data.get('folder')
        self.space = data.get('space')
        self.url = data.get('url')

    def __repr__(self):
        """String representation for the Task object."""
        status_name = self.status.get('status', 'N/A') if isinstance(self.status, dict) else 'N/A'
        list_name = self.list.get('name', 'N/A') if isinstance(self.list, dict) else 'N/A'
        return f"<Task(id='{self.id}', name='{self.name}', status='{status_name}', list='{list_name}')>"

    @classmethod
    def get_by_id(cls, client, task_id, custom_id=False, team_id=None):
        """
        Fetches a task by its ID (canonical or custom) and returns a Task object.

        Args:
            client (ClickUpClient): The initialized ClickUp client instance.
            task_id (str): The ID of the task to fetch. Can be canonical or custom.
            custom_id (bool): Set to True if the provided task_id is a Custom Task ID.
                               Defaults to False (assuming canonical ID).
            team_id (str | int, optional): The Workspace/Team ID. Required if custom_id=True.

        Returns:
            Task: An instance of the Task class populated with fetched data.

        Raises:
            ValueError: If custom_id is True but team_id is not provided or task_id is empty.
            ClixifyException: If the API call fails or task is not found.
        """
        task_id_str = str(task_id).strip()
        if not task_id_str:
            raise ValueError("task_id cannot be empty.")

        # print(f"Attempting to fetch task by ID: '{task_id_str}' (Custom ID: {custom_id})...") # Removed verbose log
        endpoint = f"/task/{task_id_str}"
        params = {}

        if custom_id:
            if not team_id:
                raise ValueError("team_id is required when fetching by custom_id (custom_id=True).")
            params['custom_task_ids'] = 'true'
            params['team_id'] = str(team_id)
            # print(f"  Using query params: {params}") # Removed verbose log

        try:
            response_data = client.request("GET", endpoint, params=params)
        except Exception as e:
            # print(f"ERROR fetching task '{task_id_str}': {e}") # Error logged by client.request
            raise ClixifyException(f"Failed to fetch task '{task_id_str}'. Original error: {e}")

        if not response_data or not response_data.get('id'):
             # print(f"ERROR: Task '{task_id_str}' not found or API returned invalid data: {response_data}") # Error logged by client.request
             raise ClixifyException(f"Task '{task_id_str}' not found or invalid data received.")

        canonical_task_id = response_data.get('id')
        # print(f"Task '{response_data.get('name')}' (Canonical ID: {canonical_task_id}) fetched successfully.") # Removed verbose log
        # Use 'cls' to instantiate the class within a classmethod
        return cls(client, canonical_task_id, data=response_data)

    def get(self, include_subtasks=False):
        """
        Fetches latest details for this task from API and updates the object instance.
        Ref: https://clickup.com/api/clickupreference/operation/GetTask/

        Args:
            include_subtasks (bool): Include subtasks' details. Defaults to False.

        Returns:
            Task: The instance itself after updating its data.
        """
        # print(f"Getting details for Task ID: {self.id}...") # Removed verbose log
        endpoint = f"/task/{self.id}"
        params = {}
        if include_subtasks:
             params['include_subtasks'] = 'true'

        response_data = self._request("GET", endpoint, params=params)
        self._data = response_data
        self._populate_attributes(self._data) # Update attributes with fresh data
        # print(f"Task details retrieved for '{self.name}'.") # Removed verbose log
        return self

    def update(self, **kwargs):
        """
        Updates this task in ClickUp. Only provided fields are sent.
        Ref: https://clickup.com/api/clickupreference/operation/UpdateTask/

        Args:
            **kwargs: Task fields to update. Common examples:
                name (str), description (str), status (str), priority (int|None),
                time_estimate (int|None), due_date (int|None), start_date (int|None),
                assignees (dict: {'add': [ids], 'rem': [ids]}), archived (bool),
                parent (str|None),
                custom_fields (list[dict]): Example for Relationship field:
                    `[{'id': 'field_uuid', 'value': ['linked_task_id_1', 'linked_task_id_2']}]`
                    Value format depends on field type.

        Returns:
            Task: The instance itself after updating its data from the API response.

        Raises:
            ClixifyException: If the API call fails.
        """
        # print(f"Updating Task ID: {self.id} with args: {kwargs}") # Removed verbose log
        endpoint = f"/task/{self.id}"
        payload = {}

        # Map simple kwargs directly to payload
        simple_keys = [
            'name', 'description', 'status', 'priority', 'time_estimate',
            'due_date', 'due_date_time', 'start_date', 'start_date_time',
            'archived', 'parent'
        ]
        for key in simple_keys:
            if key in kwargs:
                payload[key] = kwargs[key]

        # Specific handling for structured arguments
        if 'assignees' in kwargs:
             if isinstance(kwargs['assignees'], dict) and ('add' in kwargs['assignees'] or 'rem' in kwargs['assignees']):
                 payload['assignees'] = kwargs['assignees']
             else:
                 # Keep essential warnings
                 print(f"Warning: 'assignees' ignored in update. Expected format {{'add': [], 'rem': []}}.")
        if 'custom_fields' in kwargs:
            if isinstance(kwargs['custom_fields'], list):
                 payload['custom_fields'] = kwargs['custom_fields']
            else:
                 # Keep essential warnings
                 print(f"Warning: 'custom_fields' ignored in update. Expected list of dicts.")

        if not payload:
            print("Warning: No valid update data provided for Task.")
            return self

        params = {} # Optional query params
        response_data = self._request("PUT", endpoint, params=params, json=payload)
        self._data = response_data
        self._populate_attributes(self._data) # Update object state from response
        # print(f"Task update request sent. Current name from API: '{self.name}'.") # Removed verbose log
        return self

    def delete(self):
        """
        Deletes this task from ClickUp. Warning: Irreversible.
        Ref: https://clickup.com/api/clickupreference/operation/DeleteTask/

        Returns:
            dict: The response from the API (often empty on success).
        """
        # print(f"Deleting Task ID: {self.id} ('{self.name}')...") # Removed verbose log
        endpoint = f"/task/{self.id}"
        params = {} # Optional query params
        response_data = self._request("DELETE", endpoint, params=params)
        # print(f"Task deletion request sent for ID: {self.id}.") # Removed verbose log
        return response_data

    # --- Comments ---
    def add_comment(self, comment_text, assignee=None, notify_all=None):
        """
        Adds a comment to this task.
        Ref: https://clickup.com/api/clickupreference/operation/CreateTaskComment/

        Args:
            comment_text (str): Text content of the comment.
            assignee (int, optional): User ID to assign the comment to.
            notify_all (bool, optional): Notify all task watchers.

        Returns:
            dict: Raw metadata of the created comment (ID, date, etc.).
        """
        # print(f"Adding comment to Task ID: {self.id}...") # Removed verbose log
        endpoint = f"/task/{self.id}/comment"
        payload = {"comment_text": comment_text}
        if assignee is not None: payload['assignee'] = assignee
        if notify_all is not None: payload['notify_all'] = notify_all

        response_data = self._request("POST", endpoint, json=payload)
        # print(f"Comment added. Response: {response_data}") # Removed verbose log
        return response_data

    def get_comments(self, start=None, start_id=None):
        """
        Retrieves comments for this task.
        Ref: https://clickup.com/api/clickupreference/operation/GetTaskComments/

        Args:
            start (int, optional): Start timestamp (ms) for comments.
            start_id (str, optional): Comment ID to start pagination from.

        Returns:
            list[dict]: List of raw comment dictionaries.
        """
        # print(f"Getting comments for Task ID: {self.id}...") # Removed verbose log
        endpoint = f"/task/{self.id}/comment"
        params = {}
        if start: params['start'] = start
        if start_id: params['start_id'] = start_id

        response_data = self._request("GET", endpoint, params=params)
        comments = response_data.get('comments', [])
        # print(f"Retrieved {len(comments)} comments.") # Removed verbose log
        return comments

    # --- Tags ---
    def add_tag(self, tag_name):
        """
        Adds an existing tag (by name) to this task. Case-insensitive.
        Tag must exist in the workspace. Does not update local `self.tags`.
        Ref: https://clickup.com/api/clickupreference/operation/AddTagToTask/

        Args:
            tag_name (str): Name of the tag to add.

        Returns:
            dict: Empty dict {} on success.
        """
        if not tag_name or not isinstance(tag_name, str):
             raise ValueError("Tag name must be a non-empty string.")
        tag_name_encoded = urllib.parse.quote(tag_name.strip())
        # print(f"Adding tag '{tag_name.strip()}' to Task ID: {self.id}...") # Removed verbose log
        endpoint = f"/task/{self.id}/tag/{tag_name_encoded}"
        response_data = self._request("POST", endpoint)
        # print(f"Tag '{tag_name.strip()}' addition request sent.") # Removed verbose log
        return response_data

    def remove_tag(self, tag_name):
        """
        Removes a tag (by name) from this task. Case-insensitive.
        Does not update local `self.tags`.
        Ref: https://clickup.com/api/clickupreference/operation/RemoveTagFromTask/

        Args:
            tag_name (str): Name of the tag to remove.

        Returns:
            dict: Empty dict {} on success.
        """
        if not tag_name or not isinstance(tag_name, str):
             raise ValueError("Tag name must be a non-empty string.")
        tag_name_encoded = urllib.parse.quote(tag_name.strip())
        # print(f"Removing tag '{tag_name.strip()}' from Task ID: {self.id}...") # Removed verbose log
        endpoint = f"/task/{self.id}/tag/{tag_name_encoded}"
        response_data = self._request("DELETE", endpoint)
        # print(f"Tag '{tag_name.strip()}' removal request sent.") # Removed verbose log
        return response_data

    # --- Watchers ---
    def add_watcher(self, user_ref):
        """
        Adds a watcher (by ID or name). Requires list context (run task.get() first).
        NOTE: Assumes POST /task/{id}/watcher with {'user_id': ...} payload.

        Args:
            user_ref (int | str): User ID or name/email query string.

        Returns:
            dict: API response.

        Raises:
            ClixifyException, UserNotFoundByNameError, AmbiguousUserNameError, TypeError
        """
        from .list import List # Import locally to avoid circular dependency
        if not self.list or not self.list.get('id'):
             raise ClixifyException(f"List context missing for Task {self.id}. Call task.get() first.")

        parent_list_id = self.list['id']
        # print(f"Attempting to add watcher '{user_ref}' to Task ID: {self.id}...") # Removed verbose log

        # Resolve the user reference using List context
        try:
             list_context = List(self.client, parent_list_id) # Temp List for context
             resolved_user_id = list_context._resolve_user_ref(user_ref)
             # print(f"Resolved watcher reference '{user_ref}' to User ID: {resolved_user_id}") # Removed verbose log
        except (UserNotFoundByNameError, AmbiguousUserNameError, TypeError, ClixifyException) as e:
             # print(f"Error resolving watcher reference '{user_ref}': {e}") # Error logged by _resolve_user_ref
             raise # Re-raise specific resolution error

        # Proceed with assumed API call structure
        endpoint = f"/task/{self.id}/watcher"
        payload = {"user_id": resolved_user_id}
        try:
            response_data = self._request("POST", endpoint, json=payload)
            # print(f"Watcher (ID: {resolved_user_id}) addition request sent.") # Removed verbose log
            return response_data
        except Exception as e:
             # print(f"ERROR during Add Watcher API call. API details might be wrong. Error: {e}") # Error logged by client.request
             raise ClixifyException(f"Failed to add watcher via API: {e}")

    def remove_watcher(self, user_ref):
        """
        Removes a watcher (by ID or name). Requires list context (run task.get() first).
        NOTE: Assumes DELETE /task/{id}/watcher with {'user_id': ...} payload.

        Args:
            user_ref (int | str): User ID or name/email query of the user to remove.

        Returns:
            dict: Empty dict {} on success typically.

        Raises:
            ClixifyException, UserNotFoundByNameError, AmbiguousUserNameError, TypeError
        """
        from .list import List # Import locally
        if not self.list or not self.list.get('id'):
             raise ClixifyException(f"List context missing for Task {self.id}. Call task.get() first.")

        parent_list_id = self.list['id']
        # print(f"Attempting to remove watcher '{user_ref}' from Task ID: {self.id}...") # Removed verbose log

        # Resolve the user reference using List context
        try:
             list_context = List(self.client, parent_list_id)
             resolved_user_id = list_context._resolve_user_ref(user_ref)
             # print(f"Resolved watcher reference '{user_ref}' to User ID: {resolved_user_id}") # Removed verbose log
        except (UserNotFoundByNameError, AmbiguousUserNameError, TypeError, ClixifyException) as e:
             # print(f"Error resolving watcher reference '{user_ref}': {e}") # Error logged by _resolve_user_ref
             raise

        # Proceed with assumed API call structure (DELETE with payload)
        endpoint = f"/task/{self.id}/watcher"
        payload = {"user_id": resolved_user_id}
        try:
            response_data = self._request("DELETE", endpoint, json=payload)
            # print(f"Watcher (ID: {resolved_user_id}) removal request sent.") # Removed verbose log
            return response_data
        except Exception as e:
            # print(f"ERROR during Remove Watcher API call. API details might be wrong. Error: {e}") # Error logged by client.request
            raise ClixifyException(f"Failed to remove watcher via API: {e}")

    # --- Subtasks ---
    def create_subtask(self, name, **kwargs):
        """
        Creates a new subtask under this task, within the same List.

        Args:
            name (str): Name of the new subtask (Required).
            **kwargs: Other task parameters (description, assignees=[IDs], status, etc.).
                      Note: Assigning by name not directly supported; resolve IDs first.

        Returns:
            Task: A Task object representing the created subtask.

        Raises:
            ClixifyException: If parent list ID is missing or creation fails.
            ValueError: If name is empty.
        """
        if not name or not isinstance(name, str) or not name.strip():
             raise ValueError("Subtask name must be a non-empty string.")
        if not self.list or not self.list.get('id'):
             raise ClixifyException(f"Cannot create subtask: Parent task {self.id} lacks list context. Call task.get() first.")

        parent_list_id = self.list['id']
        subtask_name_cleaned = name.strip()
        # print(f"Creating subtask '{subtask_name_cleaned}' under Task ID: {self.id}...") # Removed verbose log

        endpoint = f"/list/{parent_list_id}/task"
        payload = {"name": subtask_name_cleaned}
        payload.update(kwargs)
        payload['parent'] = self.id # Link to this task as parent

        # Warn if assignee names are attempted directly
        if 'assignees' in payload and any(isinstance(a, str) for a in payload.get('assignees',[])):
            print("Warning: Assigning subtasks by name requires pre-resolution of IDs.")

        response_data = self._request("POST", endpoint, json=payload)
        subtask_id = response_data.get('id')
        # print(f"Subtask creation requested. Subtask ID: {subtask_id}") # Removed verbose log

        if subtask_id:
            # Return a new Task object, initialized with response data
            return Task(self.client, subtask_id, data=response_data)
        else:
            raise ClixifyException(f"Subtask creation failed: No ID in response. API Data: {response_data}")

    # --- Dependencies ---
    def add_dependency(self, depends_on=None, dependency_of=None):
        """
        Adds a dependency link ('waiting on' or 'blocking'). Provide exactly one argument.
        Ref: https://clickup.com/api/clickupreference/operation/AddDependency/

        Args:
            depends_on (str, optional): Task ID this task is waiting on.
            dependency_of (str, optional): Task ID that waits on this task.

        Returns:
            dict: Empty dict {} on success.
        """
        if not (depends_on or dependency_of) or (depends_on and dependency_of):
            raise ValueError("Provide exactly one of 'depends_on' or 'dependency_of' task ID.")

        endpoint = f"/task/{self.id}/dependency"
        payload = {}
        link_type = ""
        if depends_on:
             payload['depends_on'] = str(depends_on)
             link_type = f"depends on Task {depends_on}"
        if dependency_of:
             payload['dependency_of'] = str(dependency_of)
             link_type = f"is dependency for Task {dependency_of}"

        # print(f"Adding dependency for Task ID: {self.id} ({link_type})...") # Removed verbose log
        response_data = self._request("POST", endpoint, json=payload)
        # print("Dependency addition request sent.") # Removed verbose log
        return response_data

    def remove_dependency(self, depends_on=None, dependency_of=None):
        """
        Removes a dependency link. Provide exactly one argument identifying the link.
        Ref: https://clickup.com/api/clickupreference/operation/DeleteDependency/

        Args:
            depends_on (str, optional): Task ID this task depends on.
            dependency_of (str, optional): Task ID that depends on this task.

        Returns:
            dict: Empty dict {} on success.
        """
        if not (depends_on or dependency_of) or (depends_on and dependency_of):
            raise ValueError("Provide exactly one of 'depends_on' or 'dependency_of' task ID to remove.")

        endpoint = f"/task/{self.id}/dependency"
        params = {} # DELETE uses query parameters here
        link_type = ""
        if depends_on:
             params['depends_on'] = str(depends_on)
             link_type = f"depends on Task {depends_on}"
        if dependency_of:
             params['dependency_of'] = str(dependency_of)
             link_type = f"is dependency for Task {dependency_of}"

        # print(f"Removing dependency for Task ID: {self.id} ({link_type})...") # Removed verbose log
        response_data = self._request("DELETE", endpoint, params=params)
        # print("Dependency removal request sent.") # Removed verbose log
        return response_data

    # --- Custom Fields ---
    def get_custom_field_value(self, field_id):
        """
        Helper to find a custom field's value from locally stored data.
        Requires task data to be populated first (e.g., by calling self.get()).

        Args:
            field_id (str): The ID of the custom field.

        Returns:
            Any | None: The value of the custom field, or None if not found/set.
        """
        # Ensure custom fields attribute exists and is a list
        if not hasattr(self, 'custom_fields') or not isinstance(self.custom_fields, list):
             print(f"Warning: Task {self.id} has no custom field data loaded. Call task.get() first.")
             return None

        for field in self.custom_fields:
            # Check if field is a dict and has an 'id' key
            if isinstance(field, dict) and field.get('id') == field_id:
                # Value access might differ based on field type; returns common 'value' key
                return field.get('value')

        # print(f"Custom field with ID '{field_id}' not found on Task {self.id}.") # Keep this potentially useful warning
        return None

    def _find_field_id_by_name(self, field_name):
        """
        Internal helper to find a custom field's ID based on its name.
        Requires self.custom_fields to be populated (call self.get() first).

        Args:
            field_name (str): The case-insensitive name of the custom field to find.

        Returns:
            str | None: The ID (UUID) of the field if found, otherwise None.
        """
        if not field_name or not isinstance(field_name, str):
             raise ValueError("Field name must be a non-empty string.")
        if not hasattr(self, 'custom_fields') or self.custom_fields is None:
             print(f"Warning: Cannot find field by name '{field_name}'. Custom fields not loaded for task {self.id}. Call task.get() first.")
             return None

        search_name_lower = field_name.strip().lower()
        # print(f"Searching for custom field named '{field_name.strip()}' on Task {self.id}...") # Removed verbose log
        for field in self.custom_fields:
            if isinstance(field, dict) and field.get('name', '').lower() == search_name_lower:
                field_id = field.get('id')
                if field_id:
                    # print(f"Found field ID '{field_id}' for field name '{field_name.strip()}'.") # Removed verbose log
                    return field_id
                else:
                    print(f"Warning: Found field named '{field_name.strip()}' but it lacks an ID.")
                    return None

        print(f"Warning: Custom field with name '{field_name.strip()}' not found on Task {self.id}.")
        return None

    def _resolve_task_ref(self, task_ref, team_id):
        """
        Internal helper to resolve a task reference (canonical ID or custom ID)
        to its canonical ID using the GET /task endpoint. Requires team_id for custom IDs.
        """
        ref_str = str(task_ref).strip()
        if not ref_str:
            raise ValueError("Task reference cannot be empty.")

        # Simple check if resolution might be needed
        needs_resolution = team_id and any(c.isalpha() or c == '-' for c in ref_str if not c.isdigit())

        if needs_resolution:
            # print(f"  Resolving potential custom task ID: '{ref_str}' using team_id: {team_id}...") # Removed verbose log
            endpoint = f"/task/{ref_str}"
            params = {'custom_task_ids': 'true', 'team_id': str(team_id)}
            try:
                task_data = self._request("GET", endpoint, params=params)
                canonical_id = task_data.get('id')
                if canonical_id:
                    # print(f"    Resolved '{ref_str}' to canonical ID: {canonical_id}") # Removed verbose log
                    return str(canonical_id)
                else:
                    print(f"    Warning: Resolved '{ref_str}' but API response lacked 'id'. Using original ref.")
                    return ref_str
            except Exception as e:
                print(f"    Warning: Failed to resolve ref '{ref_str}' (Maybe canonical or invalid? Error: {e}). Using original ref.")
                return ref_str
            # Add a small delay? Maybe not needed here as it's internal helper
            # time.sleep(0.2)
        else:
            # print(f"  Assuming ref '{ref_str}' is a canonical ID.") # Removed verbose log
            return ref_str

    def add_relationship_link(self, task_ref_to_add, field_id=None, field_name=None, team_id=None):
        """
        Adds a task link to a Relationship custom field, identified by field_id OR field_name.
        Resolves custom task IDs if team_id is provided. Uses POST /task/{id}/field/{field_id}.

        Args:
            task_ref_to_add (str): Canonical or custom ID of the task to link.
            field_id (str, optional): ID (UUID) of the Relationship custom field. Provide this OR field_name.
            field_name (str, optional): Name of the Relationship custom field. Provide this OR field_id.
            team_id (str | int, optional): Workspace/Team ID needed to resolve task custom ID.

        Returns:
            Task: The instance itself after the update operation.

        Raises:
            ValueError: If required arguments are missing/invalid.
            ClixifyException: If field cannot be found by name, resolution fails, or API call fails.
        """
        if not (field_id or field_name) or (field_id and field_name):
             raise ValueError("Provide exactly one of 'field_id' or 'field_name'.")
        if not task_ref_to_add:
             raise ValueError("task_ref_to_add cannot be empty.")

        target_field_id = field_id
        if field_name and not field_id:
             # Find field ID by name - requires custom fields to be loaded on self
             if not self.custom_fields:
                  print(f"Custom fields not loaded for Task {self.id}, attempting to fetch...")
                  self.get() # Fetch details to ensure custom fields are populated
                  if not self.custom_fields: # Check again
                        raise ClixifyException(f"Could not load custom fields for Task {self.id} to find field '{field_name}'.")

             target_field_id = self._find_field_id_by_name(field_name)
             if not target_field_id:
                  raise ClixifyException(f"Could not find custom field named '{field_name}' on Task {self.id}.")

        # Resolve the task reference to add
        try:
            canonical_id_to_add = self._resolve_task_ref(task_ref_to_add, team_id)
        except Exception as e:
             raise ClixifyException(f"Failed to resolve task reference '{task_ref_to_add}': {e}")

        # print(f"Adding link to Task ID '{canonical_id_to_add}' in Relationship field '{target_field_id}' on Task {self.id}...") # Removed verbose log
        endpoint = f"/task/{self.id}/field/{target_field_id}"
        payload = {"value": {"add": [canonical_id_to_add]}}

        response_data = self._request("POST", endpoint, json=payload)
        # print("Relationship link addition request sent.") # Removed verbose log
        self._data = response_data # Update local data from response
        self._populate_attributes(self._data)
        return self

    def remove_relationship_link(self, task_ref_to_remove, field_id=None, field_name=None, team_id=None):
        """
        Removes a task link from a Relationship custom field, identified by field_id OR field_name.
        Resolves custom task IDs if team_id is provided. Uses POST /task/{id}/field/{field_id}.

        Args:
            task_ref_to_remove (str): Canonical or custom ID of the task to unlink.
            field_id (str, optional): ID (UUID) of the Relationship custom field. Provide this OR field_name.
            field_name (str, optional): Name of the Relationship custom field. Provide this OR field_id.
            team_id (str | int, optional): Workspace/Team ID needed to resolve task custom ID.

        Returns:
            Task: The instance itself after the update operation.

        Raises:
            ValueError: If required arguments are missing/invalid.
            ClixifyException: If field cannot be found by name, resolution fails, or API call fails.
        """
        if not (field_id or field_name) or (field_id and field_name):
             raise ValueError("Provide exactly one of 'field_id' or 'field_name'.")
        if not task_ref_to_remove:
             raise ValueError("task_ref_to_remove cannot be empty.")

        target_field_id = field_id
        if field_name and not field_id:
             # Find field ID by name - requires custom fields to be loaded
             if not self.custom_fields:
                  print(f"Custom fields not loaded for Task {self.id}, attempting to fetch...")
                  self.get()
                  if not self.custom_fields:
                        raise ClixifyException(f"Could not load custom fields for Task {self.id} to find field '{field_name}'.")

             target_field_id = self._find_field_id_by_name(field_name)
             if not target_field_id:
                  raise ClixifyException(f"Could not find custom field named '{field_name}' on Task {self.id}.")

        # Resolve the task reference to remove
        try:
            canonical_id_to_remove = self._resolve_task_ref(task_ref_to_remove, team_id)
        except Exception as e:
             raise ClixifyException(f"Failed to resolve task reference '{task_ref_to_remove}': {e}")

        # print(f"Removing link to Task ID '{canonical_id_to_remove}' from Relationship field '{target_field_id}' on Task {self.id}...") # Removed verbose log
        endpoint = f"/task/{self.id}/field/{target_field_id}"
        payload = {"value": {"rem": [canonical_id_to_remove]}}

        response_data = self._request("POST", endpoint, json=payload)
        # print("Relationship link removal request sent.") # Removed verbose log
        self._data = response_data # Update local data from response
        self._populate_attributes(self._data)
        return self

    # TODO: Add methods for Checklists, Time Tracking, Attachments as needed.