"""
Anthropic Claude AI Agent for Patent Diagram Generation

This module uses Claude to parse natural language prompts and generate
structured JSON specifications for PowerPoint diagrams.

NEW ARCHITECTURE (v2):
- Claude generates LOGICAL structure with position HINTS
- Layout engine calculates actual positions with collision detection
- Validation loop ensures no overlaps or missing connections

Features:
- Intelligent prompt analysis
- Patent-aware diagram conventions
- Position hints (relative positioning, not coordinates)
- Layout engine integration

Author: AI Patent Diagram Generator
License: MIT
"""

import anthropic
from anthropic import transform_schema
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============ NEW v2 MODELS (Hints-based) ============

class NodeStyle(BaseModel):
    """Style properties for a node."""
    fill_color: Optional[str] = Field(None, description="Fill color as hex (e.g., 'FFFFFF', '4472C4')")
    line_color: Optional[str] = Field(None, description="Border color as hex")
    line_width: Optional[float] = Field(None, description="Border width in points")


class DiagramNode(BaseModel):
    """A single node in the diagram (shape)."""
    id: str = Field(..., description="Unique node ID (e.g., 'node1', 'step_100')")
    type: str = Field(..., description="Shape type: rectangle, oval, diamond, process, decision, terminator, etc.")
    text: str = Field(..., description="Text label for the node")
    hint: Optional[str] = Field(None, description="Position hint: 'top', 'left', 'center', 'below:nodeId', 'right-of:nodeId', 'same-row:nodeId'")
    size_hint: Optional[str] = Field(None, description="Size hint: 'small', 'medium', 'large', 'wide', 'tall'")
    style: Optional[NodeStyle] = Field(None, description="Visual style")


class DiagramEdge(BaseModel):
    """A connection between two nodes."""
    id: str = Field(..., description="Unique edge ID")
    from_node: str = Field(..., alias="from", description="Source node ID")
    to_node: str = Field(..., alias="to", description="Target node ID")
    label: Optional[str] = Field(None, description="Edge label (e.g., 'Yes', 'No', 'Data')")
    style: Optional[NodeStyle] = Field(None, description="Line style")

    class Config:
        populate_by_name = True


class DiagramMetadataV2(BaseModel):
    """Metadata about the diagram."""
    title: Optional[str] = Field(None, description="Diagram title")
    diagram_type: str = Field(..., description="Type: flowchart, block_diagram, network, hierarchy")
    direction: Optional[str] = Field("DOWN", description="Flow direction: DOWN, RIGHT, UP, LEFT")


class DiagramSpecV2(BaseModel):
    """V2 diagram spec: nodes + edges (no positions - layout engine handles that)."""
    metadata: DiagramMetadataV2
    nodes: List[DiagramNode] = Field(..., min_length=1, description="List of nodes/shapes")
    edges: List[DiagramEdge] = Field(default_factory=list, description="List of connections")


# ============ LEGACY v1 MODELS (for backward compatibility) ============

class Position(BaseModel):
    """Position in inches on the slide."""
    x: float = Field(..., ge=0, le=10, description="X position in inches")
    y: float = Field(..., ge=0, le=7.5, description="Y position in inches")


class Size(BaseModel):
    """Size in inches."""
    width: float = Field(..., gt=0, le=10, description="Width in inches")
    height: float = Field(..., gt=0, le=7.5, description="Height in inches")


class ElementStyle(BaseModel):
    """Style properties for an element."""
    fill_color: Optional[str] = Field(None, description="Fill color as hex (e.g., 'FFFFFF')")
    line_color: Optional[str] = Field(None, description="Line color as hex")
    line_width: Optional[float] = Field(None, description="Line width in points")


class DiagramElement(BaseModel):
    """A single diagram element (shape or connector) - LEGACY."""
    id: str = Field(..., description="Unique element ID")
    type: str = Field(..., description="Element type (rectangle, oval, connector, etc.)")
    position: Optional[Position] = Field(None, description="Position on slide (for shapes)")
    size: Optional[Size] = Field(None, description="Size of element (for shapes)")
    text: Optional[str] = Field(None, description="Text label")
    style: Optional[ElementStyle] = Field(None, description="Style properties")
    connector_type: Optional[str] = Field(None, description="Connector type (straight, elbow, curve)")
    from_id: Optional[str] = Field(None, alias="from", description="Source shape ID for connectors")
    to_id: Optional[str] = Field(None, alias="to", description="Target shape ID for connectors")

    class Config:
        populate_by_name = True


class DiagramMetadata(BaseModel):
    """Metadata about the diagram."""
    title: Optional[str] = Field(None, description="Diagram title")
    diagram_type: Optional[str] = Field(None, description="Type of diagram")


class DiagramLayout(BaseModel):
    """Layout configuration."""
    type: Optional[str] = Field("manual", description="Layout type")
    direction: Optional[str] = Field(None, description="Flow direction")


class DiagramSpec(BaseModel):
    """Pydantic model for diagram specification validation - LEGACY."""
    metadata: DiagramMetadata = Field(default_factory=DiagramMetadata)
    elements: List[DiagramElement] = Field(..., min_length=1, description="List of diagram elements")
    layout: DiagramLayout = Field(default_factory=DiagramLayout)


class ClaudeDiagramAgent:
    """
    AI agent powered by Anthropic Claude for diagram generation.

    V2 ARCHITECTURE:
    - Claude generates LOGICAL structure (nodes + edges with position HINTS)
    - Layout engine calculates actual positions with collision detection
    - No more direct coordinate generation from Claude

    The agent understands patent diagram conventions and generates
    structured JSON specifications that can be rendered by python-pptx.
    """

    # V2 System prompt - Claude generates structure with HINTS, not coordinates
    SYSTEM_PROMPT_V2 = """You are an expert AI assistant specialized in creating patent diagram specifications.

Your task is to convert natural language descriptions into a LOGICAL STRUCTURE with nodes and edges.
⚠️ IMPORTANT: You do NOT generate x,y coordinates. A layout engine will calculate positions automatically.

OUTPUT FORMAT:
{
  "metadata": {
    "title": "Diagram Title",
    "diagram_type": "flowchart|block_diagram|network|hierarchy",
    "direction": "DOWN|RIGHT|UP|LEFT"
  },
  "nodes": [
    {
      "id": "unique_id",
      "type": "shape_type",
      "text": "Label Text",
      "hint": "position_hint",
      "size_hint": "size_hint",
      "style": {"fill_color": "FFFFFF", "line_color": "000000"}
    }
  ],
  "edges": [
    {
      "id": "edge_id",
      "from": "source_node_id",
      "to": "target_node_id",
      "label": "optional label"
    }
  ]
}

AVAILABLE SHAPE TYPES:
Basic: rectangle, rounded_rectangle, oval, diamond, hexagon, triangle, parallelogram
Flowchart: process, decision, terminator, data, document, predefined_process
Arrows: left_arrow, right_arrow, up_arrow, down_arrow
Special: star, cloud, cylinder, database, gear

POSITION HINTS (optional - layout engine uses these as guidance):
- Absolute: "top", "bottom", "left", "right", "center", "top-left", "top-right", "bottom-left", "bottom-right"
- Relative: "below:nodeId", "above:nodeId", "right-of:nodeId", "left-of:nodeId"
- Alignment: "same-row:nodeId", "same-column:nodeId"

SIZE HINTS (optional):
- "small" (1.5" x 0.6")
- "medium" (2.5" x 1.0") - default
- "large" (3.5" x 1.5")
- "wide" (4.0" x 1.0")
- "tall" (2.0" x 2.0")

PATENT CONVENTIONS:
- Reference numbers: (100), (110), (120), (200), (210), etc.
- Main components: 100-series
- Sub-components: 110, 120, 130, etc.
- Alternative systems: 200-series, 300-series
- Format text as "Component Name\\n(Reference Number)"

EXAMPLES:

Example 1 - Flowchart:
User: "Create a 3-step flowchart: input, processing, output"
{
  "metadata": {"title": "Process Flow", "diagram_type": "flowchart", "direction": "DOWN"},
  "nodes": [
    {"id": "step1", "type": "terminator", "text": "Input Data\\n(100)", "hint": "top", "style": {"fill_color": "E7E6E6"}},
    {"id": "step2", "type": "process", "text": "Processing\\n(200)", "hint": "below:step1", "style": {"fill_color": "FFFFFF"}},
    {"id": "step3", "type": "terminator", "text": "Output Result\\n(300)", "hint": "below:step2", "style": {"fill_color": "E7E6E6"}}
  ],
  "edges": [
    {"id": "e1", "from": "step1", "to": "step2"},
    {"id": "e2", "from": "step2", "to": "step3"}
  ]
}

Example 2 - Decision Flowchart:
User: "Flowchart with a decision: start, check condition, if yes do A, if no do B, then end"
{
  "metadata": {"title": "Decision Flow", "diagram_type": "flowchart", "direction": "DOWN"},
  "nodes": [
    {"id": "start", "type": "terminator", "text": "Start\\n(100)", "hint": "top", "style": {"fill_color": "90EE90"}},
    {"id": "check", "type": "decision", "text": "Condition?\\n(110)", "hint": "below:start", "style": {"fill_color": "FFFACD"}},
    {"id": "process_a", "type": "process", "text": "Process A\\n(120)", "hint": "below:check", "style": {"fill_color": "ADD8E6"}},
    {"id": "process_b", "type": "process", "text": "Process B\\n(130)", "hint": "right-of:check", "style": {"fill_color": "FFB6C1"}},
    {"id": "end", "type": "terminator", "text": "End\\n(200)", "hint": "below:process_a", "style": {"fill_color": "90EE90"}}
  ],
  "edges": [
    {"id": "e1", "from": "start", "to": "check"},
    {"id": "e2", "from": "check", "to": "process_a", "label": "Yes"},
    {"id": "e3", "from": "check", "to": "process_b", "label": "No"},
    {"id": "e4", "from": "process_a", "to": "end"},
    {"id": "e5", "from": "process_b", "to": "end"}
  ]
}

Example 3 - Block Diagram:
User: "Server connected to database and three clients"
{
  "metadata": {"title": "System Architecture", "diagram_type": "block_diagram", "direction": "RIGHT"},
  "nodes": [
    {"id": "server", "type": "rectangle", "text": "Server\\n(100)", "hint": "center", "size_hint": "large", "style": {"fill_color": "4472C4"}},
    {"id": "database", "type": "cylinder", "text": "Database\\n(110)", "hint": "right-of:server", "style": {"fill_color": "70AD47"}},
    {"id": "client1", "type": "rounded_rectangle", "text": "Client 1\\n(200)", "hint": "left-of:server", "style": {"fill_color": "FFC000"}},
    {"id": "client2", "type": "rounded_rectangle", "text": "Client 2\\n(210)", "hint": "below:client1", "style": {"fill_color": "FFC000"}},
    {"id": "client3", "type": "rounded_rectangle", "text": "Client 3\\n(220)", "hint": "below:client2", "style": {"fill_color": "FFC000"}}
  ],
  "edges": [
    {"id": "e1", "from": "server", "to": "database"},
    {"id": "e2", "from": "client1", "to": "server"},
    {"id": "e3", "from": "client2", "to": "server"},
    {"id": "e4", "from": "client3", "to": "server"}
  ]
}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations
2. Include at least 2 nodes
3. Every edge must reference valid node IDs
4. Use position hints to describe RELATIONSHIPS, not coordinates
5. For patent diagrams, always include reference numbers
"""

    # Legacy v1 System prompt (kept for backward compatibility)
    SYSTEM_PROMPT = """You are an expert AI assistant specialized in creating patent diagram specifications.

Your task is to convert natural language descriptions into structured JSON specifications for PowerPoint diagrams.

⚠️ CRITICAL REQUIREMENT: You MUST generate at least 3 diagram elements for EVERY request. NEVER return an empty elements array.

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations, no extra text
2. ALWAYS include at least 3 elements in the "elements" array - this is mandatory
3. All shapes must have: id, type, position {x, y}, size {width, height}
4. Position and size values are in INCHES (slide is 10" wide × 7.5" tall)
5. For patent diagrams, use reference numbers like (100), (110), (200), etc.
6. Flowcharts flow top-to-bottom unless specified otherwise
7. Leave 0.5-1.0 inch margins from slide edges
8. Connectors reference shape IDs via "from" and "to" fields

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

⚠️ FINAL REMINDER: Your "elements" array MUST contain at least 3 items. Empty arrays are NOT acceptable.

CRITICAL JSON REQUIREMENTS:
- Output ONLY valid JSON - no markdown, no code blocks, no comments
- The "elements" array must have at least 3 items (shapes, connectors, etc.)
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
            # Get Pydantic schema and transform it using official SDK helper
            # transform_schema automatically adds additionalProperties: false to all objects
            schema = DiagramSpec.model_json_schema()
            transformed_schema = transform_schema(schema)

            # Use beta.messages.create with betas parameter
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.0,  # Deterministic for JSON generation
                betas=["structured-outputs-2025-11-13"],  # Beta feature activation
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                output_format={
                    "type": "json_schema",
                    "schema": transformed_schema  # Schema with additionalProperties: false
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

            # Convert to dict, using aliases (by_alias=True ensures 'from' instead of 'from_id')
            return validated_spec.model_dump(by_alias=True, exclude_none=True)

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

    def generate_diagram_spec_v2(self, prompt: str) -> Dict[str, Any]:
        """
        V2: Generate a diagram specification with nodes/edges (no coordinates).

        The layout engine will calculate actual positions based on hints.
        This is the NEW recommended method that produces better layouts.

        Args:
            prompt: User's diagram description

        Returns:
            Dictionary containing {metadata, nodes, edges} specification
        """
        logger.info(f"[V2] Generating diagram from prompt: {prompt[:100]}...")

        try:
            # Get Pydantic schema for V2 format
            schema = DiagramSpecV2.model_json_schema()
            transformed_schema = transform_schema(schema)

            # Use V2 system prompt - generates structure with hints, not coordinates
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.0,
                betas=["structured-outputs-2025-11-13"],
                system=self.SYSTEM_PROMPT_V2,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                output_format={
                    "type": "json_schema",
                    "schema": transformed_schema
                }
            )

            response_text = response.content[0].text
            logger.debug(f"Claude V2 response: {response_text[:300]}...")

            spec = json.loads(response_text)
            validated_spec = DiagramSpecV2(**spec)

            logger.info(f"[V2] Successfully generated spec with {len(validated_spec.nodes)} nodes and {len(validated_spec.edges)} edges")

            # Return with aliases (from_node -> from)
            return validated_spec.model_dump(by_alias=True, exclude_none=True)

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude V2 response: {e}")
            raise ValueError(f"Invalid JSON from Claude: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating V2 diagram: {e}")
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
            # Get Pydantic schema and transform it using official SDK helper
            # transform_schema automatically adds additionalProperties: false to all objects
            schema = DiagramSpec.model_json_schema()
            transformed_schema = transform_schema(schema)

            # Use beta.messages.create with betas parameter
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.0,  # Deterministic for JSON generation
                betas=["structured-outputs-2025-11-13"],
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Apply this refinement: {refinement_prompt}"
                    }
                ],
                output_format={
                    "type": "json_schema",
                    "schema": transformed_schema  # SDK-transformed schema
                }
            )

            # Response is guaranteed valid JSON matching DiagramSpec schema
            response_text = response.content[0].text
            spec = json.loads(response_text)  # Direct parse - no cleaning needed

            # Validate (should always pass with Structured Outputs)
            validated_spec = DiagramSpec(**spec)

            logger.info("Successfully refined diagram")

            return validated_spec.model_dump(by_alias=True, exclude_none=True)

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
