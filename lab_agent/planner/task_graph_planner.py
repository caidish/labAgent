"""
Main LangGraph-based task planner for labAgent Framework v1

Implements the core orchestration system that:
- Converts user intents into TaskSpecs
- Expands TaskSpecs into executable TaskGraphs  
- Manages workflow execution with LangGraph
- Handles approvals, retries, and error recovery
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from .agent_state import (
    AgentState, TaskSpec, TaskNode, TaskStatus, RunLevel, 
    Priority, WorkflowResult, AgentMessage, ResourceLock, SafetyGuard
)
from .routing import ConditionalRouter
from .nodes import (
    IntakeNode, PrecheckNode, WorkerNode, 
    AssistantNode, ConsultantNode, InfoCenterNode
)
from ..playground.mcp_manager import MCPManager
from ..utils.logger import get_logger


class TaskGraphPlanner:
    """
    Main LangGraph-based planner that orchestrates agent workflows
    
    Converts high-level requests into TaskSpecs, expands them into 
    executable TaskGraphs, and manages execution through LangGraph.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.logger = get_logger(__name__)
        self.mcp_manager = mcp_manager
        self.router = ConditionalRouter()
        
        # Initialize node implementations
        self.intake_node = IntakeNode()
        self.precheck_node = PrecheckNode()
        self.worker_node = WorkerNode(mcp_manager)
        self.assistant_node = AssistantNode(mcp_manager)
        self.consultant_node = ConsultantNode(mcp_manager)
        self.info_center_node = InfoCenterNode(mcp_manager)
        
        # Resource management
        self.resource_locks: Dict[str, ResourceLock] = {}
        self.safety_guards: Dict[str, SafetyGuard] = {}
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        # Checkpointer for state persistence
        self.checkpointer = MemorySaver()
        
        # Compile the graph
        self.app = self.workflow.compile(checkpointer=self.checkpointer)
        
        self.logger.info("TaskGraphPlanner initialized with LangGraph workflow")
    
    def _build_workflow(self) -> StateGraph:
        """Build the main LangGraph workflow"""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("intake", self._intake_wrapper)
        workflow.add_node("precheck", self._precheck_wrapper)
        workflow.add_node("approval_gate", self._approval_gate_wrapper)
        workflow.add_node("worker", self._worker_wrapper)
        workflow.add_node("assistant", self._assistant_wrapper)
        workflow.add_node("consultant", self._consultant_wrapper)
        workflow.add_node("info_center", self._info_center_wrapper)
        workflow.add_node("error_handler", self._error_handler_wrapper)
        workflow.add_node("finalizer", self._finalizer_wrapper)
        
        # Add edges
        workflow.set_entry_point("intake")
        
        # Main flow
        workflow.add_edge("intake", "precheck")
        workflow.add_edge("precheck", "approval_gate")
        
        # Conditional routing from approval gate
        workflow.add_conditional_edges(
            "approval_gate",
            self.router.route_after_approval,
            {
                "approved": "worker",
                "rejected": "error_handler", 
                "pending": END
            }
        )
        
        # Agent pod routing
        workflow.add_conditional_edges(
            "worker", 
            self.router.route_after_worker,
            {
                "continue": "worker",
                "to_assistant": "assistant",
                "to_consultant": "consultant", 
                "to_info_center": "info_center",
                "complete": "finalizer",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "assistant",
            self.router.route_after_assistant,
            {
                "continue": "assistant",
                "to_worker": "worker",
                "to_info_center": "info_center",
                "complete": "finalizer",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "consultant",
            self.router.route_after_consultant, 
            {
                "continue": "consultant",
                "to_info_center": "info_center",
                "complete": "finalizer",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "info_center",
            self.router.route_after_info_center,
            {
                "complete": "finalizer",
                "error": "error_handler"
            }
        )
        
        # Error handling and retries
        workflow.add_conditional_edges(
            "error_handler",
            self.router.route_after_error,
            {
                "retry": "worker",
                "escalate": "info_center", 
                "abort": "finalizer"
            }
        )
        
        workflow.add_edge("finalizer", END)
        
        return workflow
    
    # Node wrapper methods to integrate with LangGraph
    
    async def _intake_wrapper(self, state: AgentState) -> AgentState:
        """Wrapper for intake node"""
        try:
            result = await self.intake_node.execute(state)
            self._log_node_execution("intake", state, result)
            return result
        except Exception as e:
            return self._handle_node_error("intake", state, e)
    
    async def _precheck_wrapper(self, state: AgentState) -> AgentState:
        """Wrapper for precheck node"""
        try:
            result = await self.precheck_node.execute(state)
            self._log_node_execution("precheck", state, result)
            return result
        except Exception as e:
            return self._handle_node_error("precheck", state, e)
    
    async def _approval_gate_wrapper(self, state: AgentState) -> AgentState:
        """Handle approval gates for runlevel elevation"""
        try:
            # Check if elevation to live mode is needed
            if state["runlevel"] == RunLevel.LIVE and not state.get("approved", False):
                # Request approval for live mode
                approval_msg = AgentMessage(
                    msg_id=f"approval_{uuid4().hex[:8]}",
                    type="approval.request",
                    sender="planner",
                    task_id=state["task_spec"].task_id,
                    namespace=state["memory_namespace"],
                    payload={
                        "reason": "Runlevel elevation to LIVE required",
                        "task_goal": state["task_spec"].goal,
                        "constraints": state["task_spec"].constraints
                    },
                    requires_ack=True,
                    priority=Priority.HIGH
                )
                
                state["messages"].append(approval_msg.dict())
                state["pending_approvals"].append(approval_msg.msg_id)
                
                self.logger.info(f"Requesting approval for task {state['task_spec'].task_id}")
                
                # In real implementation, this would wait for human approval
                # For now, auto-approve dry-run and sim modes
                if state["runlevel"] in [RunLevel.DRY_RUN, RunLevel.SIM]:
                    state["approved"] = True
                    
            else:
                state["approved"] = True
            
            return state
            
        except Exception as e:
            return self._handle_node_error("approval_gate", state, e)
    
    async def _worker_wrapper(self, state: AgentState) -> AgentState:
        """Wrapper for worker node"""
        try:
            result = await self.worker_node.execute(state)
            self._log_node_execution("worker", state, result) 
            return result
        except Exception as e:
            return self._handle_node_error("worker", state, e)
    
    async def _assistant_wrapper(self, state: AgentState) -> AgentState:
        """Wrapper for assistant node"""
        try:
            result = await self.assistant_node.execute(state)
            self._log_node_execution("assistant", state, result)
            return result
        except Exception as e:
            return self._handle_node_error("assistant", state, e)
    
    async def _consultant_wrapper(self, state: AgentState) -> AgentState:
        """Wrapper for consultant node"""
        try:
            result = await self.consultant_node.execute(state)
            self._log_node_execution("consultant", state, result)
            return result
        except Exception as e:
            return self._handle_node_error("consultant", state, e)
    
    async def _info_center_wrapper(self, state: AgentState) -> AgentState:
        """Wrapper for info center node"""
        try:
            result = await self.info_center_node.execute(state)
            self._log_node_execution("info_center", state, result)
            return result
        except Exception as e:
            return self._handle_node_error("info_center", state, e)
    
    async def _error_handler_wrapper(self, state: AgentState) -> AgentState:
        """Handle errors and determine retry strategy"""
        try:
            # Increment retry count
            state["retry_count"] = state.get("retry_count", 0) + 1
            
            # Log error details
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "error_handled",
                "retry_count": state["retry_count"],
                "errors": state["errors"]
            }
            state["execution_log"].append(error_entry)
            
            # Determine if we should retry or abort
            if state["retry_count"] < state.get("max_retries", 3):
                self.logger.warning(f"Retrying task {state['task_spec'].task_id} "
                                  f"(attempt {state['retry_count']})")
                state["status"] = TaskStatus.PENDING
            else:
                self.logger.error(f"Task {state['task_spec'].task_id} failed after "
                                f"{state['retry_count']} retries")
                state["status"] = TaskStatus.FAILED
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
            state["status"] = TaskStatus.FAILED
            return state
    
    async def _finalizer_wrapper(self, state: AgentState) -> AgentState:
        """Finalize workflow execution"""
        try:
            # Release resource locks
            for lock_id in state.get("resource_locks", []):
                self._release_resource_lock(lock_id)
            
            # Mark task as completed
            if state["status"] != TaskStatus.FAILED:
                state["status"] = TaskStatus.COMPLETED
            
            # Generate final summary
            summary_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "workflow_completed",
                "status": state["status"],
                "artifacts_created": len(state.get("artifacts", {})),
                "execution_time": self._calculate_execution_time(state)
            }
            state["execution_log"].append(summary_entry)
            
            self.logger.info(f"Task {state['task_spec'].task_id} finalized with "
                           f"status: {state['status']}")
            
            return state
            
        except Exception as e:
            return self._handle_node_error("finalizer", state, e)
    
    def _handle_node_error(self, node_name: str, state: AgentState, error: Exception) -> AgentState:
        """Handle errors that occur in nodes"""
        error_msg = f"Error in {node_name}: {str(error)}"
        self.logger.error(error_msg)
        
        state["errors"].append(error_msg)
        state["status"] = TaskStatus.FAILED
        
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "node_error",
            "node": node_name,
            "error": error_msg
        }
        state["execution_log"].append(error_entry)
        
        return state
    
    def _log_node_execution(self, node_name: str, input_state: AgentState, output_state: AgentState):
        """Log node execution details"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "node_executed", 
            "node": node_name,
            "status": output_state.get("status"),
            "current_node": output_state.get("current_node")
        }
        output_state["execution_log"].append(log_entry)
    
    def _calculate_execution_time(self, state: AgentState) -> float:
        """Calculate total execution time"""
        if not state["execution_log"]:
            return 0.0
        
        start_time = datetime.fromisoformat(state["execution_log"][0]["timestamp"])
        end_time = datetime.now()
        return (end_time - start_time).total_seconds()
    
    def _acquire_resource_lock(self, resource_id: str, task_id: str) -> bool:
        """Acquire a resource lock"""
        if resource_id in self.resource_locks:
            return False  # Already locked
        
        lock = ResourceLock(
            resource_id=resource_id,
            locked_by=task_id
        )
        self.resource_locks[resource_id] = lock
        return True
    
    def _release_resource_lock(self, resource_id: str):
        """Release a resource lock"""
        if resource_id in self.resource_locks:
            del self.resource_locks[resource_id]
    
    # Public API methods
    
    async def execute_task(self, task_spec: TaskSpec, 
                          config: Optional[RunnableConfig] = None) -> WorkflowResult:
        """Execute a task using the LangGraph workflow"""
        
        # Initialize agent state
        initial_state: AgentState = {
            "task_spec": task_spec,
            "task_graph": {},
            "current_node": None,
            "status": TaskStatus.PENDING,
            "runlevel": task_spec.runlevel,
            "approved": False,
            "memory_namespace": f"tasks/{task_spec.task_id}",
            "conversation_history": [],
            "artifacts": {},
            "execution_log": [],
            "metrics": {},
            "errors": [],
            "retry_count": 0,
            "max_retries": 3,
            "messages": [],
            "pending_approvals": [],
            "resource_locks": [],
            "budget_consumed": {}
        }
        
        self.logger.info(f"Starting task execution: {task_spec.task_id}")
        
        try:
            # Execute the workflow
            final_state = await self.app.ainvoke(
                initial_state,
                config=config or {"configurable": {"thread_id": task_spec.task_id}}
            )
            
            # Convert to result format
            result = WorkflowResult(
                task_id=task_spec.task_id,
                status=final_state["status"],
                artifacts=final_state["artifacts"],
                execution_time=self._calculate_execution_time(final_state),
                nodes_executed=[log["node"] for log in final_state["execution_log"] 
                              if log["type"] == "node_executed"],
                errors=final_state["errors"],
                metrics=final_state["metrics"],
                summary=f"Task {task_spec.task_id} completed with status {final_state['status']}"
            )
            
            self.logger.info(f"Task {task_spec.task_id} completed: {result.status}")
            return result
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            return WorkflowResult(
                task_id=task_spec.task_id,
                status=TaskStatus.FAILED,
                artifacts={},
                execution_time=0.0,
                nodes_executed=[],
                errors=[str(e)],
                metrics={},
                summary=f"Task {task_spec.task_id} failed: {str(e)}"
            )
    
    async def create_task_from_request(self, user_request: str, 
                                     owner: str = "user",
                                     priority: Priority = Priority.NORMAL,
                                     runlevel: RunLevel = RunLevel.DRY_RUN) -> TaskSpec:
        """Create a TaskSpec from a natural language request using GPT-4o via LangChain"""
        
        try:
            # Use the IntakeNode's LLM planner for natural language parsing
            if hasattr(self.intake_node, 'llm_planner') and self.intake_node.llm_planner.is_available():
                self.logger.info("Using LLM-based task creation with GPT-4o")
                
                # Create TaskSpec using LLM parameter extraction
                task_spec = await self.intake_node.llm_planner.create_task_from_request(
                    user_request, owner, priority, runlevel
                )
                
                self.logger.info(f"LLM created TaskSpec {task_spec.task_id} with {len(task_spec.constraints)} constraints")
                return task_spec
            
            else:
                self.logger.warning("LLM planner not available, using basic task creation")
                
        except Exception as e:
            self.logger.error(f"LLM task creation failed: {e}, falling back to basic creation")
        
        # Fallback to basic TaskSpec creation
        task_id = f"tg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:3]}"
        
        task_spec = TaskSpec(
            task_id=task_id,
            goal=user_request,
            owner=owner,
            priority=priority,
            runlevel=runlevel,
            tags=["user_request"]
        )
        
        self.logger.info(f"Created basic TaskSpec {task_id} from user request")
        return task_spec
    
    def get_active_tasks(self) -> List[str]:
        """Get list of currently active task IDs"""
        # In a full implementation, this would query the checkpointer
        return []
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get current status of a task"""
        # In a full implementation, this would query the checkpointer
        return None