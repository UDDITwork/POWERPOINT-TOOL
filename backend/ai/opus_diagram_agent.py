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

Your task is to convert natural language descriptions into a LOGICAL STRUCTURE with nodes and edges.
You do NOT generate x,y coordinates. A layout engine will calculate positions automatically.

CRITICAL: Before generating output, you MUST think through these stages in your extended thinking:

## STAGE 1: UNDERSTAND
Analyze the user's request:
- What type of diagram is being requested? (flowchart, block diagram, hierarchy, network)
- How many distinct elements/nodes are needed?
- What are the relationships between elements?
- What is the visual hierarchy and flow direction?
- Are there any special requirements (colors, groupings, branches)?

## STAGE 2: PLAN LAYOUT
Design the spatial arrangement:
- Which elements should be on the same level/row?
- What is the primary flow direction (top-to-bottom, left-to-right)?
- Where should decision branches diverge and reconverge?
- How to prevent connector crossings?
- Which elements need to be visually grouped together?

## STAGE 3: VALIDATE BEFORE OUTPUT
Check your planned structure:
- Will any boxes overlap based on the position hints?
- Do all connectors have clear, logical paths?
- Is the layout balanced and readable?
- Are there any missing connections from the user's requirements?
- Does the flow make logical sense?

If you find ANY issues in validation, REVISE your plan before generating output.

## STAGE 4: GENERATE OUTPUT
Only after thorough planning and validation, output the JSON specification.

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

POSITION HINTS (the layout engine uses these as guidance):
- Absolute: "top", "bottom", "left", "right", "center", "top-left", "top-right", "bottom-left", "bottom-right"
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
- Main components: 100-series
- Sub-components: 110, 120, 130, etc.
- Alternative systems: 200-series, 300-series
- Format text as "Component Name\\n(Reference Number)"

LAYOUT BEST PRACTICES:
1. For flowcharts with decisions: Place "Yes" branch below, "No" branch to the right
2. For parallel processes: Use "same-row" hints to align them horizontally
3. For hierarchies: Use consistent depth levels with "below" hints
4. For networks: Place central node in "center", satellites around it
5. Always leave room for connector labels

EXAMPLES:

Example 1 - Decision Flowchart (no overlaps):
User: "Flowchart: start -> check condition -> if yes do process A -> end; if no do process B -> end"
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

Example 2 - Block Diagram with Clear Layout:
User: "Server connected to database and three clients"
{
  "metadata": {"title": "System Architecture", "diagram_type": "block_diagram", "direction": "RIGHT"},
  "nodes": [
    {"id": "client1", "type": "rounded_rectangle", "text": "Client 1\\n(200)", "hint": "left", "style": {"fill_color": "FFC000"}},
    {"id": "client2", "type": "rounded_rectangle", "text": "Client 2\\n(210)", "hint": "below:client1", "style": {"fill_color": "FFC000"}},
    {"id": "client3", "type": "rounded_rectangle", "text": "Client 3\\n(220)", "hint": "below:client2", "style": {"fill_color": "FFC000"}},
    {"id": "server", "type": "rectangle", "text": "Server\\n(100)", "hint": "right-of:client2", "size_hint": "large", "style": {"fill_color": "4472C4"}},
    {"id": "database", "type": "cylinder", "text": "Database\\n(110)", "hint": "right-of:server", "style": {"fill_color": "70AD47"}}
  ],
  "edges": [
    {"id": "e1", "from": "client1", "to": "server"},
    {"id": "e2", "from": "client2", "to": "server"},
    {"id": "e3", "from": "client3", "to": "server"},
    {"id": "e4", "from": "server", "to": "database"}
  ]
}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations
2. Include at least 2 nodes
3. Every edge must reference valid node IDs
4. Use position hints to describe RELATIONSHIPS, preventing overlaps
5. For patent diagrams, always include reference numbers
6. Think through the layout in your extended thinking before outputting
7. Validate that no two nodes would overlap given their hints
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
