"""
LangChain-based LLM integration for intelligent task planning

This module replaces rule-based task decomposition with GPT-4o using
LangChain's structured output capabilities for robust planning.
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, ValidationError

from .agent_state import TaskSpec, TaskNode, RunLevel, Priority
from ..utils.logger import get_logger


class ExtractedParameters(BaseModel):
    """Structured output for parameter extraction"""
    temperature: Optional[str] = Field(None, description="Target temperature with units")
    voltage_range: Optional[str] = Field(None, description="Voltage range or limit")
    device_id: Optional[str] = Field(None, description="Device identifier (e.g., D14)")
    time_window: Optional[str] = Field(None, description="Time constraint for operation")
    measurement_type: Optional[str] = Field(None, description="Type of measurement")
    duration: Optional[str] = Field(None, description="Expected duration")
    safety_level: Optional[str] = Field(None, description="Required safety level")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Other extracted parameters")


class TaskGraphOutput(BaseModel):
    """Structured output for task graph generation"""
    task_graph: Dict[str, Dict[str, Any]] = Field(..., description="Complete task graph with nodes")
    execution_summary: str = Field(..., description="High-level summary of the workflow")
    estimated_duration: str = Field(..., description="Estimated total execution time")
    safety_requirements: List[str] = Field(default_factory=list, description="Safety requirements and constraints")
    required_approvals: List[str] = Field(default_factory=list, description="Required human approvals")


class SafetyValidation(BaseModel):
    """Structured output for safety validation"""
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, CRITICAL")
    safety_issues: List[str] = Field(default_factory=list, description="Identified safety concerns")
    required_guards: List[str] = Field(default_factory=list, description="Required safety guards")
    blocking_issues: List[str] = Field(default_factory=list, description="Issues that prevent execution")
    recommendations: List[str] = Field(default_factory=list, description="Safety recommendations")


class LLMPlannerConfig:
    """Configuration manager for LLM planner"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if config_path is None:
            # Default to config/planner directory
            current_dir = Path(__file__).parent.parent
            config_path = current_dir / "config" / "planner"
        
        self.config_path = Path(config_path)
        self.llm_config = self._load_config("llm_config.json")
        self.prompts = self._load_config("prompts.json")
        self.templates = self._load_config("task_templates.json")
    
    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        file_path = self.config_path / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            return {}
    
    def get_model_config(self, model_type: str = "task_decomposition") -> Dict[str, Any]:
        """Get model configuration for specific use case"""
        return self.llm_config.get("models", {}).get(model_type, {})
    
    def get_prompt(self, prompt_type: str) -> str:
        """Get prompt template for specific use case"""
        return self.prompts.get("system_prompts", {}).get(prompt_type, {}).get("prompt", "")
    
    def get_few_shot_examples(self) -> Dict[str, Any]:
        """Get few-shot examples for prompting"""
        return self.prompts.get("few_shot_examples", {})


class LLMTaskPlanner:
    """
    LangChain-based task planner using GPT-4o for intelligent workflow generation
    
    Replaces rule-based keyword matching with AI-powered natural language understanding
    and structured task decomposition.
    """
    
    def __init__(self, config: Optional[LLMPlannerConfig] = None):
        self.logger = get_logger(__name__)
        self.config = config or LLMPlannerConfig()
        
        # Initialize LangChain models
        self._init_models()
        
        # Set up output parsers
        self.param_parser = PydanticOutputParser(pydantic_object=ExtractedParameters)
        self.task_graph_parser = PydanticOutputParser(pydantic_object=TaskGraphOutput) 
        self.safety_parser = PydanticOutputParser(pydantic_object=SafetyValidation)
        
        # Cache for LLM responses
        self._response_cache = {}
        
        self.logger.info("LLMTaskPlanner initialized with GPT-4o")
    
    def _init_models(self):
        """Initialize LangChain ChatOpenAI models"""
        
        # Task decomposition model
        task_config = self.config.get_model_config("task_decomposition")
        self.task_model = ChatOpenAI(
            model=task_config.get("name", "gpt-4o"),
            temperature=task_config.get("settings", {}).get("temperature", 0.2),
            max_tokens=task_config.get("settings", {}).get("max_tokens", 2000),
            top_p=task_config.get("settings", {}).get("top_p", 1.0),
            timeout=self.config.llm_config.get("langchain_settings", {}).get("request_timeout", 60)
        )
        
        # Parameter extraction model
        param_config = self.config.get_model_config("parameter_extraction")
        self.param_model = ChatOpenAI(
            model=param_config.get("name", "gpt-4o"),
            temperature=param_config.get("settings", {}).get("temperature", 0.1),
            max_tokens=param_config.get("settings", {}).get("max_tokens", 500)
        )
        
        # Safety validation model
        safety_config = self.config.get_model_config("safety_validation")
        self.safety_model = ChatOpenAI(
            model=safety_config.get("name", "gpt-4o"),
            temperature=safety_config.get("settings", {}).get("temperature", 0.0),
            max_tokens=safety_config.get("settings", {}).get("max_tokens", 300)
        )
    
    async def extract_parameters(self, user_request: str) -> ExtractedParameters:
        """Extract structured parameters from natural language request"""
        
        try:
            prompt = self.config.get_prompt("parameter_extraction")
            
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Extract parameters from: {user_request}")
            ]
            
            # Add format instructions
            format_instructions = self.param_parser.get_format_instructions()
            messages.append(HumanMessage(content=f"Format your response as: {format_instructions}"))
            
            response = await self.param_model.ainvoke(messages)
            
            # Parse structured output
            extracted = self.param_parser.parse(response.content)
            
            self.logger.info(f"Extracted parameters: {extracted.model_dump()}")
            return extracted
            
        except Exception as e:
            self.logger.error(f"Parameter extraction failed: {e}")
            # Return empty parameters on failure
            return ExtractedParameters()
    
    async def validate_safety(self, user_request: str, extracted_params: ExtractedParameters) -> SafetyValidation:
        """Validate safety requirements for the proposed operation"""
        
        try:
            prompt = self.config.get_prompt("safety_validation")
            
            param_summary = json.dumps(extracted_params.model_dump(), indent=2)
            
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"""
                Operation: {user_request}
                
                Extracted Parameters:
                {param_summary}
                
                Evaluate safety risks and requirements.
                """)
            ]
            
            # Add format instructions
            format_instructions = self.safety_parser.get_format_instructions()
            messages.append(HumanMessage(content=f"Format your response as: {format_instructions}"))
            
            response = await self.safety_model.ainvoke(messages)
            
            # Parse structured output
            safety_validation = self.safety_parser.parse(response.content)
            
            self.logger.info(f"Safety validation: {safety_validation.risk_level}")
            return safety_validation
            
        except Exception as e:
            self.logger.error(f"Safety validation failed: {e}")
            # Return conservative safety assessment
            return SafetyValidation(
                risk_level="HIGH",
                safety_issues=["Safety validation failed"],
                blocking_issues=["Unable to assess safety - requires manual review"]
            )
    
    async def generate_task_graph(self, user_request: str, extracted_params: ExtractedParameters, 
                                safety_validation: SafetyValidation) -> Dict[str, TaskNode]:
        """Generate structured task graph using GPT-4o"""
        
        try:
            # Get the main decomposition prompt
            prompt = self.config.get_prompt("task_decomposition")
            
            # Add few-shot examples
            few_shot_examples = self.config.get_few_shot_examples()
            examples_text = ""
            for name, example in few_shot_examples.items():
                examples_text += f"\nExample - {name}:\nInput: {example['input']}\nOutput: {json.dumps(example['output'], indent=2)}\n"
            
            # Build context
            param_summary = json.dumps(extracted_params.model_dump(), indent=2)
            safety_summary = json.dumps(safety_validation.model_dump(), indent=2)
            
            messages = [
                SystemMessage(content=f"{prompt}\n\nFew-shot examples:{examples_text}"),
                HumanMessage(content=f"""
                User Request: {user_request}
                
                Extracted Parameters:
                {param_summary}
                
                Safety Assessment:
                {safety_summary}
                
                Generate a complete task graph that safely accomplishes this request.
                Consider the safety requirements and extracted parameters.
                """)
            ]
            
            # Add format instructions
            format_instructions = self.task_graph_parser.get_format_instructions()
            messages.append(HumanMessage(content=f"Format your response as: {format_instructions}"))
            
            response = await self.task_model.ainvoke(messages)
            
            # Parse structured output
            task_graph_output = self.task_graph_parser.parse(response.content)
            
            # Convert to TaskNode objects
            task_nodes = {}
            for node_id, node_data in task_graph_output.task_graph.items():
                try:
                    task_node = TaskNode(
                        node_id=node_id,
                        agent=node_data.get("agent", "worker.generic"),
                        tools=node_data.get("tools", []),
                        params=node_data.get("params", {}),
                        guards=node_data.get("guards", []),
                        on_success=node_data.get("on_success", []),
                        on_fail=node_data.get("on_fail", [])
                    )
                    task_nodes[node_id] = task_node
                    
                except ValidationError as e:
                    self.logger.error(f"Invalid TaskNode {node_id}: {e}")
                    continue
            
            self.logger.info(f"Generated task graph with {len(task_nodes)} nodes")
            return task_nodes
            
        except Exception as e:
            self.logger.error(f"Task graph generation failed: {e}")
            return self._fallback_task_graph(user_request)
    
    def _fallback_task_graph(self, user_request: str) -> Dict[str, TaskNode]:
        """Fallback to simple rule-based task graph on LLM failure"""
        
        self.logger.warning("Falling back to rule-based task generation")
        
        # Simple generic task
        generic_node = TaskNode(
            node_id="execute_task",
            agent="worker.generic",
            tools=["generic.execute"],
            params={"goal": user_request},
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
    
    async def create_task_from_request(self, user_request: str, owner: str = "user",
                                     priority: Priority = Priority.NORMAL,
                                     runlevel: RunLevel = RunLevel.DRY_RUN) -> TaskSpec:
        """Create TaskSpec from natural language using LLM parameter extraction"""
        
        # Extract parameters
        extracted_params = await self.extract_parameters(user_request)
        
        # Determine constraints from extracted parameters
        constraints = []
        if extracted_params.voltage_range:
            constraints.append(f"max_voltage={extracted_params.voltage_range}")
        if extracted_params.time_window:
            constraints.append(f"window:{extracted_params.time_window}")
        if runlevel == RunLevel.LIVE:
            constraints.append("runlevel:live")
        
        # Generate tags from extracted information
        tags = ["llm_generated"]
        if extracted_params.measurement_type:
            tags.append(extracted_params.measurement_type.lower())
        if extracted_params.device_id:
            tags.append(extracted_params.device_id.lower())
        
        # Create TaskSpec
        task_id = f"tg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(2).hex()}"
        
        task_spec = TaskSpec(
            task_id=task_id,
            goal=user_request,
            constraints=constraints,
            owner=owner,
            priority=priority,
            runlevel=runlevel,
            tags=tags
        )
        
        self.logger.info(f"Created TaskSpec {task_id} from LLM analysis")
        return task_spec
    
    async def decompose_task(self, task_spec: TaskSpec) -> Dict[str, TaskNode]:
        """Decompose TaskSpec into executable TaskGraph using LLM"""
        
        # Extract parameters from the goal
        extracted_params = await self.extract_parameters(task_spec.goal)
        
        # Validate safety
        safety_validation = await self.validate_safety(task_spec.goal, extracted_params)
        
        # Check for blocking safety issues
        if safety_validation.blocking_issues:
            self.logger.error(f"Blocking safety issues: {safety_validation.blocking_issues}")
            # Could raise an exception or return an error task
        
        # Generate task graph
        task_graph = await self.generate_task_graph(task_spec.goal, extracted_params, safety_validation)
        
        return task_graph
    
    def is_available(self) -> bool:
        """Check if LLM planner is available and configured"""
        try:
            # Check if we have required configuration
            if not self.config.llm_config:
                return False
            
            # Check if OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.warning("OpenAI API key not found")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"LLM availability check failed: {e}")
            return False