# run_test_create_assign_no_delete.py
# Focuses on Creation, Assignment, Unassignment - No Tags/Custom Fields/Watchers tests. NO DELETE.
import os
import sys
import time
from dotenv import load_dotenv
# Make sure 'clickupy' is the correct name of your library package directory
from clickupy.client import ClickUpClient
from clickupy.team import Team  # <--- أضف هذا السطر هنا
# Import custom exceptions if you want specific handling below
from clickupy.utils.exceptions import UserNotFoundByNameError, AmbiguousUserNameError, ClickupyException

# --- Diagnostics ---
print("--- Python Environment ---")
print("Python Version:", sys.version.split()[0])
print("Current Working Directory:", os.getcwd())
print("-" * 26)
# --- ---

print("\nInitializing ClickUp Client...")
try:
    client = ClickUpClient()
    print("ClickUp Client initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize ClickUp Client: {e}")
    exit(1)

print("\nGetting Team manager...")
team_manager = Team(client)

# --- ⚠️ CONFIGURATION - USER MUST EDIT THESE ⚠️ ---
workspace_name_to_find = "Testing"  # <--- *** CHANGE THIS ***
assignee_name_to_resolve = "shaawa"             # <--- *** CHANGE THIS to a name likely to match ONE user ***
# --- Test Resource Names ---
test_space_name = "clickupy_AssignFocus_Space_NoDel" # Changed name slightly
test_list_name = "clickupy_AssignFocus_List_NoDel"
task1_name = "Task 1 - Assign/Unassign Test (No Delete)"
task2_name = "Task 2 - Dependency Test (No Delete)"
subtask_name = "Subtask for Task 1 (No Delete)"
# --- ---

print(f"\nAttempting to find Workspace: '{workspace_name_to_find}'...")
try:
    my_workspace = team_manager.get_workspace(workspace_name_to_find)
except Exception as e:
    print(f"ERROR getting workspace: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

if my_workspace:
    print(f"Successfully found Workspace: {my_workspace.name} (ID: {my_workspace.id})")
    # Initialize resource variables
    test_space = None
    test_list = None
    task1 = None
    task2 = None
    subtask1 = None
    resolved_assignee_id = None # To store resolved ID for assignment tests

    # --- === Main Testing Block === ---
    try:
        # === Setup: Create Space and List ===
        print(f"\n=== Setup Phase ===")
        print(f"Attempting to create test Space: '{test_space_name}'...")
        test_space = my_workspace.create_space(test_space_name)
        if not test_space or not test_space.id: raise ClickupyException("Space creation failed.")
        print(f"Space created: '{test_space.name}' (ID: {test_space.id})")
        print("Pausing for 2 seconds...")
        time.sleep(2)

        print(f"Attempting to create test List: '{test_list_name}' in Space '{test_space.name}'...")
        test_list = test_space.create_list(test_list_name)
        if not test_list or not test_list.id: raise ClickupyException("List creation failed.")
        print(f"List created: '{test_list.name}' (ID: {test_list.id})")
        print("Pausing for 2 seconds...")
        time.sleep(2)

        # === Setup: Get List Members & Resolve Assignee ===
        print(f"\nGetting members for List '{test_list.name}'...")
        list_members = test_list.get_members() # Fetches and caches members
        if list_members:
             print(f"Found {len(list_members)} members.")
             # Attempt to resolve the specific assignee name for testing
             try:
                  resolved_assignee_id = test_list._resolve_user_ref(assignee_name_to_resolve)
                  print(f"Successfully resolved '{assignee_name_to_resolve}' to User ID {resolved_assignee_id}. Will use for assignment/unassignment tests.")
             except (UserNotFoundByNameError, AmbiguousUserNameError) as e:
                  print(f"Warning: Could not resolve assignee '{assignee_name_to_resolve}' for tests: {e}. Assignment tests might be limited.")
             except Exception as resolve_err:
                  print(f"Warning: Error resolving assignee '{assignee_name_to_resolve}': {resolve_err}")
        else:
            print("Warning: Could not retrieve list members. Assignment tests might fail.")

        # === Setup: Create Base Tasks ===
        print("\nCreating base tasks...")
        # Create Task 1 initially unassigned
        task1 = test_list.create_task(name=task1_name)
        if not task1 or not task1.id: raise ClickupyException("Task 1 creation failed.")
        print(f"Task 1 created (unassigned): '{task1.name}' (ID: {task1.id})")
        time.sleep(1)

        # Create Task 2 assigned to the resolved user (if possible)
        task2_payload = {}
        if resolved_assignee_id:
             task2_payload['assignees'] = [resolved_assignee_id]
             print(f"Attempting to create Task 2 assigned to ID: {resolved_assignee_id}")
        else:
             print("Attempting to create Task 2 unassigned (assignee not resolved).")

        task2 = test_list.create_task(name=task2_name, **task2_payload)
        if not task2 or not task2.id: raise ClickupyException("Task 2 creation failed.")
        print(f"Task 2 created: '{task2.name}' (ID: {task2.id})")
        time.sleep(1)

        # ==========================================================
        # === Start Testing Core Task Methods (Focus on Assignment) ===
        # ==========================================================
        print(f"\n=== Testing Methods on Task 1 (ID: {task1.id}) and Task 2 (ID: {task2.id}) ===")

        # --- Test Comments (Keep as basic interaction) ---
        print("\n--- Testing Comments ---")
        try:
            comment_text = f"Test comment added via script at {time.time()}"
            print(f"Adding comment to Task 1: '{comment_text}'")
            comment_info = task1.add_comment(comment_text=comment_text)
            print(f"Comment add response: {comment_info}")
            time.sleep(1)
            print("Getting comments for Task 1...")
            comments = task1.get_comments()
            if comments:
                print(f"Found {len(comments)} comments. Last comment text:")
                print(f"  '{comments[-1].get('comment_text')}' by {comments[-1].get('user',{}).get('username')}")
            else: print("No comments found.")
        except Exception as e: print(f"ERROR during comment tests: {e}")

        # --- Test Task Update (Assign / Unassign Task 1) ---
        print("\n--- Testing Task Update (Assign/Unassign) ---")
        if task1 and task1.id and resolved_assignee_id:
            try:
                # 1. Assign the resolved user to Task 1
                print(f"Attempting to assign Task 1 to User ID {resolved_assignee_id} via update...")
                # Use the specific 'assignees' payload format for update
                assign_payload = {"add": [resolved_assignee_id]}
                task1.update(assignees=assign_payload, description="Task 1 assigned via update.")
                print(f"Task 1 update request (assign) sent.")
                print("Pausing for 2 seconds...")
                time.sleep(2)
                # Verify assignment by fetching task data again
                task1.get()
                assignees_after_add = [a.get('id') for a in task1.assignees]
                if resolved_assignee_id in assignees_after_add:
                    print(f"Verification: User ID {resolved_assignee_id} successfully assigned to Task 1. Current Assignee IDs: {assignees_after_add}")
                else:
                    print(f"ERROR: User ID {resolved_assignee_id} not found in assignees after attempting assignment! Found: {assignees_after_add}")

                # 2. Unassign the same user from Task 1
                print(f"Attempting to unassign Task 1 from User ID {resolved_assignee_id} via update...")
                # Use the specific 'assignees' payload format for update
                unassign_payload = {"rem": [resolved_assignee_id]}
                task1.update(assignees=unassign_payload, description="Task 1 unassigned via update.")
                print(f"Task 1 update request (unassign) sent.")
                print("Pausing for 2 seconds...")
                time.sleep(2)
                 # Verify unassignment by fetching task data again
                task1.get()
                assignees_after_rem = [a.get('id') for a in task1.assignees]
                if resolved_assignee_id not in assignees_after_rem:
                    print(f"Verification: User ID {resolved_assignee_id} successfully unassigned from Task 1. Current Assignee IDs: {assignees_after_rem}")
                else:
                    print(f"ERROR: User ID {resolved_assignee_id} still found in assignees after attempting unassignment! Found: {assignees_after_rem}")

            except Exception as e:
                 print(f"ERROR during Task 1 assignment/unassignment update tests: {e}")
                 import traceback
                 traceback.print_exc()
        elif not resolved_assignee_id:
             print("Skipping assign/unassign tests because target user ID ('{assignee_name_to_resolve}') was not resolved.")
        else:
            print("Skipping assign/unassign tests because Task 1 object is not valid.")

        # --- Test Subtask Creation (Keep as it's a creation) ---
        print("\n--- Testing Subtask Creation ---")
        if task1 and task1.id:
            try:
                print(f"Creating subtask '{subtask_name}' under Task 1...")
                task1.get() # Ensure parent task has list context
                subtask1 = task1.create_subtask(name=subtask_name, description="A test subtask (no delete)")
                if subtask1 and subtask1.id:
                    print(f"Subtask created: '{subtask1.name}' (ID: {subtask1.id})")
                    print(f"  Subtask's parent ID: {subtask1.parent}")
                    if subtask1.parent != task1.id: print(f"ERROR: Subtask parent ID mismatch!")
                else: print("ERROR: Subtask creation failed or returned invalid object.")
            except Exception as e: print(f"ERROR creating subtask: {e}")
        else: print("Skipping subtask tests because task1 object is not valid.")

        # --- Test Dependencies (Keep as it's relating creations) ---
        print("\n--- Testing Dependencies ---")
        if task1 and task1.id and task2 and task2.id:
            try:
                print(f"Adding dependency: Task 2 depends on Task 1...")
                task2.add_dependency(depends_on=task1.id)
                time.sleep(2); task2.get() # Refresh task 2
                dep_found = any(dep.get('depends_on') == task1.id for dep in task2.dependencies)
                if dep_found: print("Verified 'depends_on' dependency was added.")
                else: print("ERROR: Dependency not found after adding!")

                print(f"Removing dependency: Task 2 depends on Task 1...")
                task2.remove_dependency(depends_on=task1.id)
                time.sleep(2); task2.get() # Refresh task 2
                dep_found_after_remove = any(dep.get('depends_on') == task1.id for dep in task2.dependencies)
                if not dep_found_after_remove: print("Verified dependency was removed.")
                else: print("ERROR: Dependency still found after removing!")
            except Exception as e: print(f"ERROR during dependency tests: {e}")
        else: print("Skipping dependency tests as base tasks are missing.")

        # --- REMOVED TAGS TEST SECTION ---
        # --- REMOVED CUSTOM FIELDS TEST SECTION ---
        # --- REMOVED WATCHERS TEST SECTION ---


        # === Final List Tasks ===
        print(f"\n--- Final Listing of Tasks in List '{test_list.name}' (Including Subtasks) ---")
        if test_list and test_list.id:
            try:
                final_tasks_in_list = test_list.list_tasks(include_closed=True, subtasks=True)
                print(f"Found {len(final_tasks_in_list)} tasks/subtasks in total:")
                if final_tasks_in_list:
                    for task_obj in final_tasks_in_list:
                        assignees = [a.get('username', 'N/A') for a in task_obj.assignees]
                        status = task_obj.status.get('status', 'N/A') if task_obj.status else 'N/A'
                        parent_info = f"(Parent: {task_obj.parent})" if task_obj.parent else ""
                        print(f" - ID: {task_obj.id}, Name: {task_obj.name}, Status: {status}, Assignees: {assignees} {parent_info}")
                else: print("List appears empty.")
            except Exception as e: print(f"ERROR listing final tasks: {e}")
        else: print("Skipping final list tasks as test_list object is not valid.")


    # --- Main Exception Handling ---
    except Exception as e:
        print(f"\nFATAL ERROR during main test operations: {e}")
        import traceback
        traceback.print_exc()

    # --- Final 'No Delete' Block ---
    finally:
        print("\n" + "="*40)
        print("--- TEST SCRIPT FINISHED - SKIPPING DELETION ---")
        print("Resources were NOT automatically deleted as requested.")
        # Displaying info about potentially created resources
        if test_space and test_space.id: print(f" - Test Space: '{test_space.name}' (ID: {test_space.id})")
        if test_list and test_list.id: print(f" - Test List: '{test_list.name}' (ID: {test_list.id})")
        if task1 and task1.id: print(f" - Task 1: '{task1.name}' (ID: {task1.id})")
        task2_display = task2.name if task2 and hasattr(task2, 'name') and task2.name else task2_name
        if task2 and task2.id: print(f" - Task 2: '{task2_display}' (ID: {task2.id})")
        if subtask1 and subtask1.id: print(f" - Subtask: '{subtask1.name}' (ID: {subtask1.id}) Parent: {subtask1.parent}")
        print("\n==> IMPORTANT: Please DELETE these resources MANUALLY in ClickUp. <==")
        print("="*40)

# --- End of main Workspace check ---
else:
    print(f"ERROR: Workspace '{workspace_name_to_find}' not found.")

print("\nOverall test script finished execution.")