"""
Anthropic Claude AI Agent for Patent Diagram Generation

This module uses Claude to parse natural language prompts and generate
structured JSON specifications for PowerPoint diagrams.

Features:
- Intelligent prompt analysis
- Patent-aware diagram conventions
- Layout optimization
- Iterative refinement support

Author: AI Patent Diagram Generator
License: MIT
"""

import anthropic
import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiagramSpec(BaseModel):
    """Pydantic model for diagram specification validation."""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    elements: List[Dict[str, Any]] = Field(default_factory=list)
    layout: Dict[str, Any] = Field(default_factory=dict)


class ClaudeDiagramAgent:
    """
    AI agent powered by Anthropic Claude for diagram generation.

    The agent understands patent diagram conventions and generates
    structured JSON specifications that can be rendered by python-pptx.
    """

    # System prompt for diagram generation
    SYSTEM_PROMPT = """You are an expert AI assistant specialized in creating patent diagram specifications.

Your task is to convert natural language descriptions into structured JSON specifications for PowerPoint diagrams.

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations, no extra text
2. All shapes must have: id, type, position {x, y}, size {width, height}
3. Position and size values are in INCHES (slide is 10" wide × 7.5" tall)
4. For patent diagrams, use reference numbers like (100), (110), (200), etc.
5. Flowcharts flow top-to-bottom unless specified otherwise
6. Leave 0.5-1.0 inch margins from slide edges
7. Connectors reference shape IDs via "from" and "to" fields

AVAILABLE SHAPE TYPES:
Basic: rectangle, rounded_rectangle, oval, diamond, hexagon, triangle, parallelogram
Flowchart: process, decision, terminator, data, document, predefined_process, flowchart_connector
Arrows: left_arrow, right_arrow, up_arrow, down_arrow, left_right_arrow, curved_right_arrow
Callouts: callout, rounded_callout, cloud_callout, line_callout
Special: star, heart, cloud, lightning, gear, plus, minus

CONNECTOR TYPES:
- straight (default for flowcharts)
- elbow (for complex routing)
- curve (for organic diagrams)

JSON STRUCTURE:
{
  "metadata": {
    "title": "Diagram Title",
    "diagram_type": "flowchart|block_diagram|architecture|network"
  },
  "elements": [
    {
      "id": "unique_id",
      "type": "shape_type",
      "position": {"x": 2.0, "y": 1.5},
      "size": {"width": 2.5, "height": 1.0},
      "text": "Label Text\\n(100)",
      "text_format": {
        "font_size": 12,
        "bold": false,
        "align": "center",
        "vertical_align": "middle"
      },
      "style": {
        "fill_color": "FFFFFF",
        "line_color": "000000",
        "line_width": 1.5
      }
    },
    {
      "id": "connector_1",
      "type": "connector",
      "connector_type": "straight",
      "from": "shape1_id",
      "to": "shape2_id",
      "from_side": "bottom",
      "to_side": "top",
      "style": {
        "arrow_end": true,
        "line_width": 1.5,
        "line_color": "000000"
      }
    }
  ],
  "layout": {
    "direction": "vertical|horizontal",
    "spacing": 1.5,
    "alignment": "center"
  }
}

LAYOUT GUIDELINES:
- Vertical flowcharts: x positions consistent, y spacing 1.5-2.0"
- Horizontal flows: y positions consistent, x spacing 2.0-2.5"
- Center elements: x = 3.5-4.5" for 2.5" wide shapes
- Top margin: y = 1.0-1.5" for first element
- Between shapes: 1.5" minimum spacing

PATENT CONVENTIONS:
- Reference numbers: (100), (110), (120), (200), (210), etc.
- Main components: 100-series
- Sub-components: 110, 120, 130, etc.
- Alternative systems: 200-series, 300-series
- Format text as "Component Name\\n(Reference Number)"

EXAMPLES:

Example 1 - Simple Flowchart:
User: "Create a 3-step flowchart: input (100), processing (200), output (300)"
{
  "metadata": {"title": "Process Flow", "diagram_type": "flowchart"},
  "elements": [
    {
      "id": "step1",
      "type": "terminator",
      "position": {"x": 3.75, "y": 1.0},
      "size": {"width": 2.5, "height": 0.8},
      "text": "Input Data\\n(100)",
      "text_format": {"font_size": 12, "align": "center"},
      "style": {"fill_color": "E7E6E6", "line_color": "000000", "line_width": 1.5}
    },
    {
      "id": "step2",
      "type": "process",
      "position": {"x": 3.75, "y": 3.0},
      "size": {"width": 2.5, "height": 1.0},
      "text": "Processing\\n(200)",
      "text_format": {"font_size": 12, "align": "center"},
      "style": {"fill_color": "FFFFFF", "line_color": "000000", "line_width": 1.5}
    },
    {
      "id": "step3",
      "type": "terminator",
      "position": {"x": 3.75, "y": 5.5},
      "size": {"width": 2.5, "height": 0.8},
      "text": "Output Result\\n(300)",
      "text_format": {"font_size": 12, "align": "center"},
      "style": {"fill_color": "E7E6E6", "line_color": "000000", "line_width": 1.5}
    },
    {
      "id": "conn1",
      "type": "connector",
      "connector_type": "straight",
      "from": "step1",
      "to": "step2",
      "from_side": "bottom",
      "to_side": "top",
      "style": {"arrow_end": true, "line_width": 1.5}
    },
    {
      "id": "conn2",
      "type": "connector",
      "connector_type": "straight",
      "from": "step2",
      "to": "step3",
      "from_side": "bottom",
      "to_side": "top",
      "style": {"arrow_end": true, "line_width": 1.5}
    }
  ],
  "layout": {"direction": "vertical", "spacing": 1.5}
}

Example 2 - Block Diagram:
User: "Server (100) connected to database (110) and three clients (200, 210, 220)"
{
  "metadata": {"title": "System Architecture", "diagram_type": "block_diagram"},
  "elements": [
    {
      "id": "server",
      "type": "rectangle",
      "position": {"x": 3.5, "y": 3.0},
      "size": {"width": 3.0, "height": 1.5},
      "text": "Server\\n(100)",
      "style": {"fill_color": "4472C4", "line_color": "000000", "line_width": 2}
    },
    {
      "id": "database",
      "type": "oval",
      "position": {"x": 7.5, "y": 3.0},
      "size": {"width": 2.0, "height": 1.5},
      "text": "Database\\n(110)",
      "style": {"fill_color": "70AD47", "line_color": "000000", "line_width": 2}
    },
    {
      "id": "client1",
      "type": "rounded_rectangle",
      "position": {"x": 1.0, "y": 1.0},
      "size": {"width": 2.0, "height": 1.0},
      "text": "Client 1\\n(200)",
      "style": {"fill_color": "FFC000", "line_color": "000000"}
    },
    {
      "id": "client2",
      "type": "rounded_rectangle",
      "position": {"x": 1.0, "y": 3.25},
      "size": {"width": 2.0, "height": 1.0},
      "text": "Client 2\\n(210)",
      "style": {"fill_color": "FFC000", "line_color": "000000"}
    },
    {
      "id": "client3",
      "type": "rounded_rectangle",
      "position": {"x": 1.0, "y": 5.5},
      "size": {"width": 2.0, "height": 1.0},
      "text": "Client 3\\n(220)",
      "style": {"fill_color": "FFC000", "line_color": "000000"}
    },
    {
      "id": "c1",
      "type": "connector",
      "from": "server",
      "to": "database",
      "style": {"arrow_end": true, "arrow_start": true}
    },
    {
      "id": "c2",
      "type": "connector",
      "from": "client1",
      "to": "server",
      "style": {"arrow_end": true, "arrow_start": true}
    },
    {
      "id": "c3",
      "type": "connector",
      "from": "client2",
      "to": "server",
      "style": {"arrow_end": true, "arrow_start": true}
    },
    {
      "id": "c4",
      "type": "connector",
      "from": "client3",
      "to": "server",
      "style": {"arrow_end": true, "arrow_start": true}
    }
  ]
}

NOW: Convert the user's prompt into a valid JSON specification following these rules exactly.

CRITICAL JSON REQUIREMENTS:
- Output ONLY valid JSON - no markdown, no code blocks, no comments
- NO trailing commas in arrays or objects
- Use only double quotes for strings (not single quotes)
- Ensure all brackets and braces are properly closed
- No comments (// or /* */) anywhere in the JSON
- Numbers must be valid (no NaN, Infinity)
- Return the raw JSON object directly without wrapping
"""

    REFINEMENT_PROMPT_TEMPLATE = """You are refining an existing diagram based on user feedback.

CURRENT DIAGRAM SPEC:
{current_spec}

USER REFINEMENT REQUEST:
{refinement_request}

INSTRUCTIONS:
1. Analyze the user's request
2. Modify the existing JSON spec accordingly
3. Preserve all elements unless explicitly told to remove them
4. Return the COMPLETE updated JSON spec (not just changes)
5. Maintain consistent positioning and alignment

Common refinements:
- "Make X wider/taller" → Increase width/height
- "Move X to the left/right" → Adjust x position
- "Add a box labeled Y" → Add new element with appropriate positioning
- "Change color of X" → Modify fill_color in style
- "Add arrow from A to B" → Add new connector element
- "Remove X" → Remove element from array

OUTPUT: Complete updated JSON specification

CRITICAL JSON REQUIREMENTS:
- Output ONLY valid JSON - no markdown, no code blocks, no comments
- NO trailing commas in arrays or objects
- Use only double quotes for strings (not single quotes)
- Ensure all brackets and braces are properly closed
- No comments (// or /* */) anywhere in the JSON
- Numbers must be valid (no NaN, Infinity)
- Return the raw JSON object directly without wrapping
"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 4096,
        temperature: float = 0.0  # Changed from 0.7 - deterministic for JSON
    ):
        """
        Initialize the Claude agent with Structured Outputs support.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0.0 for JSON generation)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        logger.info(f"Initialized Claude agent with model: {model}")

    def generate_diagram_spec(self, prompt: str) -> Dict[str, Any]:
        """
        Generate a diagram specification from a natural language prompt.

        Args:
            prompt: User's diagram description

        Returns:
            Dictionary containing diagram specification

        Raises:
            ValueError: If Claude returns invalid JSON
            anthropic.APIError: If API call fails
        """
        logger.info(f"Generating diagram from prompt: {prompt[:100]}...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.0,  # Deterministic for JSON generation
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                extra_headers={
                    "anthropic-beta": "structured-outputs-2025-11-13"
                },
                extra_body={
                    "output_format": {
                        "type": "json",
                        "schema": DiagramSpec.model_json_schema()  # Enforce Pydantic schema
                    }
                }
            )

            # Response is guaranteed valid JSON matching DiagramSpec schema
            response_text = response.content[0].text

            logger.debug(f"Claude response (Structured Output): {response_text[:200]}...")

            # Direct parse - no cleaning needed with Structured Outputs
            spec = json.loads(response_text)

            # Validate spec (should always pass with Structured Outputs)
            validated_spec = DiagramSpec(**spec)

            logger.info(f"Successfully generated spec with {len(validated_spec.elements)} elements")

            return validated_spec.dict()

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            logger.error(f"Response was: {response_text}")
            raise ValueError(f"Invalid JSON from Claude: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating diagram: {e}")
            raise

    def refine_diagram_spec(
        self,
        current_spec: Dict[str, Any],
        refinement_prompt: str
    ) -> Dict[str, Any]:
        """
        Refine an existing diagram based on user feedback.

        Args:
            current_spec: Current diagram specification
            refinement_prompt: User's refinement request

        Returns:
            Updated diagram specification
        """
        logger.info(f"Refining diagram: {refinement_prompt[:100]}...")

        # Format the refinement system prompt
        system_prompt = self.REFINEMENT_PROMPT_TEMPLATE.format(
            current_spec=json.dumps(current_spec, indent=2),
            refinement_request=refinement_prompt
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.0,  # Deterministic for JSON generation
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Apply this refinement: {refinement_prompt}"
                    }
                ],
                extra_headers={
                    "anthropic-beta": "structured-outputs-2025-11-13"
                },
                extra_body={
                    "output_format": {
                        "type": "json",
                        "schema": DiagramSpec.model_json_schema()  # Enforce Pydantic schema
                    }
                }
            )

            # Response is guaranteed valid JSON matching DiagramSpec schema
            response_text = response.content[0].text
            spec = json.loads(response_text)  # Direct parse - no cleaning needed

            # Validate (should always pass with Structured Outputs)
            validated_spec = DiagramSpec(**spec)

            logger.info("Successfully refined diagram")

            return validated_spec.dict()

        except Exception as e:
            logger.error(f"Error refining diagram: {e}")
            raise

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from Claude's response with aggressive error handling.

        Args:
            text: Response text that may contain JSON

        Returns:
            Parsed JSON dictionary
        """
        import re

        # Remove markdown code blocks if present
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        # Aggressive JSON cleaning

        # 1. Remove all types of comments
        text = re.sub(r'//[^\n]*', '', text)  # Single-line comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)  # Multi-line comments

        # 2. Fix Unicode characters
        text = text.replace('\u2019', "'")  # Right single quote
        text = text.replace('\u201c', '"')  # Left double quote
        text = text.replace('\u201d', '"')  # Right double quote
        text = text.replace('\u2018', "'")  # Left single quote
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '-')  # Em dash
        text = text.replace('\u00a0', ' ')  # Non-breaking space

        # 3. Remove trailing commas before closing brackets/braces (aggressive)
        # This handles multiple cases: , }, , ], ,  }, etc.
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        # Handle nested cases
        text = re.sub(r',(\s*[}\]])', r'\1', text)  # Run twice for nested

        # 4. Fix common malformed patterns
        text = re.sub(r',\s*,', ',', text)  # Double commas
        text = re.sub(r':\s*,', ': null,', text)  # Empty values
        text = re.sub(r'{\s*,', '{', text)  # Comma at start of object
        text = re.sub(r'\[\s*,', '[', text)  # Comma at start of array

        # 5. Remove any text before first { or [
        first_brace = text.find('{')
        first_bracket = text.find('[')
        if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
            text = text[first_brace:]
        elif first_bracket != -1:
            text = text[first_bracket:]

        # 6. Remove any text after last } or ]
        last_brace = text.rfind('}')
        last_bracket = text.rfind(']')
        if last_brace > last_bracket:
            text = text[:last_brace + 1]
        elif last_bracket != -1:
            text = text[:last_bracket + 1]

        # Try to parse
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Detailed error logging
            logger.error(f"JSON parse error at line {e.lineno} column {e.colno}: {e.msg}")
            logger.error(f"Character at error: {repr(text[e.pos:e.pos+20]) if e.pos < len(text) else 'EOF'}")

            # Show context around error
            lines = text.split('\n')
            if e.lineno <= len(lines):
                start_line = max(0, e.lineno - 3)
                end_line = min(len(lines), e.lineno + 2)
                logger.error("Context:")
                for i in range(start_line, end_line):
                    prefix = ">>> " if i == e.lineno - 1 else "    "
                    logger.error(f"{prefix}{i + 1}: {lines[i]}")
                    if i == e.lineno - 1:
                        logger.error(f"    {' ' * len(str(i + 1))}  {' ' * (e.colno - 1)}^")

            # Log the cleaned JSON for debugging
            logger.error(f"Cleaned JSON (first 500 chars): {text[:500]}")
            logger.error(f"Cleaned JSON (last 500 chars): {text[-500:]}")

            raise ValueError(f"Invalid JSON from Claude: {e.msg} at line {e.lineno} column {e.colno}")

    def analyze_prompt_complexity(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze a prompt to estimate diagram complexity.

        Args:
            prompt: User's diagram description

        Returns:
            Dictionary with complexity metrics
        """
        # Simple heuristic analysis
        analysis = {
            "estimated_shapes": 0,
            "estimated_connectors": 0,
            "diagram_type": "unknown",
            "complexity": "low"
        }

        prompt_lower = prompt.lower()

        # Count potential shapes
        shape_keywords = ['step', 'block', 'box', 'circle', 'node', 'component', 'element', 'device']
        for keyword in shape_keywords:
            analysis["estimated_shapes"] += prompt_lower.count(keyword)

        # Estimate connectors
        connector_keywords = ['connect', 'arrow', 'link', 'flow', 'to']
        for keyword in connector_keywords:
            analysis["estimated_connectors"] += prompt_lower.count(keyword)

        # Determine diagram type
        if any(word in prompt_lower for word in ['flowchart', 'flow', 'process', 'step']):
            analysis["diagram_type"] = "flowchart"
        elif any(word in prompt_lower for word in ['architecture', 'system', 'block diagram']):
            analysis["diagram_type"] = "block_diagram"
        elif any(word in prompt_lower for word in ['network', 'topology']):
            analysis["diagram_type"] = "network"

        # Complexity
        total_elements = analysis["estimated_shapes"] + analysis["estimated_connectors"]
        if total_elements < 5:
            analysis["complexity"] = "low"
        elif total_elements < 15:
            analysis["complexity"] = "medium"
        else:
            analysis["complexity"] = "high"

        return analysis


# Convenience function
def generate_from_prompt(prompt: str, api_key: str) -> Dict[str, Any]:
    """
    Quick function to generate diagram spec from prompt.

    Args:
        prompt: Diagram description
        api_key: Anthropic API key

    Returns:
        Diagram specification dictionary
    """
    agent = ClaudeDiagramAgent(api_key=api_key)
    return agent.generate_diagram_spec(prompt)
