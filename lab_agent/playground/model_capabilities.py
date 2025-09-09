"""
Model Capabilities - Define what features each model supports
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ModelFamily(Enum):
    """Supported model families"""
    GPT_4_1 = "gpt-4.1"
    GPT_4O = "gpt-4o" 
    O_SERIES = "o-series"
    GPT_5 = "gpt-5"


@dataclass
class ModelSupports:
    """What features a model supports"""
    tools: bool = True
    vision: bool = False
    reasoning_items: bool = False
    reasoning_effort: bool = False
    verbosity: bool = False
    streaming: bool = True
    uses_completion_tokens: bool = False  # True for reasoning models that use max_completion_tokens


@dataclass
class ModelDefaults:
    """Default parameter values for a model"""
    temperature: Optional[float] = 0.2  # None for reasoning models
    top_p: Optional[float] = 1.0        # None for reasoning models
    reasoning_effort: Optional[str] = None
    verbosity: Optional[str] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None  # For reasoning models


@dataclass
class ModelCapabilities:
    """Complete capability definition for a model"""
    family: ModelFamily
    model_name: str
    display_name: str
    supports: ModelSupports
    defaults: ModelDefaults
    description: str


# Model capability definitions
MODEL_CAPS: Dict[str, ModelCapabilities] = {
    "gpt-4.1": ModelCapabilities(
        family=ModelFamily.GPT_4_1,
        model_name="gpt-4.1",
        display_name="GPT-4.1",
        supports=ModelSupports(
            tools=True,
            vision=True,
            reasoning_items=False,
            reasoning_effort=False,
            verbosity=False,
            streaming=True
        ),
        defaults=ModelDefaults(
            temperature=0.2,
            top_p=1.0,
            max_tokens=4096
        ),
        description="Latest GPT-4.1 with enhanced reasoning and long context"
    ),
    
    "gpt-4o": ModelCapabilities(
        family=ModelFamily.GPT_4O,
        model_name="gpt-4o",
        display_name="GPT-4o",
        supports=ModelSupports(
            tools=True,
            vision=True,
            reasoning_items=False,
            reasoning_effort=False,
            verbosity=False,
            streaming=True
        ),
        defaults=ModelDefaults(
            temperature=0.2,
            top_p=1.0,
            max_tokens=4096
        ),
        description="GPT-4o optimized for speed and efficiency"
    ),
    
    "o3": ModelCapabilities(
        family=ModelFamily.O_SERIES,
        model_name="o3",
        display_name="o3",
        supports=ModelSupports(
            tools=True,
            vision=False,
            reasoning_items=True,
            reasoning_effort=True,
            verbosity=False,
            streaming=True,
            uses_completion_tokens=True  # Reasoning model
        ),
        defaults=ModelDefaults(
            temperature=None,  # Not supported in reasoning models
            top_p=None,        # Not supported in reasoning models
            reasoning_effort="medium",
            max_completion_tokens=4096  # Use completion tokens for reasoning models
        ),
        description="o3 reasoning model with advanced problem-solving"
    ),
    
    "o4-mini": ModelCapabilities(
        family=ModelFamily.O_SERIES,
        model_name="o4-mini",
        display_name="o4-mini",
        supports=ModelSupports(
            tools=True,
            vision=False,
            reasoning_items=True,
            reasoning_effort=True,
            verbosity=False,
            streaming=True,
            uses_completion_tokens=True  # Reasoning model
        ),
        defaults=ModelDefaults(
            temperature=None,  # Not supported in reasoning models
            top_p=None,        # Not supported in reasoning models
            reasoning_effort="low",
            max_completion_tokens=2048  # Use completion tokens for reasoning models
        ),
        description="Lightweight o4-mini reasoning model for fast inference"
    ),
    
    "gpt-5": ModelCapabilities(
        family=ModelFamily.GPT_5,
        model_name="gpt-5",
        display_name="GPT-5",
        supports=ModelSupports(
            tools=True,
            vision=True,
            reasoning_items=True,
            reasoning_effort=True,
            verbosity=True,
            streaming=True,
            uses_completion_tokens=True  # Reasoning model
        ),
        defaults=ModelDefaults(
            temperature=None,  # Not supported in reasoning models
            top_p=None,        # Not supported in reasoning models
            reasoning_effort="medium",
            verbosity="medium",
            max_completion_tokens=8192  # Use completion tokens for reasoning models
        ),
        description="GPT-5 with advanced reasoning, verbosity control, and enhanced tools"
    )
}


# Parameter options
REASONING_EFFORT_OPTIONS = ["minimal", "low", "medium", "high"]
VERBOSITY_OPTIONS = ["low", "medium", "high"]


def get_model_caps(model_name: str) -> Optional[ModelCapabilities]:
    """Get capabilities for a specific model"""
    return MODEL_CAPS.get(model_name)


def get_available_models() -> Dict[str, ModelCapabilities]:
    """Get all available models and their capabilities"""
    return MODEL_CAPS.copy()


def get_models_by_family(family: ModelFamily) -> Dict[str, ModelCapabilities]:
    """Get all models from a specific family"""
    return {
        name: caps for name, caps in MODEL_CAPS.items() 
        if caps.family == family
    }


def supports_feature(model_name: str, feature: str) -> bool:
    """Check if a model supports a specific feature"""
    caps = get_model_caps(model_name)
    if not caps:
        return False
    
    return getattr(caps.supports, feature, False)


def get_model_defaults(model_name: str) -> Optional[ModelDefaults]:
    """Get default parameters for a model"""
    caps = get_model_caps(model_name)
    return caps.defaults if caps else None


def is_reasoning_model(model_name: str) -> bool:
    """Check if a model is a reasoning model that uses max_completion_tokens"""
    caps = get_model_caps(model_name)
    return caps.supports.uses_completion_tokens if caps else False


def get_supported_reasoning_efforts(model_name: str) -> List[str]:
    """Get supported reasoning effort levels for a model"""
    caps = get_model_caps(model_name)
    if not caps or not caps.supports.reasoning_effort:
        return []
    
    # GPT-5 supports minimal, others don't
    if caps.family == ModelFamily.GPT_5:
        return REASONING_EFFORT_OPTIONS  # includes minimal
    else:
        return [opt for opt in REASONING_EFFORT_OPTIONS if opt != "minimal"]


def supports_temperature_top_p(model_name: str) -> bool:
    """Check if a model supports temperature and top_p parameters"""
    caps = get_model_caps(model_name)
    if not caps:
        return True  # Default to supporting them
    
    # Reasoning models don't support temperature/top_p
    return not caps.supports.uses_completion_tokens