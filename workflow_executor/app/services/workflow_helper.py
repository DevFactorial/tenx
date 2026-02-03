from typing import List, Sequence, Dict, Any

from typing import Any, Dict, List, Set

class WorkflowDependencyError(Exception):
    """Raised when a required dependency has failed."""
    pass

def is_node_completed(node: Dict[str, Any], completed_task_ids: Set[str]) -> bool:
    """Checks if a node is fully finished."""
    if node.get("type") == "TASK":
        return node.get("id") in completed_task_ids
    
    # A Group is completed only if all its internal tasks are completed
    group_tasks = node.get("tasks", [])
    if not group_tasks:
        return True
    return all(is_node_completed(child, completed_task_ids) for child in group_tasks)

def is_node_started(node: Dict[str, Any], active_ids: Set[str]) -> bool:
    """Checks if a node or any part of it has already been triggered/started."""
    if node.get("type") == "TASK":
        return node.get("id") in active_ids
    
    # A Group is started if ANY child has started or finished
    return any(is_node_started(child, active_ids) for child in node.get("tasks", []))

def is_node_failed(node: Dict[str, Any], failed_task_ids: Set[str]) -> bool:
    """Checks if a node or any part of its group has failed."""
    if node.get("type") == "TASK":
        return node.get("id") in failed_task_ids
    
    # A Group is failed if ANY of its children have failed
    return any(is_node_failed(child, failed_task_ids) for child in node.get("tasks", []))

def get_all_nodes_map(tasks_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Flattens the nested structure into a flat ID-to-Node map for dependency lookups."""
    node_map = {}
    for node in tasks_list:
        node_map[node["id"]] = node
        if node.get("type") == "TASK_GROUP":
            # Recursively merge internal maps
            node_map.update(get_all_nodes_map(node.get("tasks", [])))
    return node_map

def find_next_tasks(
    workflow_defn: Dict[str, Any], 
    completed_task_ids: Set[str],
    in_progress_task_ids: Set[str],
    failed_task_ids: Set[str] # Added this set
) -> List[Dict[str, Any]]:
    
    next_to_run = []
    active_ids = completed_task_ids.union(in_progress_task_ids).union(failed_task_ids)
    all_tasks = workflow_defn.get("tasks", [])
    node_map = get_all_nodes_map(all_tasks)

    nodes_to_check = list(all_tasks)
    
    while nodes_to_check:
        current_node = nodes_to_check.pop(0)
        
        # 1. Skip if already finished
        if is_node_completed(current_node, completed_task_ids):
            if current_node.get("type") == "TASK_GROUP":
                nodes_to_check.extend(current_node.get("tasks", []))
            continue

        # 2. Skip if started (prevents double-launching)
        if is_node_started(current_node, active_ids):
            if current_node.get("type") == "TASK_GROUP":
                nodes_to_check.extend(current_node.get("tasks", []))
            continue

        # 3. Dependency Check with Fail-Fast
        run_after = current_node.get("run_after", [])
        
        dependencies_met = True
        for dep_id in run_after:
            dep_node = node_map.get(dep_id)
            if not dep_node:
                continue
            
            # FAIL-FAST: If a dependency is failed, the whole path is blocked
            if is_node_failed(dep_node, failed_task_ids):
                raise WorkflowDependencyError(
                    f"Dependency {dep_id} failed. Cannot proceed with {current_node.get('id')}."
                )

            if not is_node_completed(dep_node, completed_task_ids):
                dependencies_met = False
                break
        
        if dependencies_met:
            next_to_run.append(current_node)
            
    return next_to_run


def resolve_task_inputs(
        current_task_input: List[Dict[str, Any]], 
        workflow_input: Dict[str, Any], 
        completed_tasks_outputs: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Resolves input values for a task based on its mapping configuration.
        
        Args:
            current_task_input: The 'input' list from the current task definition.
            workflow_input: The actual runtime values provided for the workflow.
            completed_tasks_outputs: A map of task names to their produced outputs.
                                    e.g., {"create_file": {"dir_name_path": "/tmp/test"}}
        """
        resolved_input = []

        for mapping in current_task_input:
            # Create a copy of the mapping to avoid mutating the original definition
            mapping_copy = mapping.copy()
            fetch_from = mapping_copy.get("fetch_from")
            fetch_key = mapping_copy.get("fetch_key")

            if fetch_from == "WORKFLOW_INPUT":
                # Map from top-level workflow input
                # Example: fetch_key "file_name" -> workflow_input["file_name"]
                mapping_copy["value"] = workflow_input.get(fetch_key, mapping_copy.get("value"))

            elif fetch_from == "TASK_OUTPUT":
                # Map from a previous task's output
                # Expected fetch_key format: "task_name.output_name"
                if fetch_key and "." in fetch_key:
                    source_task_name, output_field = fetch_key.split(".", 1)
                    
                    # Look up the task in our completed map
                    task_output_data = completed_tasks_outputs.get(source_task_name, {})
                    
                    # Update value if found, otherwise keep existing/default
                    mapping_copy["value"] = task_output_data.get(output_field, mapping_copy.get("value"))

            elif fetch_from == "STATIC_VALUE":
                # Value is already set in the definition, no action needed
                pass

            resolved_input.append(mapping_copy)

        return resolved_input


