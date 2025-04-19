# list.py
from .base import ClickUpResource
from .task import Task
from .utils.exceptions import ClixifyException, UserNotFoundByNameError, AmbiguousUserNameError

class List(ClickUpResource):
    """
    Represents an individual List object in ClickUp.
    Provides methods to interact with this specific list (get details, update, delete)
    and manage Tasks within it (list_tasks, create_task, get_members).
    """
    def __init__(self, client, list_id, name=None, data=None):
        """
        Initializes the List object.

        Args:
            client (ClickUpClient): The client object for API communication.
            list_id (str | int): The ID of the list.
            name (str, optional): The name of the list. Defaults to None.
            data (dict, optional): Raw list data as received from the API. Defaults to None.
        """
        super().__init__(client)
        self.id = str(list_id)
        self.name = name
        self._data = data if data else {}
        # Cache for list members, initialized when get_members is first called successfully
        self._members_cache = None

        # Initialize attributes from data if provided
        if data:
            self._populate_attributes(data)
        # Ensure name is set if passed directly and not available in initial data
        elif name is None and data and 'name' in data:
             self.name = data['name'] # Should be handled by _populate now, but safe fallback


    def _populate_attributes(self, data):
        """Helper method to populate instance attributes from a data dictionary."""
        self.name = data.get('name', self.name)
        self.orderindex = data.get('orderindex')
        self.content = data.get('content')
        self.status = data.get('status') # Status object/color e.g. {'status': 'Open', 'color': '#d3d3d3',...}
        self.priority = data.get('priority') # Priority object e.g. {'priority': 'urgent', 'color': '#ff0000',...}
        self.assignee = data.get('assignee') # Usually null for Lists
        self.due_date = data.get('due_date') # Timestamp ms string or None
        self.start_date = data.get('start_date') # Timestamp ms string or None
        self.folder = data.get('folder') # Folder object summary {'id': '...', 'name': '...'}
        self.space = data.get('space') # Space object summary {'id': '...', 'name': '...'}
        self.archived = data.get('archived', False)
        self.override_statuses = data.get('override_statuses') # Boolean or None
        self.statuses = data.get('statuses') # List of status objects if override_statuses=True
        self.permission_level = data.get('permission_level')
        # Consider adding other useful fields like 'task_count'

    def __repr__(self):
        """String representation for the List object."""
        # Safely access nested names
        folder_name = self.folder.get('name', 'N/A') if isinstance(self.folder, dict) else 'None'
        space_name = self.space.get('name', 'N/A') if isinstance(self.space, dict) else 'N/A'
        return f"<List(id='{self.id}', name='{self.name}', space='{space_name}', folder='{folder_name}')>"

    def get(self):
        """
        Fetches the latest details for this list from the API and updates the object.
        Ref: https://clickup.com/api/clickupreference/operation/GetList/

        Returns:
            List: The instance itself after updating its data.
        """
        print(f"Getting details for List ID: {self.id}...")
        endpoint = f"/list/{self.id}"
        response_data = self._request("GET", endpoint)
        self._data = response_data
        self._populate_attributes(self._data) # Update attributes with fetched data
        print(f"List details retrieved for '{self.name}'.")
        return self

    def update(self, name=None, content=None, due_date=None, due_date_time=None,
               priority=None, assignee_add=None, assignee_rem=None, status=None,
               unset_status=None):
        """
        Updates this list in ClickUp. Only provided fields are sent.
        Ref: https://clickup.com/api/clickupreference/operation/UpdateList/

        Args:
            name (str, optional): New name.
            content (str, optional): New description. API behavior for clearing might vary.
            due_date (int | None, optional): Due date timestamp (ms) or None to remove.
            due_date_time (bool, optional): True if due_date includes time.
            priority (int | None, optional): Priority number or None to remove.
            assignee_add (int, optional): User ID to add as assignee.
            assignee_rem (int, optional): User ID to remove as assignee.
            status (str, optional): Status text (depends on space settings).
            unset_status (bool, optional): True to remove list status.

        Returns:
            List: The instance itself after updating attributes from the API response.
        """
        print(f"Updating List ID: {self.id}...")
        endpoint = f"/list/{self.id}"
        payload = {}

        # Build payload with provided (non-None) arguments
        if name is not None: payload['name'] = name
        if content is not None: payload['content'] = content
        if due_date is not None: payload['due_date'] = due_date
        if due_date is not None and due_date_time is not None: # Only relevant if due_date is set
            payload['due_date_time'] = due_date_time
        if priority is not None: payload['priority'] = priority # API expects int or null
        # Build assignee payload if needed
        assignee_payload = {}
        if assignee_add is not None: assignee_payload['add'] = assignee_add
        if assignee_rem is not None: assignee_payload['rem'] = assignee_rem
        if assignee_payload: payload['assignee'] = assignee_payload
        # ---
        if status is not None: payload['status'] = status
        if unset_status is not None: payload['unset_status'] = unset_status

        if not payload:
            print("Warning: No update data provided for List.")
            return self

        response_data = self._request("PUT", endpoint, json=payload)
        self._data = response_data
        self._populate_attributes(self._data) # Update attributes with response data
        print(f"List update request sent. Current name from API: '{self.name}'.")
        return self

    def delete(self):
        """
        Deletes this list from ClickUp. Warning: Irreversible.
        Ref: https://clickup.com/api/clickupreference/operation/DeleteList/

        Returns:
            dict: The response from the API (often empty on success).
        """
        print(f"Deleting List ID: {self.id} ('{self.name}')...")
        endpoint = f"/list/{self.id}"
        response_data = self._request("DELETE", endpoint)
        print(f"List deletion request sent for ID: {self.id}.")
        return response_data

    def get_members(self, force_refresh=False):
        """
        Fetches members with access to this List. Uses cache unless forced.
        Ref: https://clickup.com/api/clickupreference/operation/GetListMembers/

        Args:
            force_refresh (bool): Ignore cache and fetch fresh data. Defaults to False.

        Returns:
            list[dict]: List of member dictionaries (incl. 'id', 'username', 'role'). Empty list on error.
        """
        if self._members_cache is not None and not force_refresh:
             print(f"Using cached members for List {self.id}.")
             return self._members_cache

        print(f"Fetching members for List ID: {self.id} ('{self.name}')...")
        endpoint = f"/list/{self.id}/member"
        try:
            response_data = self._request("GET", endpoint)
            self._members_cache = response_data.get("members", []) # Store in cache
            print(f"Found {len(self._members_cache)} members with access to List {self.id}.")
            return self._members_cache
        except Exception as e:
            print(f"Error fetching members for List {self.id}: {e}")
            self._members_cache = None # Invalidate cache on error
            return []

    def _resolve_user_ref(self, user_ref):
        """
        Resolves a user reference (ID or name query) to a user ID within this list's members.
        Uses cached members if available, fetches otherwise. Case-insensitive check on username/email.

        Args:
            user_ref (int | str): User ID or name query string.

        Returns:
            int: The resolved User ID.

        Raises:
            UserNotFoundByNameError, AmbiguousUserNameError, TypeError, ClixifyException
        """
        if isinstance(user_ref, int):
            return user_ref # Assume valid ID
        elif not isinstance(user_ref, str) or not user_ref.strip():
            raise TypeError(f"User reference must be an integer ID or a non-empty string name, got {type(user_ref)}.")

        name_query = user_ref.strip()
        name_query_lower = name_query.lower()
        print(f"Resolving user reference query: '{name_query}' in List '{self.name}'...")

        members = self.get_members() # Uses the caching mechanism within get_members
        if not members:
            print(f"Cannot resolve name '{name_query}': Member list empty/unavailable for List {self.id}.")
            raise UserNotFoundByNameError(name_query, self.id)

        matches = []
        for member in members:
            username = str(member.get('username', '')).lower()
            email = str(member.get('email', '')).lower()
            # Match if query is substring of username or email
            if name_query_lower in username or name_query_lower in email:
                matches.append(member)

        # Handle match results
        if len(matches) == 1:
            user_id = matches[0].get('id')
            username_match = matches[0].get('username', 'N/A')
            print(f"Resolved '{name_query}' to User ID: {user_id} ('{username_match}')")
            if user_id is None:
                 raise ClixifyException(f"Matching user found for '{name_query}' but ID is missing.")
            return user_id
        elif len(matches) == 0:
            print(f"No user found matching '{name_query}' in List {self.id}.")
            raise UserNotFoundByNameError(name_query, self.id)
        else: # More than 1 match
            print(f"Ambiguous user reference '{name_query}'. Found {len(matches)} matches.")
            raise AmbiguousUserNameError(name_query, matches, self.id)


    # --- Task Management Methods within List ---
    def create_task(self, name, assignees=None, **kwargs):
        """
        Creates a new task within this List, resolving assignee names/IDs.
        Ref: https://clickup.com/api/clickupreference/operation/CreateTask/

        Args:
            name (str): The name of the new task (Required).
            assignees (list[int | str], optional): List of User IDs or names to assign.
            **kwargs: Other task parameters (description, tags, status, priority, due_date, etc.).

        Returns:
            Task: A Task object representing the created task.

        Raises:
            UserNotFoundByNameError, AmbiguousUserNameError, TypeError, ValueError, ClixifyException
        """
        if not name or not isinstance(name, str) or not name.strip():
             raise ValueError("Task name must be a non-empty string.")
        task_name_cleaned = name.strip()

        print(f"Attempting to create task '{task_name_cleaned}' in List '{self.name}' (ID: {self.id})...")
        endpoint = f"/list/{self.id}/task"
        payload = {"name": task_name_cleaned}

        # Resolve assignees if provided
        if assignees is not None:
            if not isinstance(assignees, list):
                raise TypeError("'assignees' parameter must be a list of User IDs (int) or names (str).")

            print(f"Resolving assignees specified: {assignees}")
            unique_resolved_ids = set()
            for assignee_ref in assignees:
                # Resolve each assignee using the helper method - will raise errors on failure
                resolved_id = self._resolve_user_ref(assignee_ref)
                unique_resolved_ids.add(resolved_id)

            resolved_assignee_ids = list(unique_resolved_ids)
            if resolved_assignee_ids:
                payload['assignees'] = resolved_assignee_ids
                print(f"Task will be created with Assignee IDs: {resolved_assignee_ids}")
            # If list was empty or resolution failed, exception would have been raised

        payload.update(kwargs) # Add other keyword arguments

        print(f"Sending task creation payload: {payload}")
        response_data = self._request("POST", endpoint, json=payload)
        created_task_id = response_data.get('id')
        print(f"Task creation requested. Task ID from response: {created_task_id}")

        if created_task_id:
            # Instantiate and return Task object
            return Task(self.client, created_task_id, data=response_data)
        else:
            # Should not happen if API call returns 200 OK, indicates API issue or unexpected response format
            print(f"Error: Task creation API call succeeded but no Task ID found in response: {response_data}")
            raise ClixifyException("Task creation succeeded but no Task ID found in response.")

    def list_tasks(self, get_all=False, archived=False, page=0, order_by=None, reverse=None,
                   subtasks=None, statuses=None, include_closed=None, assignees=None,
                   due_date_gt=None, due_date_lt=None, date_created_gt=None, date_created_lt=None,
                   date_updated_gt=None, date_updated_lt=None, custom_fields=None):
        """
        Fetches tasks within this List, with filtering, pagination, and optional auto-fetching of all pages.
        Ref: https://clickup.com/api/clickupreference/operation/GetTasks/

        Args:
            get_all (bool): Fetch all pages if True. Defaults to False.
            archived (bool): Include archived tasks. Defaults to False.
            page (int): Page number (0-indexed). Used only if get_all=False. Defaults to 0.
            order_by (str): Sort field ('id', 'created', 'updated', 'due_date').
            reverse (bool): Reverse sort order.
            subtasks (bool): Include subtasks.
            statuses (list[str]): Filter by status names (case-insensitive).
            include_closed (bool): Include tasks with a closed status. Defaults to False.
            assignees (list[int]): Filter by assignee User IDs.
            due_date_gt (int): Filter due date greater than (ms timestamp).
            due_date_lt (int): Filter due date less than (ms timestamp).
            # ... other date/custom field filters ...

        Returns:
            list[Task]: A list of Task objects matching the criteria.
        """
        print(f"Fetching tasks for List '{self.name}' (ID: {self.id}) (GetAll: {get_all})...")
        endpoint = f"/list/{self.id}/task"
        base_params = {} # Base parameters used for all page requests

        # Build base params dictionary from provided filters
        if archived: base_params['archived'] = 'true'
        if order_by: base_params['order_by'] = order_by
        if reverse is not None: base_params['reverse'] = str(reverse).lower()
        if subtasks is not None: base_params['subtasks'] = str(subtasks).lower()
        if include_closed: base_params['include_closed'] = 'true'
        if due_date_gt: base_params['due_date_gt'] = due_date_gt
        if due_date_lt: base_params['due_date_lt'] = due_date_lt
        if date_created_gt: base_params['date_created_gt'] = date_created_gt
        if date_created_lt: base_params['date_created_lt'] = date_created_lt
        if date_updated_gt: base_params['date_updated_gt'] = date_updated_gt
        if date_updated_lt: base_params['date_updated_lt'] = date_updated_lt
        if custom_fields: base_params['custom_fields'] = custom_fields
        # Pass lists directly, requests library handles array formatting in query params
        if statuses: base_params['statuses'] = statuses
        if assignees: base_params['assignees'] = assignees


        all_task_objects = []
        current_page = 0

        if get_all:
            # Fetch all pages sequentially
            print("Pagination mode: Fetching all pages...")
            while True:
                page_params = base_params.copy()
                page_params['page'] = current_page
                print(f"  Fetching page {current_page}...")
                try:
                    response_data = self._request("GET", endpoint, params=page_params)
                    tasks_list_data = response_data.get("tasks", [])
                except Exception as e:
                    print(f"  ERROR fetching page {current_page}: {e}")
                    break # Stop pagination on error

                if not tasks_list_data:
                    # Stop when an empty task list is received, indicating the end
                    print(f"  No more tasks found on page {current_page}. Pagination finished.")
                    break

                print(f"  Found {len(tasks_list_data)} tasks on page {current_page}.")
                for task_data in tasks_list_data:
                    all_task_objects.append(Task(self.client, task_data['id'], data=task_data))

                current_page += 1
                # Loop continues, delay is handled by client before next request

            print(f"Total tasks fetched across all pages: {len(all_task_objects)}")
            return all_task_objects

        else:
            # Fetch only the specified single page
            page_params = base_params.copy()
            page_params['page'] = page
            print(f"Pagination mode: Fetching single page {page}...")
            try:
                response_data = self._request("GET", endpoint, params=page_params)
                tasks_list_data = response_data.get("tasks", [])
                print(f"Found {len(tasks_list_data)} tasks on page {page}.")
                # Instantiate Task objects for this page
                tasks_on_page = [Task(self.client, td['id'], data=td) for td in tasks_list_data]
                return tasks_on_page
            except Exception as e:
                 print(f"ERROR fetching page {page}: {e}")
                 return [] # Return empty list on error for single page fetch