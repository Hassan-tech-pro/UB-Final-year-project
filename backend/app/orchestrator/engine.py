import asyncio
import time
import logging
from typing import Any, Callable, Optional
from datetime import datetime, timezone

from .graph import create_agent_graph
from .state import OrchestratorState
from ..core.database import db
from ..models.schemas import WorkflowResponse

logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self):
        self._compiled_graph = create_agent_graph()
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._event_subscribers: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}

    def subscribe(self, workflow_id: str, callback: Callable[[dict[str, Any]], Any]):
        """Subscribes a listener (e.g. WebSocket connection) to workflow events."""
        if workflow_id not in self._event_subscribers:
            self._event_subscribers[workflow_id] = []
        self._event_subscribers[workflow_id].append(callback)

    def unsubscribe(self, workflow_id: str, callback: Callable[[dict[str, Any]], Any]):
        if workflow_id in self._event_subscribers:
            self._event_subscribers[workflow_id] = [
                cb for cb in self._event_subscribers[workflow_id] if cb != callback
            ]

    async def broadcast_event(self, workflow_id: str, event_type: str, data: dict[str, Any]):
        """Dispatches an event to all connected listeners."""
        event_payload = {
            "workflow_id": workflow_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        subscribers = self._event_subscribers.get(workflow_id, [])
        for cb in subscribers:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event_payload)
                else:
                    cb(event_payload)
            except Exception as e:
                logger.warning(f"Error notifying subscriber for workflow {workflow_id}: {e}")

    async def start_workflow(
        self,
        workflow_id: str,
        objective: str,
        uploaded_files: list[str]
    ) -> asyncio.Task:
        """Starts asynchronous execution of the stateful LangGraph workflow."""
        # Create initial record in DB
        db.create_workflow(workflow_id, objective)

        initial_state: OrchestratorState = {
            "workflow_id": workflow_id,
            "objective": objective,
            "uploaded_files": uploaded_files,
            "plan": None,
            "current_task_id": None,
            "task_order": [],
            "completed_task_ids": [],
            "task_results": {},
            "task_statuses": {},
            "task_errors": {},
            "retry_counts": {},
            "verifications": [],
            "artifacts": [],
            "logs": [],
            "status": "PENDING",
            "error": None,
            "start_time": time.time(),
            "duration_seconds": 0.0
        }

        task = asyncio.create_task(self._run_graph_loop(workflow_id, initial_state))
        self._active_tasks[workflow_id] = task
        return task

    async def _run_graph_loop(self, workflow_id: str, initial_state: OrchestratorState):
        """Asynchronously streams steps from the LangGraph agent graph."""
        try:
            await self.broadcast_event(workflow_id, "WORKFLOW_STARTED", {"objective": initial_state["objective"]})

            # Stream execution events
            # We iterate through the compiled LangGraph nodes
            state = initial_state
            async for event in self._compiled_graph.astream(initial_state):
                for node_name, node_output in event.items():
                    # Merge node updates into overall state
                    if isinstance(node_output, dict):
                        state.update(node_output)

                    # Broadcast specific node event to UI
                    if node_name == "plan_node":
                        await self.broadcast_event(workflow_id, "PLAN_GENERATED", {
                            "plan": node_output.get("plan")
                        })
                    elif node_name == "execute_task_node":
                        t_id = state.get("current_task_id")
                        await self.broadcast_event(workflow_id, "TASK_EXECUTED", {
                            "task_id": t_id,
                            "status": state.get("task_statuses", {}).get(t_id),
                            "result": state.get("task_results", {}).get(t_id)
                        })
                    elif node_name == "verify_task_node":
                        t_id = state.get("current_task_id")
                        recent_verif = state.get("verifications", [])[-1] if state.get("verifications") else {}
                        await self.broadcast_event(workflow_id, "TASK_VERIFIED", {
                            "task_id": t_id,
                            "verification": recent_verif,
                            "artifacts": state.get("artifacts", [])
                        })
                    elif node_name == "recover_task_node":
                        t_id = state.get("current_task_id")
                        await self.broadcast_event(workflow_id, "TASK_RETRY", {
                            "task_id": t_id,
                            "plan": state.get("plan"),
                            "retry_count": state.get("retry_counts", {}).get(t_id, 0)
                        })
                    elif node_name == "finalize_node":
                        await self.broadcast_event(workflow_id, "WORKFLOW_COMPLETED", {
                            "status": node_output.get("status"),
                            "duration_seconds": node_output.get("duration_seconds")
                        })

                # Yield control briefly to ensure WebSocket delivery
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            db.update_workflow_status(workflow_id, "CANCELLED")
            db.add_log(workflow_id, "WARNING", "Workflow cancelled by user.")
            await self.broadcast_event(workflow_id, "WORKFLOW_CANCELLED", {})
        except Exception as e:
            logger.error(f"Workflow execution failure: {e}", exc_info=True)
            db.update_workflow_status(workflow_id, "FAILED")
            db.add_log(workflow_id, "ERROR", f"Workflow failed with exception: {str(e)}")
            await self.broadcast_event(workflow_id, "WORKFLOW_FAILED", {"error": str(e)})
        finally:
            self._active_tasks.pop(workflow_id, None)

    def cancel_workflow(self, workflow_id: str) -> bool:
        task = self._active_tasks.get(workflow_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

engine = WorkflowEngine()
