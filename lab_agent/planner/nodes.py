"""
LangGraph node implementations for different agent pods

Each node class implements the execution logic for specific agent types:
- IntakeNode: Parse user requests into TaskSpecs
- PrecheckNode: Validate resources and constraints
- WorkerNode: Execute instrument/hardware operations
- AssistantNode: Handle administrative operations
- ConsultantNode: Manage knowledge and research tasks
- InfoCenterNode: Generate briefs and summaries
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from .agent_state import (
    AgentState, TaskSpec, TaskNode, TaskStatus, RunLevel,
    Priority, AgentMessage
)
from ..playground.mcp_manager import MCPManager
from ..utils.logger import get_logger
from .llm_planner import LLMTaskPlanner


class BaseNode:
    """Base class for all LangGraph nodes"""
    
    def __init__(self, node_type: str):
        self.node_type = node_type
        self.logger = get_logger(f"{__name__}.{node_type}")
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the node logic - to be implemented by subclasses"""
        raise NotImplementedError
    
    def _log_execution(self, state: AgentState, action: str, details: Dict[str, Any] = None):
        """Log node execution details"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": f"{self.node_type}_action",
            "action": action,
            "details": details or {}
        }
        state["execution_log"].append(log_entry)
        self.logger.info(f"{self.node_type}: {action}")


class IntakeNode(BaseNode):
    """
    Handles task intake and request parsing
    
    Converts user requests into structured TaskSpecs and performs
    initial validation and classification using GPT-4o via LangChain.
    """
    
    def __init__(self):
        super().__init__("intake")
        self.llm_planner = LLMTaskPlanner()
    
    async def execute(self, state: AgentState) -> AgentState:
        """Parse user request and create task graph"""
        
        task_spec = state["task_spec"]
        self._log_execution(state, "parsing_request", {"goal": task_spec.goal})
        
        # Generate task graph from the goal
        task_graph = await self._generate_task_graph(task_spec)
        state["task_graph"] = task_graph
        
        # Set initial node
        if task_graph:
            first_node_id = list(task_graph.keys())[0]
            state["current_node"] = first_node_id
            state["task_graph"][first_node_id].status = TaskStatus.PENDING
        
        # Initialize memory namespace
        state["memory_namespace"] = f"tasks/{task_spec.task_id}"
        
        # Set status
        state["status"] = TaskStatus.RUNNING
        
        self._log_execution(state, "task_graph_created", {
            "nodes_count": len(task_graph),
            "first_node": state.get("current_node")
        })
        
        return state
    
    async def _generate_task_graph(self, task_spec: TaskSpec) -> Dict[str, TaskNode]:
        """Generate task graph from TaskSpec using GPT-4o via LangChain"""
        
        try:
            # Check if LLM planner is available
            if self.llm_planner.is_available():
                self.logger.info("Using LLM-based task decomposition with GPT-4o")
                
                # Use LLM to decompose the task
                task_graph = await self.llm_planner.decompose_task(task_spec)
                
                if task_graph:
                    self.logger.info(f"LLM generated task graph with {len(task_graph)} nodes")
                    return task_graph
                else:
                    self.logger.warning("LLM returned empty task graph, falling back to rule-based")
            
            else:
                self.logger.warning("LLM planner not available, using rule-based fallback")
            
        except Exception as e:
            self.logger.error(f"LLM task decomposition failed: {e}, falling back to rule-based")
        
        # Fallback to simplified rule-based approach
        return self._fallback_rule_based_task_graph(task_spec)
    
    def _fallback_rule_based_task_graph(self, task_spec: TaskSpec) -> Dict[str, TaskNode]:
        """Fallback rule-based task graph generation"""
        
        self.logger.info("Using rule-based fallback for task decomposition")
        
        goal_lower = task_spec.goal.lower()
        
        # Cooldown + measurement workflow
        if "cooldown" in goal_lower and ("gate" in goal_lower or "sweep" in goal_lower):
            cooldown_node = TaskNode(
                node_id="cooldown_setup",
                agent="worker.cooldown",
                tools=["instrMCP.cryostat", "instrMCP.temperature"],
                params={"target_T": "20 mK", "rate": "<=5 mK/min"},
                guards=["interlock.cryostat_ok", "shift=night_ops"],
                on_success=["measurement"],
                on_fail=["notify_owner"]
            )
            
            measurement_node = TaskNode(
                node_id="measurement",
                agent="worker.sweep",
                tools=["instrMCP.sweep", "instrMCP.daq"],
                params={"type": "auto_detect", "range": "auto"},
                guards=["capability: DAC ≤ 50 mV"],
                on_success=["brief_update"],
                on_fail=["retry_measurement"]
            )
            
            brief_node = TaskNode(
                node_id="brief_update",
                agent="info_center.brief",
                tools=["brief.update"],
                params={"type": "completion"},
                on_success=[],
                on_fail=[]
            )
            
            return {
                "cooldown_setup": cooldown_node,
                "measurement": measurement_node,
                "brief_update": brief_node
            }
        
        # Literature research workflow
        elif "arxiv" in goal_lower or "papers" in goal_lower or "literature" in goal_lower:
            search_node = TaskNode(
                node_id="arxiv_search",
                agent="consultant.arxiv",
                tools=["arxiv.search", "paper.score"],
                params={"keywords": "auto_extract", "days": 7},
                on_success=["brief_update"],
                on_fail=["manual_search"]
            )
            
            brief_node = TaskNode(
                node_id="brief_update",
                agent="info_center.brief",
                tools=["brief.update"],
                params={"type": "completion"},
                on_success=[],
                on_fail=[]
            )
            
            return {
                "arxiv_search": search_node,
                "brief_update": brief_node
            }
        
        # Administrative workflow
        elif "receipt" in goal_lower or "expense" in goal_lower or "admin" in goal_lower:
            admin_node = TaskNode(
                node_id="admin_processing",
                agent="assistant.forms",
                tools=["forms.process", "policy.validate"],
                params={"auto_process": True},
                guards=[],
                on_success=["brief_update"],
                on_fail=["manual_review"]
            )
            
            brief_node = TaskNode(
                node_id="brief_update",
                agent="info_center.brief",
                tools=["brief.update"],
                params={"type": "completion"},
                on_success=[],
                on_fail=[]
            )
            
            return {
                "admin_processing": admin_node,
                "brief_update": brief_node
            }
        
        # Generic single-step task
        else:
            generic_node = TaskNode(
                node_id="execute_task",
                agent="worker.generic",
                tools=["generic.execute"],
                params={"goal": task_spec.goal},
                on_success=["brief_update"],
                on_fail=["escalate"]
            )
            
            brief_node = TaskNode(
                node_id="brief_update",
                agent="info_center.brief",
                tools=["brief.update"],
                params={"type": "completion"},
                on_success=[],
                on_fail=[]
            )
            
            return {
                "execute_task": generic_node,
                "brief_update": brief_node
            }


class PrecheckNode(BaseNode):
    """
    Performs pre-execution validation and resource checks
    
    Validates constraints, checks resource availability,
    and ensures prerequisites are met before execution.
    """
    
    def __init__(self):
        super().__init__("precheck")
    
    async def execute(self, state: AgentState) -> AgentState:
        """Perform pre-execution checks"""
        
        self._log_execution(state, "starting_prechecks")
        
        # Check constraints
        constraint_results = await self._check_constraints(state)
        
        # Check resource availability
        resource_results = await self._check_resources(state)
        
        # Check budget/limits
        budget_results = await self._check_budget(state)
        
        # Check time windows
        window_results = await self._check_time_windows(state)
        
        # Aggregate results
        all_checks_passed = all([
            constraint_results["passed"],
            resource_results["passed"], 
            budget_results["passed"],
            window_results["passed"]
        ])
        
        if all_checks_passed:
            state["status"] = TaskStatus.RUNNING
            self._log_execution(state, "prechecks_passed")
        else:
            state["status"] = TaskStatus.FAILED
            failed_checks = []
            if not constraint_results["passed"]:
                failed_checks.extend(constraint_results["errors"])
            if not resource_results["passed"]:
                failed_checks.extend(resource_results["errors"])
            if not budget_results["passed"]:
                failed_checks.extend(budget_results["errors"])
            if not window_results["passed"]:
                failed_checks.extend(window_results["errors"])
            
            state["errors"].extend(failed_checks)
            self._log_execution(state, "prechecks_failed", {"errors": failed_checks})
        
        return state
    
    async def _check_constraints(self, state: AgentState) -> Dict[str, Any]:
        """Check task constraints"""
        
        constraints = state["task_spec"].constraints
        errors = []
        
        for constraint in constraints:
            if constraint.startswith("runlevel:"):
                required_level = constraint.split(":")[1]
                if state["runlevel"] != required_level:
                    errors.append(f"Runlevel mismatch: required {required_level}, got {state['runlevel']}")
            
            elif constraint.startswith("window:"):
                # Time window constraint handled in _check_time_windows
                pass
            
            elif constraint.startswith("max_power="):
                # Power constraint - would check against actual capabilities
                pass
        
        return {"passed": len(errors) == 0, "errors": errors}
    
    async def _check_resources(self, state: AgentState) -> Dict[str, Any]:
        """Check resource availability"""
        
        # Check required tools/instruments
        required_tools = set()
        for node in state["task_graph"].values():
            required_tools.update(node.tools)
        
        errors = []
        
        # In a full implementation, this would check actual resource availability
        # For now, assume all resources are available
        
        return {"passed": len(errors) == 0, "errors": errors}
    
    async def _check_budget(self, state: AgentState) -> Dict[str, Any]:
        """Check budget and usage limits"""
        
        # Check token budget, instrument time, etc.
        errors = []
        
        # Placeholder budget checks
        # In a full implementation, this would check actual budgets
        
        return {"passed": len(errors) == 0, "errors": errors}
    
    async def _check_time_windows(self, state: AgentState) -> Dict[str, Any]:
        """Check time window constraints"""
        
        constraints = state["task_spec"].constraints
        errors = []
        
        for constraint in constraints:
            if constraint.startswith("window:"):
                window = constraint.split(":")[1]
                if not self._is_in_time_window(window):
                    errors.append(f"Outside allowed time window: {window}")
        
        return {"passed": len(errors) == 0, "errors": errors}
    
    def _is_in_time_window(self, window: str) -> bool:
        """Check if current time is within allowed window"""
        
        # Parse window format like "21:00-07:00"
        if "-" in window:
            start_str, end_str = window.split("-")
            start_hour = int(start_str.split(":")[0])
            end_hour = int(end_str.split(":")[0])
            
            current_hour = datetime.now().hour
            
            # Handle overnight windows
            if start_hour > end_hour:
                return current_hour >= start_hour or current_hour <= end_hour
            else:
                return start_hour <= current_hour <= end_hour
        
        return True


class WorkerNode(BaseNode):
    """
    Executes instrument and hardware operations
    
    Handles physical device control, measurements,
    and data acquisition through MCP tools.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        super().__init__("worker")
        self.mcp_manager = mcp_manager
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute worker tasks"""
        
        current_node_id = state.get("current_node")
        if not current_node_id:
            state["errors"].append("No current node specified for worker")
            return state
        
        current_node = state["task_graph"].get(current_node_id)
        if not current_node:
            state["errors"].append(f"Node {current_node_id} not found in task graph")
            return state
        
        self._log_execution(state, "executing_worker_task", {
            "node_id": current_node_id,
            "agent": current_node.agent,
            "tools": current_node.tools
        })
        
        # Update node status
        current_node.status = TaskStatus.RUNNING
        current_node.started_at = datetime.now()
        
        try:
            # Execute the worker task based on agent type
            if current_node.agent.startswith("worker.cooldown"):
                result = await self._execute_cooldown_task(current_node, state)
            elif current_node.agent.startswith("worker.sweep"):
                result = await self._execute_sweep_task(current_node, state)
            elif current_node.agent.startswith("worker.lockin"):
                result = await self._execute_lockin_task(current_node, state)
            else:
                result = await self._execute_generic_worker_task(current_node, state)
            
            # Update node with result
            current_node.result = result
            current_node.status = TaskStatus.COMPLETED
            current_node.completed_at = datetime.now()
            
            # Move to next node
            self._advance_to_next_node(state, current_node.on_success)
            
            self._log_execution(state, "worker_task_completed", {
                "node_id": current_node_id,
                "result_keys": list(result.keys()) if result else []
            })
            
        except Exception as e:
            error_msg = f"Worker task failed: {str(e)}"
            state["errors"].append(error_msg)
            current_node.error = error_msg
            current_node.status = TaskStatus.FAILED
            current_node.completed_at = datetime.now()
            
            # Move to failure handling
            self._advance_to_next_node(state, current_node.on_fail)
            
            self._log_execution(state, "worker_task_failed", {
                "node_id": current_node_id,
                "error": error_msg
            })
        
        return state
    
    async def _execute_cooldown_task(self, node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Execute cryostat cooldown task"""
        
        # Simulate cooldown process
        target_temp = node.params.get("target_T", "20 mK")
        
        # In dry-run mode, just simulate
        if state["runlevel"] == RunLevel.DRY_RUN:
            await asyncio.sleep(0.1)  # Simulate time
            return {
                "final_temperature": target_temp,
                "time_taken": "simulated",
                "status": "completed"
            }
        
        # In real implementation, would call MCP tools
        # For now, simulate the process
        return {
            "final_temperature": target_temp,
            "time_taken": "2.5 hours",
            "status": "completed"
        }
    
    async def _execute_sweep_task(self, node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Execute measurement sweep task"""
        
        sweep_type = node.params.get("type", "1D")
        voltage_range = node.params.get("range", "±10 mV")
        
        # In dry-run mode, just simulate
        if state["runlevel"] == RunLevel.DRY_RUN:
            await asyncio.sleep(0.1)
            return {
                "sweep_type": sweep_type,
                "points_measured": "simulated",
                "data_file": f"sim_sweep_{uuid4().hex[:8]}.h5",
                "status": "completed"
            }
        
        # Simulate measurement
        data_file = f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
        
        return {
            "sweep_type": sweep_type,
            "points_measured": 10000,
            "data_file": data_file,
            "status": "completed"
        }
    
    async def _execute_lockin_task(self, node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Execute lock-in amplifier configuration"""
        
        frequency = node.params.get("frequency", "1 kHz")
        sensitivity = node.params.get("sensitivity", "auto")
        
        return {
            "frequency_set": frequency,
            "sensitivity_set": sensitivity,
            "status": "configured"
        }
    
    async def _execute_generic_worker_task(self, node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Execute generic worker task"""
        
        # Placeholder for generic task execution
        return {
            "task_completed": True,
            "status": "completed"
        }
    
    def _advance_to_next_node(self, state: AgentState, next_node_ids: List[str]):
        """Advance to the next node in the task graph"""
        
        if next_node_ids:
            # For now, just take the first next node
            next_node_id = next_node_ids[0]
            if next_node_id in state["task_graph"]:
                state["current_node"] = next_node_id
                state["task_graph"][next_node_id].status = TaskStatus.PENDING
            else:
                # No more nodes, mark as complete
                state["current_node"] = None
        else:
            # No next nodes, task is complete
            state["current_node"] = None


class AssistantNode(BaseNode):
    """
    Handles administrative operations
    
    Processes receipts, manages emails, handles onboarding/offboarding,
    and other administrative tasks.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        super().__init__("assistant")
        self.mcp_manager = mcp_manager
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute assistant tasks"""
        
        self._log_execution(state, "executing_assistant_tasks")
        
        # Process administrative tasks
        # This would integrate with actual admin systems
        
        self._log_execution(state, "assistant_tasks_completed")
        return state


class ConsultantNode(BaseNode):
    """
    Manages knowledge and research tasks
    
    Handles literature searches, paper analysis, wiki updates,
    and citation management.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        super().__init__("consultant")
        self.mcp_manager = mcp_manager
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute consultant tasks"""
        
        self._log_execution(state, "executing_consultant_tasks")
        
        # This would integrate with the existing ArXiv Daily system
        # and other knowledge management tools
        
        self._log_execution(state, "consultant_tasks_completed")
        return state


class InfoCenterNode(BaseNode):
    """
    Generates briefs and rolling intelligence
    
    Creates daily briefs, status updates, and maintains
    the "state of the experiment" information.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        super().__init__("info_center")
        self.mcp_manager = mcp_manager
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute info center tasks"""
        
        self._log_execution(state, "generating_brief")
        
        # Generate summary and brief
        brief = await self._generate_task_brief(state)
        
        # Store in artifacts
        brief_id = f"brief_{state['task_spec'].task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        state["artifacts"][brief_id] = brief
        
        self._log_execution(state, "brief_generated", {"brief_id": brief_id})
        return state
    
    async def _generate_task_brief(self, state: AgentState) -> str:
        """Generate a brief summary of the task execution"""
        
        task_spec = state["task_spec"]
        
        # Count completed vs failed nodes
        completed_nodes = 0
        failed_nodes = 0
        total_nodes = len(state["task_graph"])
        
        for node in state["task_graph"].values():
            if node.status == TaskStatus.COMPLETED:
                completed_nodes += 1
            elif node.status == TaskStatus.FAILED:
                failed_nodes += 1
        
        # Generate brief
        brief = f"""
# Task Brief: {task_spec.task_id}

## Objective
{task_spec.goal}

## Status
- **Overall**: {state['status']}
- **Nodes Completed**: {completed_nodes}/{total_nodes}
- **Nodes Failed**: {failed_nodes}
- **Execution Time**: {self._calculate_execution_time(state):.1f} seconds

## Artifacts Generated
{len(state['artifacts'])} artifacts created

## Next Actions
{self._suggest_next_actions(state)}
"""
        
        return brief
    
    def _calculate_execution_time(self, state: AgentState) -> float:
        """Calculate execution time from logs"""
        
        if not state["execution_log"]:
            return 0.0
        
        start_time = datetime.fromisoformat(state["execution_log"][0]["timestamp"])
        end_time = datetime.now()
        return (end_time - start_time).total_seconds()
    
    def _suggest_next_actions(self, state: AgentState) -> str:
        """Suggest next actions based on task state"""
        
        if state["status"] == TaskStatus.COMPLETED:
            return "Task completed successfully. No further actions required."
        elif state["status"] == TaskStatus.FAILED:
            return "Task failed. Review errors and consider retry or manual intervention."
        else:
            return "Task in progress. Monitoring ongoing."