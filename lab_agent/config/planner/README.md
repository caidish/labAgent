# Lab Agent Planner Configuration

This directory contains configuration files for the LLM-based task planner that uses GPT-4o via LangChain to convert natural language requests into structured task workflows.

## Configuration Files

### `llm_config.json`
Model configurations and LangChain settings for different use cases:

- **`models`**: Model configurations for specific tasks
  - `task_decomposition`: Primary model for converting natural language to task graphs
  - `parameter_extraction`: Model for extracting specific parameters (temperatures, voltages, etc.)
  - `safety_validation`: Model for validating safety constraints and identifying risks

- **`langchain_settings`**: LangChain-specific configuration
  - API settings, timeouts, retries
  - Callbacks for monitoring and cost tracking

- **`structured_output`**: Settings for Pydantic-based structured output parsing
- **`safety_controls`**: Safety measures and human approval requirements
- **`monitoring`**: Logging and tracking configuration
- **`cache_settings`**: Response caching for efficiency

### `prompts.json`
System prompts and instructions for different LLM tasks:

- **`system_prompts`**: Core prompts for each model type
  - `task_decomposition`: Main prompt for generating task workflows
  - `parameter_extraction`: Prompt for extracting specific lab parameters
  - `safety_validation`: Prompt for safety risk assessment

- **`few_shot_examples`**: Example input/output pairs for better performance
  - `cooldown_and_measurement`: Example of experimental workflow
  - `literature_search`: Example of research workflow

- **`validation_prompts`**: Prompts for validating generated outputs
- **`error_handling_prompts`**: Prompts for fixing invalid outputs

### `task_templates.json`
Workflow templates and parameter extraction patterns:

- **`workflow_templates`**: Pre-defined workflow patterns
  - `experimental_measurement`: Lab measurement workflows
  - `literature_research`: Research and analysis workflows
  - `administrative_processing`: Admin and document workflows
  - `imaging_workflow`: Microscope and imaging workflows

- **`parameter_extraction_patterns`**: Regex patterns for extracting values
  - Temperature, voltage, time, device ID patterns
  - Unit conversion specifications

- **`safety_constraint_templates`**: Safety limits and constraints
- **`common_tool_combinations`**: Frequently used tool combinations
- **`validation_rules`**: Rules for validating generated task graphs

## Usage

The planner automatically loads these configurations when initializing:

```python
from lab_agent.planner.llm_planner import LLMTaskPlanner

# Initialize with default config
planner = LLMTaskPlanner()

# Or with custom config path
planner = LLMTaskPlanner(config_path="/path/to/config")
```

## Environment Setup

Ensure you have the required environment variables:

```bash
export OPENAI_API_KEY="your_openai_api_key"
```

## Model Selection

The planner uses different GPT-4o configurations optimized for each task:

- **Task Decomposition**: `temperature=0.2` for consistent structure
- **Parameter Extraction**: `temperature=0.1` for precise extraction
- **Safety Validation**: `temperature=0.0` for conservative assessment

## Safety Features

- **Content Filtering**: Enabled by default
- **Human Approval**: Required for live operations and high-cost tasks
- **Fallback System**: Automatic fallback to rule-based system on LLM failure
- **Validation**: Multiple validation layers for generated outputs

## Monitoring and Costs

The planner includes comprehensive monitoring:

- Token usage tracking
- Response latency monitoring
- Cost alerts for high usage
- Structured logging of all LLM interactions

## Customization

### Adding New Workflow Templates

Add to `task_templates.json` under `workflow_templates`:

```json
{
  "your_workflow_name": {
    "description": "Description of the workflow",
    "trigger_keywords": ["keyword1", "keyword2"],
    "template": {
      "nodes": [
        {
          "type": "node_type",
          "agent": "agent.type",
          "tools": ["tool1", "tool2"],
          "typical_params": ["param1", "param2"],
          "safety_guards": ["guard1"]
        }
      ]
    }
  }
}
```

### Adding New Parameter Patterns

Add to `task_templates.json` under `parameter_extraction_patterns`:

```json
{
  "your_parameter": {
    "patterns": ["regex_pattern1", "regex_pattern2"],
    "units": ["unit1", "unit2"],
    "conversion_to_si": {
      "unit1": 1.0,
      "unit2": 0.001
    }
  }
}
```

### Modifying Prompts

Edit prompts in `prompts.json` under appropriate sections. The planner uses Pydantic for structured output, so ensure prompts align with the expected output models.

## Troubleshooting

### LLM Not Available
- Check `OPENAI_API_KEY` environment variable
- Verify network connectivity
- Check OpenAI API limits and billing

### Invalid Output
- Review prompt engineering in `prompts.json`
- Check Pydantic model definitions in `llm_planner.py`
- Enable validation retries in `llm_config.json`

### Safety Violations
- Review safety prompts in `prompts.json`
- Check safety constraint templates in `task_templates.json`
- Verify guard conditions in generated workflows

## Performance Optimization

### Caching
Response caching is enabled by default with 1-hour TTL. Adjust in `llm_config.json`:

```json
{
  "cache_settings": {
    "enable_response_cache": true,
    "cache_ttl_seconds": 3600,
    "cache_key_fields": ["goal", "constraints", "runlevel"]
  }
}
```

### Token Budget
Set daily token budgets in `llm_config.json`:

```json
{
  "models": {
    "task_decomposition": {
      "cost_limits": {
        "daily_token_budget": 100000
      }
    }
  }
}
```

## Integration

The LLM planner integrates with:

- **LangGraph**: For workflow orchestration
- **MCP Servers**: For tool execution
- **FastMCP**: For real-time communication
- **Agent Pods**: For distributed execution

See `lab_agent/planner/README.md` for integration details.