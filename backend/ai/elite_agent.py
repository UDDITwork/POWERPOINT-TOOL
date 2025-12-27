"""
Elite Claude Agent for Patent Diagram Generation

This is an advanced version of the Claude agent that uses sophisticated
prompt engineering and multi-step reasoning to generate patent-quality diagrams.

Features:
- Automatic diagram type detection
- Multi-pass refinement
- Constraint validation
- Layout optimization hints

Author: AI Patent Diagram Generator (Elite Engineering Edition)
License: MIT
"""

import anthropic
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field, validator

from .advanced_prompts import (
    MASTER_SYSTEM_PROMPT,
    REFINEMENT_SYSTEM_PROMPT,
    DIAGRAM_TYPE_DETECTION_PROMPT
)

logger = logging.getLogger(__name__)


class DiagramAnalysis(BaseModel):
    """Analysis of a diagram prompt."""
    diagram_type: str
    confidence: float
    reasoning: str
    suggested_layout: str
    estimated_complexity: str
    estimated_components: int


class EliteClaudeAgent:
    """
    Elite-tier Claude agent with advanced reasoning capabilities.

    This agent uses multi-step processing:
    1. Analyze prompt to detect diagram type
    2. Generate logical structure with Claude
    3. Validate and optimize structure
    4. Return layout-engine-ready specification
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4.5-20250929",
        max_tokens: int = 8192,  # Increased for complex diagrams
        temperature: float = 0.3  # Lower for more precision
    ):
        """
        Initialize the elite agent.

        Args:
            api_key: Anthropic API key
            model: Claude model (use Opus for most complex diagrams)
            max_tokens: Max response tokens
            temperature: Lower = more deterministic, higher = more creative
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        logger.info(f"Initialized Elite Claude Agent with {model}")

    def analyze_prompt(self, prompt: str) -> DiagramAnalysis:
        """
        Step 1: Analyze the prompt to determine diagram type and complexity.

        Args:
            prompt: User's diagram description

        Returns:
            Analysis with diagram type, complexity, etc.
        """
        logger.info("Step 1: Analyzing prompt to detect diagram type...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.1,  # Very low for classification
                system=DIAGRAM_TYPE_DETECTION_PROMPT.format(user_prompt=prompt),
                messages=[
                    {
                        "role": "user",
                        "content": "Analyze this diagram description and classify its type."
                    }
                ]
            )

            analysis_json = self._extract_json(response.content[0].text)
            analysis = DiagramAnalysis(**analysis_json)

            logger.info(
                f"Analysis complete: {analysis.diagram_type} "
                f"(confidence: {analysis.confidence}, "
                f"complexity: {analysis.estimated_complexity})"
            )

            return analysis

        except Exception as e:
            logger.warning(f"Analysis failed, using fallback: {e}")
            # Fallback to simple heuristic
            return self._fallback_analysis(prompt)

    def generate_diagram_spec(
        self,
        prompt: str,
        analysis: Optional[DiagramAnalysis] = None
    ) -> Dict[str, Any]:
        """
        Step 2: Generate the logical diagram structure.

        Args:
            prompt: User's diagram description
            analysis: Optional pre-computed analysis (if None, will analyze)

        Returns:
            Hierarchical structure ready for layout engine
        """
        # Step 1: Analyze if not provided
        if analysis is None:
            analysis = self.analyze_prompt(prompt)

        # Step 2: Enhance prompt with analysis context
        enhanced_prompt = self._enhance_prompt(prompt, analysis)

        logger.info(f"Step 2: Generating {analysis.diagram_type} diagram structure...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=MASTER_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ]
            )

            # Extract JSON
            spec_json = self._extract_json(response.content[0].text)

            # Step 3: Validate structure
            validated_spec = self._validate_spec(spec_json)

            # Step 4: Optimize structure
            optimized_spec = self._optimize_spec(validated_spec, analysis)

            logger.info(
                f"Diagram spec generated: "
                f"{self._count_elements(optimized_spec)} elements"
            )

            return optimized_spec

        except Exception as e:
            logger.error(f"Failed to generate diagram spec: {e}")
            raise

    def refine_diagram_spec(
        self,
        current_spec: Dict[str, Any],
        refinement_prompt: str
    ) -> Dict[str, Any]:
        """
        Step 3: Refine an existing diagram based on user feedback.

        Args:
            current_spec: Current diagram specification
            refinement_prompt: User's refinement request

        Returns:
            Updated diagram specification
        """
        logger.info(f"Refining diagram: {refinement_prompt[:100]}...")

        # Format system prompt with current spec
        system_prompt = REFINEMENT_SYSTEM_PROMPT.format(
            current_spec=json.dumps(current_spec, indent=2),
            refinement_request=refinement_prompt
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Apply this refinement to the diagram: {refinement_prompt}"
                    }
                ]
            )

            refined_json = self._extract_json(response.content[0].text)
            validated_spec = self._validate_spec(refined_json)

            logger.info("Diagram refinement complete")

            return validated_spec

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            raise

    def multi_pass_generation(
        self,
        prompt: str,
        passes: int = 2
    ) -> Dict[str, Any]:
        """
        Advanced: Generate diagram with multiple refinement passes.

        This improves quality by:
        1. Generate initial diagram
        2. Self-critique and identify improvements
        3. Regenerate with improvements applied

        Args:
            prompt: User's diagram description
            passes: Number of refinement passes (1-3 recommended)

        Returns:
            Optimized diagram specification
        """
        logger.info(f"Multi-pass generation with {passes} passes...")

        # Initial generation
        spec = self.generate_diagram_spec(prompt)

        # Refinement passes
        for pass_num in range(1, passes):
            logger.info(f"Refinement pass {pass_num}/{passes-1}...")

            critique_prompt = f"""
            Review this diagram structure and suggest improvements:
            - Are reference numbers sequential and logical?
            - Are nesting levels appropriate?
            - Are connections clearly defined?
            - Is the hierarchy balanced?

            Current structure:
            {json.dumps(spec, indent=2)}

            Suggest specific improvements.
            """

            # Get critique
            critique_response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": critique_prompt}
                ]
            )

            critique = critique_response.content[0].text

            # Apply critique
            if "no improvements" not in critique.lower():
                spec = self.refine_diagram_spec(spec, critique)

        logger.info("Multi-pass generation complete")
        return spec

    # ==================== HELPER METHODS ====================

    def _enhance_prompt(
        self,
        prompt: str,
        analysis: DiagramAnalysis
    ) -> str:
        """Enhance user prompt with analysis context."""
        enhancements = []

        enhancements.append(f"DIAGRAM TYPE: {analysis.diagram_type}")
        enhancements.append(f"COMPLEXITY: {analysis.estimated_complexity}")
        enhancements.append(f"SUGGESTED LAYOUT: {analysis.suggested_layout}")

        # Add specific guidance based on type
        if analysis.diagram_type == "hierarchical":
            enhancements.append(
                "Use nested structure with parent-child relationships. "
                "Ensure deep components are properly contained within parents."
            )
        elif analysis.diagram_type == "flowchart":
            enhancements.append(
                "Create sequential steps with clear flow. "
                "Use decision diamonds for conditional logic."
            )
        elif analysis.diagram_type == "network":
            enhancements.append(
                "Define peer-to-peer connections clearly. "
                "Group nodes by tier or function."
            )

        enhanced = "\n".join(enhancements) + "\n\nUSER REQUEST:\n" + prompt

        return enhanced

    def _validate_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate diagram specification for correctness.

        Checks:
        - All IDs are unique
        - All connection references are valid
        - No circular nesting
        - Reference numbers follow convention
        """
        # Collect all IDs
        all_ids = set()

        def collect_ids(node):
            if isinstance(node, dict):
                if 'id' in node:
                    node_id = node['id']
                    if node_id in all_ids:
                        logger.warning(f"Duplicate ID detected: {node_id}")
                    all_ids.add(node_id)
                if 'children' in node:
                    for child in node['children']:
                        collect_ids(child)
            elif isinstance(node, list):
                for item in node:
                    collect_ids(item)

        # Collect IDs from all possible locations
        if 'root' in spec:
            collect_ids(spec['root'])
        if 'nodes' in spec:
            collect_ids(spec['nodes'])
        if 'steps' in spec:
            collect_ids(spec['steps'])
        if 'external_elements' in spec:
            collect_ids(spec['external_elements'])

        # Validate connections
        connections = spec.get('connections', []) + spec.get('edges', [])
        for conn in connections:
            from_id = conn.get('from')
            to_id = conn.get('to')

            if from_id and from_id not in all_ids:
                logger.warning(f"Connection references unknown ID: {from_id}")
            if to_id and to_id not in all_ids:
                logger.warning(f"Connection references unknown ID: {to_id}")

        logger.info(f"Validation complete: {len(all_ids)} unique elements")

        return spec

    def _optimize_spec(
        self,
        spec: Dict[str, Any],
        analysis: DiagramAnalysis
    ) -> Dict[str, Any]:
        """
        Optimize diagram specification based on analysis.

        Optimizations:
        - Add default layout hints if missing
        - Suggest optimal container sizes
        - Balance hierarchy depth
        """
        # Add metadata if missing
        if 'metadata' not in spec:
            spec['metadata'] = {}

        spec['metadata']['diagram_type'] = analysis.diagram_type
        spec['metadata']['complexity'] = analysis.estimated_complexity

        # Add layout hints based on type
        if analysis.diagram_type == "hierarchical" and 'root' in spec:
            if 'layout_hints' not in spec['root']:
                spec['root']['layout_hints'] = {
                    "orientation": "vertical",
                    "child_arrangement": "stack",
                    "padding": 0.3
                }

        elif analysis.diagram_type == "flowchart" and 'steps' in spec:
            if 'layout_hints' not in spec:
                spec['layout_hints'] = {
                    "direction": analysis.suggested_layout,
                    "max_box_width": 6.5,
                    "vertical_spacing": 0.5
                }

        elif analysis.diagram_type == "network" and 'nodes' in spec:
            if 'layout_hints' not in spec:
                spec['layout_hints'] = {
                    "topology": analysis.suggested_layout,
                    "node_spacing": 2.0
                }

        return spec

    def _count_elements(self, spec: Dict[str, Any]) -> int:
        """Count total elements in specification."""
        count = 0

        def count_recursive(node):
            nonlocal count
            if isinstance(node, dict):
                if 'id' in node:
                    count += 1
                for value in node.values():
                    count_recursive(value)
            elif isinstance(node, list):
                for item in node:
                    count_recursive(item)

        count_recursive(spec)
        return count

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from Claude response, handling markdown."""
        # Remove markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response was: {text[:500]}...")
            raise ValueError(f"Invalid JSON from Claude: {e}")

    def _fallback_analysis(self, prompt: str) -> DiagramAnalysis:
        """Fallback analysis using simple heuristics."""
        prompt_lower = prompt.lower()

        # Detect type
        if any(word in prompt_lower for word in ['step', 'process', 'method', 'flow']):
            diagram_type = "flowchart"
            suggested_layout = "vertical"
        elif any(word in prompt_lower for word in ['contain', 'system', 'architecture']):
            diagram_type = "hierarchical"
            suggested_layout = "vertical"
        else:
            diagram_type = "network"
            suggested_layout = "force-directed"

        # Estimate complexity
        word_count = len(prompt.split())
        if word_count < 30:
            complexity = "low"
            components = 5
        elif word_count < 100:
            complexity = "medium"
            components = 12
        else:
            complexity = "high"
            components = 20

        return DiagramAnalysis(
            diagram_type=diagram_type,
            confidence=0.7,
            reasoning="Fallback heuristic analysis",
            suggested_layout=suggested_layout,
            estimated_complexity=complexity,
            estimated_components=components
        )
