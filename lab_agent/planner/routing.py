"""
Conditional routing logic for LangGraph workflows

Implements the decision logic that determines how to route between
different agent pods based on task state, results, and conditions.
"""

from typing import Dict, Any, Literal
from .agent_state import AgentState, TaskStatus, RunLevel, TaskNode


class ConditionalRouter:
    """
    Handles conditional routing decisions in the LangGraph workflow
    
    Each routing method examines the current state and determines
    the next node to execute based on conditions, results, and task requirements.
    """
    
    def route_after_approval(self, state: AgentState) -> Literal["approved", "rejected", "pending"]:
        """Route after approval gate"""
        
        # Check if approval is still pending
        if state.get("pending_approvals") and not state.get("approved", False):
            return "pending"
        
        # Check if approved
        if state.get("approved", False):
            return "approved"
        
        # Default to rejected
        return "rejected"
    
    def route_after_worker(self, state: AgentState) -> Literal[
        "continue", "to_assistant", "to_consultant", "to_info_center", "complete", "error"
    ]:
        """Route after worker node execution"""
        
        # Check for errors
        if state["status"] == TaskStatus.FAILED or state.get("errors"):
            return "error"
        
        # Check if current node has more work
        current_node_id = state.get("current_node")
        if current_node_id:
            current_node = state["task_graph"].get(current_node_id)
            if current_node and current_node.status == TaskStatus.RUNNING:
                return "continue"
        
        # Determine next action based on task graph
        next_action = self._determine_next_action(state)
        
        if next_action == "assistant":
            return "to_assistant"
        elif next_action == "consultant": 
            return "to_consultant"
        elif next_action == "info_center":
            return "to_info_center"
        elif next_action == "complete":
            return "complete"
        else:
            return "continue"
    
    def route_after_assistant(self, state: AgentState) -> Literal[
        "continue", "to_worker", "to_info_center", "complete", "error"
    ]:
        """Route after assistant node execution"""
        
        # Check for errors
        if state["status"] == TaskStatus.FAILED or state.get("errors"):
            return "error"
        
        # Check if more assistant work is needed
        if self._has_pending_admin_tasks(state):
            return "continue"
        
        # Determine next action
        next_action = self._determine_next_action(state)
        
        if next_action == "worker":
            return "to_worker"
        elif next_action == "info_center":
            return "to_info_center"
        elif next_action == "complete":
            return "complete"
        else:
            return "complete"
    
    def route_after_consultant(self, state: AgentState) -> Literal[
        "continue", "to_info_center", "complete", "error"
    ]:
        """Route after consultant node execution"""
        
        # Check for errors
        if state["status"] == TaskStatus.FAILED or state.get("errors"):
            return "error"
        
        # Check if more consultant work is needed
        if self._has_pending_knowledge_tasks(state):
            return "continue"
        
        # Usually flows to info center for briefing
        return "to_info_center"
    
    def route_after_info_center(self, state: AgentState) -> Literal["complete", "error"]:
        """Route after info center node execution"""
        
        # Check for errors
        if state["status"] == TaskStatus.FAILED or state.get("errors"):
            return "error"
        
        # Info center is typically the final step
        return "complete"
    
    def route_after_error(self, state: AgentState) -> Literal["retry", "escalate", "abort"]:
        """Route after error handling"""
        
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        # Check if we should retry
        if retry_count < max_retries:
            # Determine if error is retryable
            if self._is_retryable_error(state):
                return "retry"
        
        # Check if we should escalate to human
        if self._should_escalate(state):
            return "escalate"
        
        # Default to abort
        return "abort"
    
    def _determine_next_action(self, state: AgentState) -> str:
        """Determine the next action based on task graph and current state"""
        
        current_node_id = state.get("current_node")
        if not current_node_id:
            return "complete"
        
        current_node = state["task_graph"].get(current_node_id)
        if not current_node:
            return "complete"
        
        # Check if current node is completed successfully
        if current_node.status == TaskStatus.COMPLETED:
            # Look for next nodes to execute
            next_nodes = current_node.on_success
            if next_nodes:
                # Find the next appropriate agent type
                for next_node_id in next_nodes:
                    next_node = state["task_graph"].get(next_node_id)
                    if next_node:
                        agent_type = next_node.agent.split('.')[0]  # e.g., "worker" from "worker.cooldown"
                        return agent_type
        
        return "complete"
    
    def _has_pending_admin_tasks(self, state: AgentState) -> bool:
        """Check if there are pending administrative tasks"""
        
        # Look for unprocessed receipts, emails, etc.
        for node in state["task_graph"].values():
            if (node.agent.startswith("assistant.") and 
                node.status in [TaskStatus.PENDING, TaskStatus.RUNNING]):
                return True
        
        return False
    
    def _has_pending_knowledge_tasks(self, state: AgentState) -> bool:
        """Check if there are pending knowledge/research tasks"""
        
        # Look for unprocessed papers, wiki updates, etc.
        for node in state["task_graph"].values():
            if (node.agent.startswith("consultant.") and 
                node.status in [TaskStatus.PENDING, TaskStatus.RUNNING]):
                return True
        
        return False
    
    def _is_retryable_error(self, state: AgentState) -> bool:
        """Determine if the error is retryable"""
        
        # Check error types
        errors = state.get("errors", [])
        
        # Non-retryable errors
        non_retryable_keywords = [
            "permission denied",
            "unauthorized", 
            "invalid credentials",
            "syntax error",
            "malformed request"
        ]
        
        for error in errors:
            error_lower = error.lower()
            if any(keyword in error_lower for keyword in non_retryable_keywords):
                return False
        
        # Retryable errors (network, timeouts, etc.)
        retryable_keywords = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "rate limit",
            "server error"
        ]
        
        for error in errors:
            error_lower = error.lower()
            if any(keyword in error_lower for keyword in retryable_keywords):
                return True
        
        # Default to retryable for unknown errors
        return True
    
    def _should_escalate(self, state: AgentState) -> bool:
        """Determine if error should be escalated to human"""
        
        # Always escalate if max retries exceeded
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count >= max_retries:
            return True
        
        # Escalate for critical safety violations
        errors = state.get("errors", [])
        critical_keywords = [
            "safety",
            "interlock",
            "emergency",
            "critical",
            "hardware damage"
        ]
        
        for error in errors:
            error_lower = error.lower()
            if any(keyword in error_lower for keyword in critical_keywords):
                return True
        
        # Escalate for live mode failures
        if state.get("runlevel") == RunLevel.LIVE:
            return True
        
        return False
    
    def _check_resource_conflicts(self, state: AgentState) -> bool:
        """Check for resource conflicts that need resolution"""
        
        # This would check against actual resource locks
        # For now, return False (no conflicts)
        return False
    
    def _evaluate_safety_guards(self, state: AgentState) -> bool:
        """Evaluate safety guards and interlocks"""
        
        current_node_id = state.get("current_node")
        if not current_node_id:
            return True
        
        current_node = state["task_graph"].get(current_node_id)
        if not current_node:
            return True
        
        # Check all guards for the current node
        for guard_condition in current_node.guards:
            if not self._evaluate_guard_condition(guard_condition, state):
                state["errors"].append(f"Safety guard failed: {guard_condition}")
                return False
        
        return True
    
    def _evaluate_guard_condition(self, condition: str, state: AgentState) -> bool:
        """Evaluate a specific guard condition"""
        
        # Simple condition evaluation
        # In a full implementation, this would be more sophisticated
        
        if condition == "interlock.cryostat_ok":
            # Check cryostat status
            return True  # Assume OK for now
        
        elif condition.startswith("shift="):
            # Check time window
            shift_type = condition.split("=")[1]
            if shift_type == "night_ops":
                # Check if current time is in night operations window
                from datetime import datetime
                current_hour = datetime.now().hour
                return 21 <= current_hour or current_hour <= 7
        
        elif condition.startswith("capability:"):
            # Check capability constraints
            return True  # Assume OK for now
        
        # Default to pass
        return True