"""
Configuration for Patent Diagram AI Backend

This module contains all configurable settings for diagram generation,
including model selection, extended thinking parameters, and validation settings.

Author: AI Patent Diagram Generator
License: MIT
"""

import os
from typing import Literal

# ============ MODEL CONFIGURATION ============

# Available models
MODEL_OPUS = "claude-opus-4-5-20251101"  # Premium - best quality, extended thinking
MODEL_SONNET = "claude-sonnet-4-5"       # Fast - good for simple diagrams

# Default model (can be overridden by environment variable)
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", MODEL_OPUS)

# ============ EXTENDED THINKING CONFIGURATION ============

THINKING_CONFIG = {
    # Enable extended thinking (Opus only)
    "enabled": True,

    # Token budget for thinking (minimum 1024, recommended 10K-32K)
    # Higher budget = more reasoning = better quality but more cost
    "budget_tokens": int(os.getenv("THINKING_BUDGET", "16000")),

    # Budget presets for different complexity levels
    "budget_presets": {
        "simple": 5000,      # 3-5 nodes
        "medium": 10000,     # 6-10 nodes
        "complex": 16000,    # 10-20 nodes
        "very_complex": 32000  # 20+ nodes
    }
}

# ============ VALIDATION CONFIGURATION ============

VALIDATION_CONFIG = {
    # Enable self-validation loop
    "self_validation_enabled": True,

    # Maximum attempts to generate valid diagram
    "max_validation_attempts": 2,

    # Thinking budget for validation (smaller than generation)
    "validation_thinking_budget": 5000,

    # Enable geometric validation after generation
    "geometric_validation": True,

    # Enable Vision AI validation (screenshot analysis)
    "vision_validation": False,  # Disabled by default (expensive)
}

# ============ LAYOUT CONFIGURATION ============

LAYOUT_CONFIG = {
    # Use ELK layout engine for position calculation
    "use_elk_layout": True,

    # Fallback to basic layout if ELK fails
    "fallback_to_basic": True,

    # Minimum spacing between nodes (inches)
    "min_node_spacing": 0.5,

    # Default direction for flowcharts
    "default_direction": "DOWN",

    # Slide dimensions (inches)
    "slide_width": 10.0,
    "slide_height": 7.5,

    # Margins (inches)
    "margin_left": 0.5,
    "margin_right": 0.5,
    "margin_top": 0.5,
    "margin_bottom": 0.5,
}

# ============ GENERATION CONFIGURATION ============

GENERATION_CONFIG = {
    # Maximum tokens for response
    "max_tokens": 16000,

    # Temperature (0.0 for deterministic JSON)
    # Note: Extended thinking requires temperature=1 (default)
    "temperature": 1.0,  # Required for extended thinking

    # Use structured outputs beta
    "use_structured_outputs": False,  # Disabled when using extended thinking

    # Retry configuration
    "max_retries": 3,
    "retry_delay": 1.0,  # seconds
}

# ============ EFFORT CONFIGURATION (Opus only) ============

EFFORT_CONFIG = {
    # Enable effort parameter (Opus 4.5 only)
    "enabled": False,  # Set to True to use effort parameter

    # Default effort level: "low", "medium", "high"
    "default_effort": "high",

    # Effort presets based on diagram complexity
    "effort_presets": {
        "simple": "medium",
        "medium": "high",
        "complex": "high"
    }
}

# ============ API CONFIGURATION ============

API_CONFIG = {
    # Anthropic API key (from environment)
    "api_key": os.getenv("ANTHROPIC_API_KEY"),

    # API base URL (optional, for proxies)
    "base_url": os.getenv("ANTHROPIC_BASE_URL"),

    # Request timeout (seconds)
    "timeout": 120,

    # Beta features to enable
    "betas": [
        # "effort-2025-11-24",  # Uncomment to enable effort parameter
        # "interleaved-thinking-2025-05-14",  # For multi-turn thinking
    ]
}

# ============ LOGGING CONFIGURATION ============

LOGGING_CONFIG = {
    # Log thinking blocks
    "log_thinking": True,

    # Log full JSON specs
    "log_specs": True,

    # Log validation results
    "log_validation": True,

    # Maximum characters to log for thinking
    "thinking_log_limit": 500,
}

# ============ COMBINED DIAGRAM CONFIG ============

DIAGRAM_CONFIG = {
    # Model
    "model": DEFAULT_MODEL,

    # Extended thinking
    "thinking_enabled": THINKING_CONFIG["enabled"],
    "thinking_budget": THINKING_CONFIG["budget_tokens"],

    # Validation
    "self_validation_enabled": VALIDATION_CONFIG["self_validation_enabled"],
    "max_validation_attempts": VALIDATION_CONFIG["max_validation_attempts"],
    "geometric_validation": VALIDATION_CONFIG["geometric_validation"],

    # Layout
    "use_elk_layout": LAYOUT_CONFIG["use_elk_layout"],

    # Generation
    "max_tokens": GENERATION_CONFIG["max_tokens"],
}


def get_thinking_budget_for_complexity(node_count: int) -> int:
    """
    Get appropriate thinking budget based on diagram complexity.

    Args:
        node_count: Estimated number of nodes in the diagram

    Returns:
        Recommended thinking budget in tokens
    """
    if node_count <= 5:
        return THINKING_CONFIG["budget_presets"]["simple"]
    elif node_count <= 10:
        return THINKING_CONFIG["budget_presets"]["medium"]
    elif node_count <= 20:
        return THINKING_CONFIG["budget_presets"]["complex"]
    else:
        return THINKING_CONFIG["budget_presets"]["very_complex"]


def get_effort_for_complexity(node_count: int) -> Literal["low", "medium", "high"]:
    """
    Get appropriate effort level based on diagram complexity.

    Args:
        node_count: Estimated number of nodes in the diagram

    Returns:
        Recommended effort level
    """
    if node_count <= 5:
        return EFFORT_CONFIG["effort_presets"]["simple"]
    elif node_count <= 10:
        return EFFORT_CONFIG["effort_presets"]["medium"]
    else:
        return EFFORT_CONFIG["effort_presets"]["complex"]


def validate_config():
    """Validate configuration and return any issues."""
    issues = []

    if not API_CONFIG["api_key"]:
        issues.append("ANTHROPIC_API_KEY environment variable not set")

    if THINKING_CONFIG["budget_tokens"] < 1024:
        issues.append("thinking_budget must be at least 1024 tokens")

    if GENERATION_CONFIG["max_tokens"] <= THINKING_CONFIG["budget_tokens"]:
        issues.append("max_tokens must be greater than thinking_budget")

    return issues
