"""
Model Capabilities - Define what features each model supports
"""

from typing import Dict, Any, Optional
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


@dataclass
class ModelDefaults:
    """Default parameter values for a model"""
    temperature: float = 0.2
    top_p: float = 1.0
    reasoning_effort: Optional[str] = None
    verbosity: Optional[str] = None
    max_tokens: Optional[int] = None


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
            streaming=True
        ),
        defaults=ModelDefaults(
            temperature=0.2,
            top_p=1.0,
            reasoning_effort="medium",
            max_tokens=4096
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
            streaming=True
        ),
        defaults=ModelDefaults(
            temperature=0.2,
            top_p=1.0,
            reasoning_effort="low",
            max_tokens=2048
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
            streaming=True
        ),
        defaults=ModelDefaults(
            temperature=0.2,
            top_p=1.0,
            reasoning_effort="medium",
            verbosity="medium",
            max_tokens=8192
        ),
        description="GPT-5 with advanced reasoning, verbosity control, and enhanced tools"
    )
}


# Parameter options
REASONING_EFFORT_OPTIONS = ["low", "medium", "high"]
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