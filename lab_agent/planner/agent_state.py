"""
Agent state management for LangGraph workflows

Defines the state structure, TaskSpec, and TaskNode formats that flow
through the LangGraph execution graph.
"""

from typing import Dict, List, Any, Optional, Literal, TypedDict
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class RunLevel(str, Enum):
    """Execution safety levels"""
    DRY_RUN = "dry-run"
    SIM = "sim" 
    LIVE = "live"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskSpec(BaseModel):
    """Task specification matching labAgent Framework v1"""
    task_id: str = Field(..., description="Unique task identifier")
    goal: str = Field(..., description="High-level task objective")
    constraints: List[str] = Field(default_factory=list, description="Execution constraints")
    artifacts: List[str] = Field(default_factory=list, description="Required/expected artifacts")
    owner: str = Field(..., description="Task owner/requestor")
    sla: str = Field(default="P1D", description="Service level agreement (ISO 8601)")
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    priority: Priority = Field(default=Priority.NORMAL, description="Task priority")
    runlevel: RunLevel = Field(default=RunLevel.DRY_RUN, description="Execution safety level")
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class TaskNode(BaseModel):
    """Individual task graph node"""
    node_id: str = Field(..., description="Unique node identifier") 
    agent: str = Field(..., description="Agent pod assignment (e.g., worker.cooldown)")
    tools: List[str] = Field(default_factory=list, description="Required MCP tools")
    params: Dict[str, Any] = Field(default_factory=dict, description="Node parameters")
    guards: List[str] = Field(default_factory=list, description="Safety/interlock guards")
    on_success: List[str] = Field(default_factory=list, description="Success continuation nodes")
    on_fail: List[str] = Field(default_factory=list, description="Failure handling nodes")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current node status")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Node execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: Optional[datetime] = Field(default=None, description="Execution start time")
    completed_at: Optional[datetime] = Field(default=None, description="Execution completion time")
    
    class Config:
        use_enum_values = True


class AgentState(TypedDict):
    """LangGraph state that flows through the execution graph"""
    
    # Core task information
    task_spec: TaskSpec
    task_graph: Dict[str, TaskNode]
    current_node: Optional[str]
    
    # Execution state
    status: TaskStatus
    runlevel: RunLevel
    approved: bool
    
    # Memory and context
    memory_namespace: str
    conversation_history: List[Dict[str, Any]]
    artifacts: Dict[str, str]  # artifact_id -> URI
    
    # Monitoring and observability
    execution_log: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    
    # Error handling
    errors: List[str]
    retry_count: int
    max_retries: int
    
    # Inter-agent communication
    messages: List[Dict[str, Any]]
    pending_approvals: List[str]
    
    # Resource management
    resource_locks: List[str]
    budget_consumed: Dict[str, float]  # resource_type -> amount


class WorkflowResult(BaseModel):
    """Final workflow execution result"""
    task_id: str
    status: TaskStatus
    artifacts: Dict[str, str]
    execution_time: float
    nodes_executed: List[str]
    errors: List[str]
    metrics: Dict[str, Any]
    summary: str
    
    class Config:
        use_enum_values = True


class AgentMessage(BaseModel):
    """Inter-agent communication message"""
    msg_id: str = Field(..., description="Unique message identifier")
    type: Literal["task.dispatch", "status.update", "artifact.new", "alert", "approval.request"]
    sender: str = Field(..., description="Sending agent identifier")
    task_id: Optional[str] = Field(default=None, description="Associated task ID")
    namespace: str = Field(..., description="Memory namespace")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    requires_ack: bool = Field(default=False, description="Requires acknowledgment")
    priority: Priority = Field(default=Priority.NORMAL, description="Message priority")
    visibility: Literal["lab", "owner", "pi-only"] = Field(default="lab", description="Message visibility")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class ResourceLock(BaseModel):
    """Resource locking for multi-device coordination"""
    resource_id: str = Field(..., description="Resource identifier (e.g., cryostat_slot_1)")
    locked_by: str = Field(..., description="Task ID that holds the lock")
    lock_type: Literal["exclusive", "shared"] = Field(default="exclusive")
    acquired_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(default=None, description="Auto-release time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional lock metadata")


class SafetyGuard(BaseModel):
    """Safety interlock definition"""
    guard_id: str = Field(..., description="Guard identifier")
    condition: str = Field(..., description="Guard condition expression")
    message: str = Field(..., description="Human-readable description")
    severity: Literal["warning", "error", "critical"] = Field(default="error")
    auto_remediate: bool = Field(default=False, description="Can be automatically resolved")
    remediation_action: Optional[str] = Field(default=None, description="Auto-remediation action")