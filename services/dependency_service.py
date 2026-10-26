"""Dependency Management and Graph Validation Service.

Pure deterministic Python implementation for:
- Dependency validation
- Circular dependency detection (Cycle Detection using DFS)
- Invalid task ID detection
- Ready-to-execute status evaluation
- Dependency bottleneck and wait-reasoning generation
"""
from typing import Dict, List, Optional, Set, Tuple
from models.schemas import Task, TaskStatus


class DependencyValidationResult:
    def __init__(
        self,
        is_valid: bool,
        cycles: List[List[str]],
        invalid_references: Dict[str, List[str]],
        error_messages: List[str],
    ):
        self.is_valid = is_valid
        self.cycles = cycles  # e.g., [["TASK-1", "TASK-2", "TASK-1"]]
        self.invalid_references = invalid_references  # {"TASK-3": ["TASK-99"]}
        self.error_messages = error_messages


class TaskReadiness:
    def __init__(
        self,
        task_id: str,
        is_ready: bool,
        missing_dependencies: List[str],
        reason: str,
    ):
        self.task_id = task_id
        self.is_ready = is_ready
        self.missing_dependencies = missing_dependencies
        self.reason = reason


class DependencyService:
    @staticmethod
    def validate_dependencies(tasks: List[Task]) -> DependencyValidationResult:
        """Validates all task dependencies: checks for missing IDs and cycles."""
        task_id_set = {t.id.upper() for t in tasks}
        invalid_refs: Dict[str, List[str]] = {}
        error_messages: List[str] = []
        cycles: List[List[str]] = []

        # 1. Check for invalid task references
        for task in tasks:
            tid = task.id.upper()
            bad_deps = [dep.upper() for dep in task.dependencies if dep.upper() not in task_id_set]
            if bad_deps:
                invalid_refs[tid] = bad_deps
                error_messages.append(
                    f"Task {tid} references non-existent dependencies: {', '.join(bad_deps)}"
                )

        # 2. Cycle Detection using DFS
        # Graph: edge from U -> V means U depends on V (or V must finish before U)
        # Here: adj[u] = list of prerequisite task IDs that 'u' directly depends on
        adj: Dict[str, List[str]] = {t.id.upper(): [] for t in tasks}
        for task in tasks:
            tid = task.id.upper()
            for dep in task.dependencies:
                dep_norm = dep.upper()
                if dep_norm in task_id_set and dep_norm != tid:
                    adj[tid].append(dep_norm)
                elif dep_norm == tid:
                    # Self-dependency is a cycle of length 1
                    cycles.append([tid, tid])
                    error_messages.append(f"Task {tid} cannot depend on itself.")

        visited: Dict[str, int] = {t: 0 for t in adj}  # 0: unvisited, 1: visiting, 2: visited
        path: List[str] = []

        def dfs(node: str):
            visited[node] = 1
            path.append(node)
            for neighbor in adj.get(node, []):
                if visited[neighbor] == 1:
                    # Cycle detected!
                    cycle_start_idx = path.index(neighbor)
                    cycle_path = path[cycle_start_idx:] + [neighbor]
                    cycles.append(cycle_path)
                elif visited[neighbor] == 0:
                    dfs(neighbor)
            path.pop()
            visited[node] = 2

        for t in adj:
            if visited[t] == 0:
                dfs(t)

        for cycle in cycles:
            if len(cycle) > 2:
                error_messages.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        is_valid = len(invalid_refs) == 0 and len(cycles) == 0 and len(error_messages) == 0
        return DependencyValidationResult(
            is_valid=is_valid,
            cycles=cycles,
            invalid_references=invalid_refs,
            error_messages=error_messages,
        )

    @staticmethod
    def get_task_readiness(task: Task, all_tasks: List[Task]) -> TaskReadiness:
        """Determines if a task is ready to be worked on (all prerequisites are Done)."""
        if task.status == TaskStatus.DONE:
            return TaskReadiness(
                task_id=task.id,
                is_ready=False,
                missing_dependencies=[],
                reason="Task is already completed.",
            )

        task_lookup = {t.id.upper(): t for t in all_tasks}
        unresolved: List[str] = []

        for dep_id in task.dependencies:
            dep_norm = dep_id.upper()
            dep_task = task_lookup.get(dep_norm)
            if not dep_task:
                unresolved.append(f"{dep_norm} (missing task)")
            elif dep_task.status != TaskStatus.DONE:
                unresolved.append(f"{dep_norm} ('{dep_task.title}' is {dep_task.status.value})")

        if unresolved:
            return TaskReadiness(
                task_id=task.id,
                is_ready=False,
                missing_dependencies=unresolved,
                reason=f"Waiting for {len(unresolved)} prerequisite(s): {', '.join(unresolved)}",
            )

        return TaskReadiness(
            task_id=task.id,
            is_ready=True,
            missing_dependencies=[],
            reason="All prerequisite dependencies are completed. Ready to execute!",
        )

    @staticmethod
    def get_waiting_analysis(tasks: List[Task]) -> List[Dict[str, object]]:
        """Produces a human-friendly list of waiting tasks and what needs to happen next."""
        analysis: List[Dict[str, object]] = []
        task_lookup = {t.id.upper(): t for t in tasks}

        for task in tasks:
            if task.status in (TaskStatus.DONE,):
                continue

            readiness = DependencyService.get_task_readiness(task, tasks)
            if not readiness.is_ready and readiness.missing_dependencies:
                prereq_owners = []
                for dep_str in task.dependencies:
                    prereq = task_lookup.get(dep_str.upper())
                    if prereq and prereq.status != TaskStatus.DONE:
                        prereq_owners.append(f"{prereq.assigned_to} on [{prereq.id}] {prereq.title}")

                next_step = (
                    f"Team needs to complete: {'; '.join(prereq_owners)}"
                    if prereq_owners
                    else "Resolve prerequisite blockers first."
                )

                analysis.append(
                    {
                        "task_id": task.id,
                        "task_title": task.title,
                        "assigned_to": task.assigned_to,
                        "status": task.status.value,
                        "waiting_on": readiness.missing_dependencies,
                        "what_needs_to_happen": next_step,
                    }
                )

        return analysis

    @staticmethod
    def get_topological_order(tasks: List[Task]) -> List[Task]:
        """Returns tasks ordered topologically by dependencies. Falls back to original if cycle exists."""
        validation = DependencyService.validate_dependencies(tasks)
        if not validation.is_valid:
            # Sort by suggested_order as fallback
            return sorted(tasks, key=lambda t: t.suggested_order)

        task_lookup = {t.id.upper(): t for t in tasks}
        in_degree: Dict[str, int] = {t.id.upper(): 0 for t in tasks}
        graph: Dict[str, List[str]] = {t.id.upper(): [] for t in tasks}

        for task in tasks:
            tid = task.id.upper()
            for dep in task.dependencies:
                dep_norm = dep.upper()
                if dep_norm in graph:
                    graph[dep_norm].append(tid)
                    in_degree[tid] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        # Secondary sort by suggested_order
        queue.sort(key=lambda x: task_lookup[x].suggested_order)
        ordered: List[Task] = []

        while queue:
            curr = queue.pop(0)
            ordered.append(task_lookup[curr])
            for neighbor in graph[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
            queue.sort(key=lambda x: task_lookup[x].suggested_order)

        if len(ordered) == len(tasks):
            return ordered
        return sorted(tasks, key=lambda t: t.suggested_order)
