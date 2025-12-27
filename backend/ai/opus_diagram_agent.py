"""
Claude Opus 4.5 Diagram Agent with Extended Thinking

This module implements a premium diagram generation agent using Claude Opus 4.5
with extended thinking capabilities for multi-step reasoning.

Key Features:
1. Extended thinking with configurable budget (10K-32K tokens)
2. Multi-stage reasoning: UNDERSTAND -> PLAN -> VALIDATE -> GENERATE
3. Self-validation loop to catch errors before output
4. Thinking transparency for debugging

Author: AI Patent Diagram Generator
License: MIT
"""

import anthropic
import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NodeStyle(BaseModel):
    """Style properties for a node."""
    fill_color: Optional[str] = Field(None, description="Fill color as hex (e.g., 'FFFFFF', '4472C4')")
    line_color: Optional[str] = Field(None, description="Border color as hex")
    line_width: Optional[float] = Field(None, description="Border width in points")
    border_style: Optional[str] = Field(None, description="Border style: 'solid', 'dashed', 'dotted'")


class DiagramNode(BaseModel):
    """A single node in the diagram (shape)."""
    id: str = Field(..., description="Unique node ID (e.g., 'node1', 'step_100')")
    type: str = Field(..., description="Shape type: rectangle, oval, diamond, process, decision, terminator, etc.")
    text: str = Field(..., description="Text label for the node")
    hint: Optional[str] = Field(None, description="Position hint: 'top', 'left', 'center', 'below:nodeId', 'right-of:nodeId', 'same-row:nodeId'")
    size_hint: Optional[str] = Field(None, description="Size hint: 'small', 'medium', 'large', 'wide', 'tall'")
    style: Optional[NodeStyle] = Field(None, description="Visual style")
    parent: Optional[str] = Field(None, description="Parent container ID for nested elements")
    children: Optional[List[str]] = Field(None, description="Child node IDs for inline nesting")


class DiagramContainer(BaseModel):
    """A container/group that holds related nodes together."""
    id: str = Field(..., description="Unique container ID (e.g., 'group_100', 'container_A')")
    label: str = Field(..., description="Container label text")
    children: List[str] = Field(..., description="List of child node IDs contained in this group")
    style: Optional[NodeStyle] = Field(None, description="Visual style - typically dashed border")
    hint: Optional[str] = Field(None, description="Position hint for the container")


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
    diagram_type: str = Field(..., description="Type: flowchart, block_diagram, network, hierarchical")
    direction: Optional[str] = Field("DOWN", description="Flow direction: DOWN, RIGHT, UP, LEFT")


class DiagramSpecV2(BaseModel):
    """V2 diagram spec with hierarchical container support."""
    metadata: DiagramMetadataV2
    containers: Optional[List[DiagramContainer]] = Field(default_factory=list, description="List of container groups with dashed borders")
    nodes: List[DiagramNode] = Field(..., min_length=1, description="List of nodes/shapes")
    edges: List[DiagramEdge] = Field(default_factory=list, description="List of connections")


class OpusDiagramAgent:
    """
    Premium diagram agent using Claude Opus 4.5 with extended thinking.

    This agent leverages Claude's extended thinking capability to perform
    multi-step reasoning before generating diagram specifications. This results
    in higher quality outputs with better spatial reasoning.

    Key differences from ClaudeDiagramAgent:
    1. Uses claude-opus-4-5-20251101 model
    2. Enables extended thinking with configurable token budget
    3. Multi-stage reasoning prompt (UNDERSTAND -> PLAN -> VALIDATE -> GENERATE)
    4. Processes and logs thinking blocks for transparency
    5. Optional self-validation loop before returning output
    """

    # Multi-stage reasoning system prompt for Opus with extended thinking
    SYSTEM_PROMPT_OPUS = """You are an expert patent diagram architect using multi-step reasoning.

Your task is to convert natural language descriptions into a HIERARCHICAL STRUCTURE with containers, nodes, and edges.
You do NOT generate x,y coordinates. A layout engine will calculate positions automatically.

CRITICAL: Before generating output, you MUST think through these stages in your extended thinking:

## STAGE 1: UNDERSTAND
Analyze the user's request:
- What type of diagram is being requested? (flowchart, block diagram, hierarchy, network)
- How many distinct elements/nodes are needed?
- What are the relationships between elements?
- What is the visual hierarchy and flow direction?
- Are there LOGICAL GROUPINGS? (elements that belong together conceptually)

## STAGE 2: IDENTIFY CONTAINERS/GROUPS
Determine which elements should be grouped together:
- Look for subsystems, modules, or related components
- Identify parent-child relationships
- Find elements that share a common purpose or location
- Create CONTAINERS with DASHED BORDERS to visually group related items

## STAGE 3: PLAN LAYOUT
Design the spatial arrangement:
- Which containers should be side-by-side vs stacked?
- Which elements belong INSIDE which container?
- What is the primary flow direction (top-to-bottom, left-to-right)?
- How to prevent connector crossings?

## STAGE 4: VALIDATE BEFORE OUTPUT
Check your planned structure:
- Does every child node reference its parent container?
- Are containers properly sized to fit their children?
- Do all connectors have clear, logical paths?
- Is the layout balanced and readable?

If you find ANY issues in validation, REVISE your plan before generating output.

## STAGE 5: GENERATE OUTPUT
Only after thorough planning and validation, output the JSON specification.

OUTPUT FORMAT WITH HIERARCHICAL CONTAINERS:
{
  "metadata": {
    "title": "Diagram Title",
    "diagram_type": "hierarchical|flowchart|block_diagram|network",
    "direction": "DOWN|RIGHT|UP|LEFT"
  },
  "containers": [
    {
      "id": "container_100",
      "label": "Container Name (100)",
      "children": ["node_110", "node_120", "node_130"],
      "style": {"border_style": "dashed"},
      "hint": "left"
    }
  ],
  "nodes": [
    {
      "id": "node_110",
      "type": "rectangle",
      "text": "Node Label\\n(110)",
      "parent": "container_100",
      "hint": "top",
      "size_hint": "medium"
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

CONTAINER RULES (CRITICAL FOR PATENT DIAGRAMS):
1. Use containers to GROUP related elements visually
2. Containers have DASHED BORDERS by default (style: {"border_style": "dashed"})
3. Every node inside a container MUST have "parent": "container_id"
4. Container's "children" array lists all node IDs inside it
5. Containers can be side-by-side using hints like "right-of:other_container"
6. Containers automatically size to fit their children

AVAILABLE SHAPE TYPES:
Basic: rectangle, rounded_rectangle, oval, diamond, hexagon, triangle, parallelogram
Flowchart: process, decision, terminator, data, document, predefined_process
Arrows: left_arrow, right_arrow, up_arrow, down_arrow
Special: star, cloud, cylinder, database, gear

POSITION HINTS:
- Absolute: "top", "bottom", "left", "right", "center"
- Relative: "below:nodeId", "above:nodeId", "right-of:nodeId", "left-of:nodeId"
- Alignment: "same-row:nodeId", "same-column:nodeId"

SIZE HINTS:
- "small" (1.5" x 0.6")
- "medium" (2.5" x 1.0") - default
- "large" (3.5" x 1.5")
- "wide" (4.0" x 1.0")
- "tall" (2.0" x 2.0")

PATENT CONVENTIONS:
- Reference numbers: (100), (110), (120), (200), (210), etc.
- Main components/containers: 100-series, 200-series
- Sub-components inside containers: 110, 120, 130, etc.
- Format text as "Component Name\\n(Reference Number)"

EXAMPLES:

Example 1 - Hierarchical System with Containers:
User: "System 400 with Offline Setup 416A containing Input Block 402A with Traces 404A and Edges 406A, and Runtime Setup 416B containing Input Block 402B"
{
  "metadata": {"title": "System Architecture 400", "diagram_type": "hierarchical", "direction": "RIGHT"},
  "containers": [
    {
      "id": "container_416A",
      "label": "Offline Warmup Setup\\n(416A)",
      "children": ["402A", "404A", "406A"],
      "style": {"border_style": "dashed"},
      "hint": "left"
    },
    {
      "id": "container_416B",
      "label": "Runtime Setup\\n(416B)",
      "children": ["402B", "214A"],
      "style": {"border_style": "dashed"},
      "hint": "right-of:container_416A"
    }
  ],
  "nodes": [
    {"id": "402A", "type": "rectangle", "text": "Input Block\\n(402A)", "parent": "container_416A", "hint": "top"},
    {"id": "404A", "type": "rectangle", "text": "Traces\\n(404A)", "parent": "container_416A", "hint": "below:402A"},
    {"id": "406A", "type": "rectangle", "text": "Edges\\n(406A)", "parent": "container_416A", "hint": "below:404A"},
    {"id": "402B", "type": "rectangle", "text": "Input Block\\n(402B)", "parent": "container_416B", "hint": "top"},
    {"id": "214A", "type": "rectangle", "text": "Model\\n(214A)", "parent": "container_416B", "hint": "below:402B"}
  ],
  "edges": [
    {"id": "e1", "from": "402A", "to": "404A"},
    {"id": "e2", "from": "404A", "to": "406A"},
    {"id": "e3", "from": "container_416A", "to": "container_416B", "label": "Data Flow"}
  ]
}

Example 2 - Nested Hierarchy:
User: "Main System with Module A containing Sub-A1 and Sub-A2, and Module B containing Sub-B1"
{
  "metadata": {"title": "Nested System", "diagram_type": "hierarchical", "direction": "DOWN"},
  "containers": [
    {
      "id": "module_a",
      "label": "Module A\\n(100)",
      "children": ["sub_a1", "sub_a2"],
      "style": {"border_style": "dashed"},
      "hint": "left"
    },
    {
      "id": "module_b",
      "label": "Module B\\n(200)",
      "children": ["sub_b1"],
      "style": {"border_style": "dashed"},
      "hint": "right-of:module_a"
    }
  ],
  "nodes": [
    {"id": "sub_a1", "type": "rectangle", "text": "Sub-A1\\n(110)", "parent": "module_a", "hint": "top"},
    {"id": "sub_a2", "type": "rectangle", "text": "Sub-A2\\n(120)", "parent": "module_a", "hint": "below:sub_a1"},
    {"id": "sub_b1", "type": "rectangle", "text": "Sub-B1\\n(210)", "parent": "module_b", "hint": "top"}
  ],
  "edges": [
    {"id": "e1", "from": "sub_a1", "to": "sub_a2"},
    {"id": "e2", "from": "sub_a2", "to": "sub_b1"}
  ]
}

Example 3 - Simple Flowchart (no containers needed):
User: "Flowchart: start -> process -> end"
{
  "metadata": {"title": "Simple Flow", "diagram_type": "flowchart", "direction": "DOWN"},
  "containers": [],
  "nodes": [
    {"id": "start", "type": "terminator", "text": "Start\\n(100)", "hint": "top"},
    {"id": "process", "type": "process", "text": "Process\\n(110)", "hint": "below:start"},
    {"id": "end", "type": "terminator", "text": "End\\n(200)", "hint": "below:process"}
  ],
  "edges": [
    {"id": "e1", "from": "start", "to": "process"},
    {"id": "e2", "from": "process", "to": "end"}
  ]
}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations
2. ALWAYS include "containers" array (can be empty [])
3. For any diagram with GROUPS or SUBSYSTEMS, use containers with dashed borders
4. Every node inside a container MUST have "parent" field matching container ID
5. Container's "children" array MUST list all its child node IDs
6. Every edge must reference valid node IDs
7. Use position hints to describe RELATIONSHIPS, preventing overlaps
8. For patent diagrams, always include reference numbers in parentheses
9. Think through the HIERARCHY in your extended thinking before outputting
"""

    VALIDATION_PROMPT_TEMPLATE = """You generated this diagram specification:
{spec}

Original request: {original_prompt}

VALIDATE this diagram for the following issues:

1. OVERLAP CHECK: Based on the position hints, would any nodes overlap or be too close?
   - Check if multiple nodes have conflicting hints (e.g., both "below:same_node")
   - Check if relative positions create overlap scenarios

2. CONNECTOR PATH CHECK: Would any connector paths cross through shapes?
   - Check if edges between distant nodes would pass through intermediate nodes

3. COMPLETENESS CHECK: Are all requested elements present?
   - Compare against the original request

4. LOGICAL FLOW CHECK: Does the layout make visual sense?
   - Is the flow direction consistent?
   - Are related elements grouped appropriately?

Return your validation as JSON:
{{
  "valid": true or false,
  "issues": ["issue description 1", "issue description 2"],
  "suggested_fixes": ["fix suggestion 1", "fix suggestion 2"]
}}

If valid is true, issues array should be empty.
Output ONLY the JSON, no other text.
"""

    REFINEMENT_PROMPT_TEMPLATE = """The previous diagram had these issues:
{issues}

Original request: {original_prompt}

Previous specification:
{current_spec}

Please generate an IMPROVED specification that fixes these issues.
Focus especially on:
1. Adjusting position hints to prevent overlaps
2. Ensuring clear connector paths
3. Maintaining logical flow

Output ONLY the corrected JSON specification.
"""

    def __init__(
        self,
        api_key: str,
        thinking_budget: int = 16000,
        max_tokens: int = 16000
    ):
        """
        Initialize the Opus diagram agent with extended thinking.

        Args:
            api_key: Anthropic API key
            thinking_budget: Token budget for extended thinking (min 1024, recommended 10K-32K)
            max_tokens: Maximum tokens for response (must be > thinking_budget)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-opus-4-5-20251101"
        self.thinking_budget = max(1024, thinking_budget)  # Enforce minimum
        self.max_tokens = max(max_tokens, self.thinking_budget + 4096)  # Ensure room for output

        logger.info(f"Initialized Opus agent with model: {self.model}, thinking_budget: {self.thinking_budget}")

    def generate_diagram_spec(self, prompt: str) -> Dict[str, Any]:
        """
        Generate diagram specification with extended thinking.

        This method enables Claude to reason through the diagram structure
        before generating output, resulting in better spatial layouts.

        Args:
            prompt: User's diagram description

        Returns:
            Dictionary containing:
            - spec: The diagram specification
            - thinking_summary: List of thinking block contents
            - tokens_used: Token usage statistics
        """
        logger.info(f"[Opus] Generating diagram with extended thinking: {prompt[:100]}...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget
                },
                system=self.SYSTEM_PROMPT_OPUS,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Process response blocks
            thinking_log = []
            output_text = None

            for block in response.content:
                if block.type == "thinking":
                    # Extended thinking block (may be summarized in Claude 4)
                    thinking_content = getattr(block, 'thinking', str(block))
                    thinking_log.append(thinking_content)
                    logger.debug(f"[Opus] Thinking: {thinking_content[:300]}...")
                elif block.type == "text":
                    output_text = block.text

            if not output_text:
                raise ValueError("No text output received from Claude")

            # Parse JSON output
            spec = self._extract_json(output_text)

            # Validate with Pydantic
            validated_spec = DiagramSpecV2(**spec)

            logger.info(f"[Opus] Generated spec with {len(validated_spec.nodes)} nodes, "
                       f"{len(validated_spec.edges)} edges, "
                       f"thinking blocks: {len(thinking_log)}")

            return {
                "spec": validated_spec.model_dump(by_alias=True, exclude_none=True),
                "thinking_summary": thinking_log,
                "tokens_used": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens
                }
            }

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            raise ValueError(f"Invalid JSON from Claude: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating diagram: {e}")
            raise

    def generate_with_validation(
        self,
        prompt: str,
        max_attempts: int = 2,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Generate diagram with optional self-validation loop.

        This method generates a diagram and then asks Claude to validate
        its own output. If issues are found, it regenerates with feedback.

        Args:
            prompt: User's diagram description
            max_attempts: Maximum generation attempts (default 2)
            validate: Whether to run self-validation (default True)

        Returns:
            Dictionary containing spec, thinking_summary, tokens_used, and validation_info
        """
        logger.info(f"[Opus] Generating with validation (max_attempts={max_attempts})")

        total_tokens = {"input": 0, "output": 0}
        all_thinking = []
        validation_history = []

        original_prompt = prompt

        for attempt in range(max_attempts):
            logger.info(f"[Opus] Attempt {attempt + 1}/{max_attempts}")

            # Generate diagram
            result = self.generate_diagram_spec(prompt)
            spec = result["spec"]
            all_thinking.extend(result["thinking_summary"])
            total_tokens["input"] += result["tokens_used"]["input"]
            total_tokens["output"] += result["tokens_used"]["output"]

            # Skip validation on last attempt or if disabled
            if not validate or attempt == max_attempts - 1:
                return {
                    "spec": spec,
                    "thinking_summary": all_thinking,
                    "tokens_used": total_tokens,
                    "validation_info": {
                        "attempts": attempt + 1,
                        "history": validation_history
                    }
                }

            # Self-validate
            validation = self._self_validate(spec, original_prompt)
            validation_history.append(validation)
            total_tokens["input"] += validation.get("tokens_used", {}).get("input", 0)
            total_tokens["output"] += validation.get("tokens_used", {}).get("output", 0)

            if validation.get("valid", True):
                logger.info("[Opus] Validation passed!")
                return {
                    "spec": spec,
                    "thinking_summary": all_thinking,
                    "tokens_used": total_tokens,
                    "validation_info": {
                        "attempts": attempt + 1,
                        "passed": True,
                        "history": validation_history
                    }
                }

            # Build refinement prompt for next attempt
            logger.info(f"[Opus] Validation found issues: {validation.get('issues', [])}")
            prompt = self._build_refinement_prompt(
                original_prompt=original_prompt,
                current_spec=spec,
                issues=validation.get("issues", [])
            )

        # Return best effort
        return {
            "spec": spec,
            "thinking_summary": all_thinking,
            "tokens_used": total_tokens,
            "validation_info": {
                "attempts": max_attempts,
                "passed": False,
                "history": validation_history
            }
        }

    def _self_validate(self, spec: Dict, original_prompt: str) -> Dict[str, Any]:
        """
        Ask Claude to validate its own diagram specification.

        Args:
            spec: The generated diagram specification
            original_prompt: The original user prompt

        Returns:
            Validation result with valid flag and issues list
        """
        logger.info("[Opus] Running self-validation...")

        validation_prompt = self.VALIDATION_PROMPT_TEMPLATE.format(
            spec=json.dumps(spec, indent=2),
            original_prompt=original_prompt
        )

        try:
            # Use smaller thinking budget for validation, but ensure max_tokens > budget
            validation_thinking_budget = 3000
            response = self.client.messages.create(
                model=self.model,
                max_tokens=validation_thinking_budget + 2000,  # Must be > thinking budget
                thinking={
                    "type": "enabled",
                    "budget_tokens": validation_thinking_budget
                },
                messages=[
                    {
                        "role": "user",
                        "content": validation_prompt
                    }
                ]
            )

            # Extract text response
            for block in response.content:
                if block.type == "text":
                    result = self._extract_json(block.text)
                    result["tokens_used"] = {
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens
                    }
                    return result

            return {"valid": True, "issues": []}

        except Exception as e:
            logger.error(f"Validation error: {e}")
            # On error, assume valid to avoid blocking
            return {"valid": True, "issues": [], "error": str(e)}

    def _build_refinement_prompt(
        self,
        original_prompt: str,
        current_spec: Dict,
        issues: List[str]
    ) -> str:
        """Build a refinement prompt incorporating validation issues."""
        return self.REFINEMENT_PROMPT_TEMPLATE.format(
            issues="\n".join(f"- {issue}" for issue in issues),
            original_prompt=original_prompt,
            current_spec=json.dumps(current_spec, indent=2)
        )

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from Claude's response with error handling.

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

        # Clean up common issues
        text = re.sub(r',(\s*[}\]])', r'\1', text)  # Remove trailing commas

        # Find JSON boundaries
        first_brace = text.find('{')
        if first_brace != -1:
            text = text[first_brace:]
        last_brace = text.rfind('}')
        if last_brace != -1:
            text = text[:last_brace + 1]

        return json.loads(text)


# Convenience function
def generate_with_opus(prompt: str, api_key: str, thinking_budget: int = 16000) -> Dict[str, Any]:
    """
    Quick function to generate diagram spec using Opus with extended thinking.

    Args:
        prompt: Diagram description
        api_key: Anthropic API key
        thinking_budget: Token budget for thinking

    Returns:
        Diagram specification with thinking summary
    """
    agent = OpusDiagramAgent(api_key=api_key, thinking_budget=thinking_budget)
    return agent.generate_with_validation(prompt)
