# Lab Agent Planner Module

The planner module implements the core task orchestration system for the Lab Agent Framework, converting natural language requests into executable task workflows using GPT-4o via LangChain.

## Architecture Overview

```
User Request → LLM Parser → TaskSpec → Task Graph → LangGraph Execution
```

### Key Components

1. **LLM Planner** (`llm_planner.py`): GPT-4o integration for natural language processing
2. **Task Graph Planner** (`task_graph_planner.py`): Main LangGraph workflow orchestrator
3. **Agent Nodes** (`nodes.py`): Individual agent pod implementations
4. **State Management** (`agent_state.py`): Typed state definitions
5. **Routing Logic** (`routing.py`): Conditional workflow routing

## LLM Integration

### Natural Language Processing

The planner uses three specialized GPT-4o models:

- **Parameter Extraction**: Extracts lab parameters (temperatures, voltages, devices)
- **Safety Validation**: Assesses risks and safety requirements
- **Task Decomposition**: Generates structured task workflows

### Structured Output

All LLM interactions use Pydantic models for type safety:

```python
class ExtractedParameters(BaseModel):
    temperature: Optional[str] = None
    voltage_range: Optional[str] = None
    device_id: Optional[str] = None
    # ... more parameters

class TaskGraphOutput(BaseModel):
    task_graph: Dict[str, Dict[str, Any]]
    execution_summary: str
    estimated_duration: str
    safety_requirements: List[str]
```

## Agent Pod Architecture

### Worker Agents
- **worker.cooldown**: Cryostat and temperature control
- **worker.sweep**: Measurement sweeps and data acquisition
- **worker.lockin**: Lock-in amplifier configuration
- **worker.microscope**: Imaging and optical measurements

### Assistant Agents
- **assistant.storage**: File management and data upload
- **assistant.forms**: Administrative forms and documentation
- **assistant.ocr**: Document processing and receipt parsing
- **assistant.policy**: Policy validation and approval workflows

### Consultant Agents
- **consultant.arxiv**: Literature search and analysis
- **consultant.wiki**: Knowledge base updates
- **consultant.summarize**: Content analysis and summarization

### Information Center
- **info_center.brief**: Status reporting and summaries
- **info_center.notify**: Communications and alerts

## Workflow Execution

### LangGraph Integration

The planner uses LangGraph for workflow orchestration:

```python
workflow = StateGraph(AgentState)

# Add agent nodes
workflow.add_node("intake", intake_wrapper)
workflow.add_node("precheck", precheck_wrapper)
workflow.add_node("worker", worker_wrapper)
# ... more nodes

# Add conditional routing
workflow.add_conditional_edges(
    "worker",
    route_after_worker,
    {
        "continue": "worker",
        "to_assistant": "assistant",
        "complete": "finalizer"
    }
)
```

### State Management

The agent state tracks execution progress:

```python
AgentState = TypedDict("AgentState", {
    "task_spec": TaskSpec,
    "task_graph": Dict[str, TaskNode],
    "current_node": Optional[str],
    "status": TaskStatus,
    "artifacts": Dict[str, Any],
    "execution_log": List[Dict[str, Any]],
    # ... more fields
})
```

## Safety and Validation

### Multi-Layer Safety

1. **LLM Safety Validation**: GPT-4o assesses risks and requirements
2. **Constraint Checking**: Validates parameters against safety limits
3. **Guard Conditions**: Runtime safety checks during execution
4. **Human Approval**: Required for live operations

### Example Safety Guards

```python
guards = [
    "interlock.cryostat_ok",
    "capability: DAC ≤ 50 mV",
    "shift=night_ops",
    "collision_detection"
]
```

## Configuration

The planner loads configuration from `config/planner/`:

```python
config = LLMPlannerConfig()
models = config.get_model_config("task_decomposition")
prompts = config.get_prompt("parameter_extraction")
templates = config.get_few_shot_examples()
```

See `config/planner/README.md` for detailed configuration documentation.

## Usage Examples

### Basic Task Execution

```python
from lab_agent.planner import TaskGraphPlanner
from lab_agent.playground.mcp_manager import MCPManager

# Initialize planner
mcp_manager = MCPManager()
planner = TaskGraphPlanner(mcp_manager)

# Create task from natural language
task_spec = await planner.create_task_from_request(
    "Cool down device D14 to 20 mK and run a gate sweep",
    runlevel=RunLevel.DRY_RUN
)

# Execute the task
result = await planner.execute_task(task_spec)
print(f"Task completed with status: {result.status}")
```

### Advanced Workflow

```python
# Literature research workflow
task_spec = await planner.create_task_from_request(
    "Find recent papers about topological insulators and update the wiki",
    priority=Priority.NORMAL
)

# Execute with custom configuration
config = {"configurable": {"thread_id": task_spec.task_id}}
result = await planner.execute_task(task_spec, config)

# Access artifacts
for artifact_id, content in result.artifacts.items():
    print(f"Generated artifact: {artifact_id}")
```

## Error Handling and Retries

### Automatic Fallbacks

1. **LLM Failure**: Falls back to rule-based task generation
2. **Tool Failure**: Attempts retries with exponential backoff
3. **Validation Errors**: Uses error correction prompts

### Error Recovery

```python
# Retry configuration
max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        result = await execute_node(state)
        break
    except Exception as e:
        retry_count += 1
        if retry_count >= max_retries:
            escalate_to_human(e)
```

## Integration Points

### MCP Server Integration

The planner integrates with MCP servers for tool execution:

```python
# Tool execution through MCP
result = await mcp_manager.call_tool(
    server_name="arxiv",
    tool_name="search_papers",
    arguments={"keywords": keywords, "days": 7}
)
```

### FastMCP Integration

Real-time communication through FastMCP:

```python
# Status updates
await fastmcp_client.notify(
    "task.status_update",
    {
        "task_id": task_id,
        "status": "running",
        "progress": 0.5
    }
)
```

## Monitoring and Observability

### Execution Logging

All workflow steps are logged with structured data:

```python
log_entry = {
    "timestamp": datetime.now().isoformat(),
    "type": "node_executed",
    "node": "worker",
    "status": "completed",
    "artifacts_created": 3
}
```

### Metrics Collection

- Token usage and costs
- Execution time per node
- Success/failure rates
- Resource utilization

### Performance Monitoring

```python
# Track execution metrics
metrics = {
    "llm_calls": 5,
    "tokens_used": 2500,
    "execution_time": 45.2,
    "nodes_executed": ["intake", "precheck", "worker"],
    "artifacts_created": 3
}
```

## Development and Testing

### Adding New Agent Types

1. Define agent in `nodes.py`
2. Add routing logic in `routing.py`
3. Update workflow in `task_graph_planner.py`
4. Add templates in `config/planner/task_templates.json`

### Testing Workflows

```python
# Test in dry-run mode
task_spec = TaskSpec(
    task_id="test_001",
    goal="Test workflow",
    runlevel=RunLevel.DRY_RUN
)

result = await planner.execute_task(task_spec)
assert result.status == TaskStatus.COMPLETED
```

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger("lab_agent.planner").setLevel(logging.DEBUG)
```

## Performance Considerations

### Optimization Strategies

1. **Response Caching**: Cache LLM responses for similar requests
2. **Parallel Execution**: Run independent tasks concurrently
3. **Resource Pooling**: Share resources across tasks
4. **Token Budget Management**: Monitor and limit LLM usage

### Scaling

- **Horizontal**: Multiple planner instances
- **Vertical**: Increase resource limits
- **Hybrid**: Combine LLM and rule-based approaches

## Security and Compliance

### Access Control

- Task execution requires appropriate permissions
- Resource locks prevent conflicts
- Audit trails for all operations

### Data Protection

- Sensitive parameters encrypted at rest
- Secure communication with MCP servers
- PII handling compliance

## Future Enhancements

### Planned Features

1. **Multi-Modal Input**: Support for images and documents
2. **Adaptive Learning**: Improve performance based on feedback
3. **Advanced Scheduling**: Time-based task scheduling
4. **Resource Optimization**: Intelligent resource allocation

### Extension Points

- Custom agent types
- Additional LLM providers
- Advanced routing algorithms
- External system integrations

---

For configuration details, see `config/planner/README.md`.
For API documentation, see the individual module docstrings.