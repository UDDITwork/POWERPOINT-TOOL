"""
Unified Diagram Generation Pipeline

This is the master pipeline that combines:
1. Elite Claude Agent (logical structure generation)
2. Advanced Layout Engine (positioning & sizing)
3. python-pptx Generator (rendering to PPTX)

This is what achieves patent-quality diagrams like FIG. 2!

Author: AI Patent Diagram Generator (Elite Engineering Edition)
License: MIT
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from ai.elite_agent import EliteClaudeAgent
from diagram_engine.advanced_layout import (
    AdvancedHierarchicalLayout,
    create_advanced_layout_engine
)
from diagram_engine.layout_engine import FlowLayoutEngine, NetworkLayoutEngine
from diagram_engine.pptx_generator import PPTXDiagramGenerator

logger = logging.getLogger(__name__)


class PatentDiagramPipeline:
    """
    Master pipeline for generating patent-quality diagrams.

    This pipeline achieves the precision required for complex diagrams
    like FIG. 2 by using multi-stage processing:

    Stage 1: Claude analyzes prompt and generates logical structure
    Stage 2: Layout engine calculates precise positions
    Stage 3: python-pptx renders to editable PPTX

    Example:
        pipeline = PatentDiagramPipeline(anthropic_api_key="sk-ant-...")

        # Generate complex nested diagram
        pipeline.generate(
            prompt="Create diagram like FIG. 2 with nested components...",
            output_path="fig2.pptx"
        )

        # Result: Fully editable PPTX with perfect positioning!
    """

    def __init__(
        self,
        anthropic_api_key: str,
        model: str = "claude-sonnet-4.5-20250929",
        slide_width: float = 10.0,
        slide_height: float = 7.5,
        use_multi_pass: bool = False
    ):
        """
        Initialize the pipeline.

        Args:
            anthropic_api_key: Anthropic API key
            model: Claude model to use (Opus for most complex diagrams)
            slide_width: Slide width in inches
            slide_height: Slide height in inches
            use_multi_pass: Enable multi-pass refinement (slower but higher quality)
        """
        self.api_key = anthropic_api_key
        self.model = model
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.use_multi_pass = use_multi_pass

        # Initialize Claude agent
        self.agent = EliteClaudeAgent(
            api_key=anthropic_api_key,
            model=model
        )

        logger.info("Patent Diagram Pipeline initialized (ELITE MODE)")

    def generate(
        self,
        prompt: str,
        output_path: str,
        quality: str = "high"
    ) -> Dict[str, Any]:
        """
        Generate a patent diagram from prompt.

        Args:
            prompt: Natural language description of diagram
            output_path: Where to save the PPTX file
            quality: "high" (multi-pass) or "fast" (single-pass)

        Returns:
            Dict with generation metadata
        """
        logger.info("=" * 70)
        logger.info("PATENT DIAGRAM GENERATION - ELITE PIPELINE")
        logger.info("=" * 70)
        logger.info(f"Prompt: {prompt[:100]}...")
        logger.info(f"Quality: {quality}")
        logger.info("")

        # ==================== STAGE 1: ANALYSIS ====================
        logger.info("STAGE 1: Analyzing prompt with Claude...")
        analysis = self.agent.analyze_prompt(prompt)

        logger.info(f"  → Diagram Type: {analysis.diagram_type}")
        logger.info(f"  → Complexity: {analysis.estimated_complexity}")
        logger.info(f"  → Est. Components: {analysis.estimated_components}")
        logger.info(f"  → Suggested Layout: {analysis.suggested_layout}")
        logger.info("")

        # ==================== STAGE 2: STRUCTURE GENERATION ====================
        logger.info("STAGE 2: Generating logical structure...")

        if quality == "high" or self.use_multi_pass:
            # Multi-pass for highest quality
            logical_spec = self.agent.multi_pass_generation(prompt, passes=2)
            logger.info("  → Used multi-pass refinement")
        else:
            # Single-pass for speed
            logical_spec = self.agent.generate_diagram_spec(prompt, analysis)
            logger.info("  → Used single-pass generation")

        element_count = self._count_elements(logical_spec)
        logger.info(f"  → Generated {element_count} elements")
        logger.info("")

        # ==================== STAGE 3: LAYOUT CALCULATION ====================
        logger.info("STAGE 3: Calculating precise positions...")

        # Select appropriate layout engine
        layout_engine = self._get_layout_engine(analysis.diagram_type)

        # Calculate positions
        positioned_spec = layout_engine.calculate_layout(logical_spec)

        logger.info(f"  → Layout complete: {len(positioned_spec['elements'])} total elements")
        logger.info("")

        # ==================== STAGE 4: PPTX RENDERING ====================
        logger.info("STAGE 4: Rendering to PowerPoint...")

        generator = PPTXDiagramGenerator(
            width_inches=self.slide_width,
            height_inches=self.slide_height
        )

        generator.create_from_json(positioned_spec)
        generator.save(output_path)

        logger.info(f"  → Saved to: {output_path}")
        logger.info("")

        # ==================== COMPLETION ====================
        logger.info("=" * 70)
        logger.info("✅ GENERATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Output: {output_path}")
        logger.info(f"Elements: {len(positioned_spec['elements'])}")
        logger.info(f"Type: {analysis.diagram_type}")
        logger.info("")
        logger.info("📊 Open the file in PowerPoint - every element is editable!")
        logger.info("=" * 70)

        return {
            "success": True,
            "output_path": output_path,
            "diagram_type": analysis.diagram_type,
            "complexity": analysis.estimated_complexity,
            "element_count": len(positioned_spec['elements']),
            "logical_spec": logical_spec,
            "positioned_spec": positioned_spec
        }

    def refine(
        self,
        current_spec: Dict[str, Any],
        refinement_prompt: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Refine an existing diagram.

        Args:
            current_spec: Current logical specification
            refinement_prompt: User's refinement request
            output_path: Where to save refined PPTX

        Returns:
            Dict with refinement metadata
        """
        logger.info("REFINING DIAGRAM...")
        logger.info(f"Refinement: {refinement_prompt}")

        # Refine logical structure
        refined_logical = self.agent.refine_diagram_spec(
            current_spec,
            refinement_prompt
        )

        # Detect diagram type
        diagram_type = refined_logical.get('diagram_type', 'hierarchical')

        # Re-layout
        layout_engine = self._get_layout_engine(diagram_type)
        positioned_spec = layout_engine.calculate_layout(refined_logical)

        # Render
        generator = PPTXDiagramGenerator(self.slide_width, self.slide_height)
        generator.create_from_json(positioned_spec)
        generator.save(output_path)

        logger.info(f"✅ Refinement complete: {output_path}")

        return {
            "success": True,
            "output_path": output_path,
            "element_count": len(positioned_spec['elements']),
            "refined_spec": refined_logical
        }

    def generate_from_spec(
        self,
        logical_spec: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Generate PPTX from an existing logical specification.

        Useful for batch processing or when you already have the spec.

        Args:
            logical_spec: Logical diagram structure
            output_path: Where to save PPTX

        Returns:
            Path to saved file
        """
        diagram_type = logical_spec.get('diagram_type', 'hierarchical')

        # Layout
        layout_engine = self._get_layout_engine(diagram_type)
        positioned_spec = layout_engine.calculate_layout(logical_spec)

        # Render
        generator = PPTXDiagramGenerator(self.slide_width, self.slide_height)
        generator.create_from_json(positioned_spec)
        generator.save(output_path)

        logger.info(f"Generated from spec: {output_path}")

        return output_path

    # ==================== HELPER METHODS ====================

    def _get_layout_engine(self, diagram_type: str):
        """Get appropriate layout engine for diagram type."""
        if diagram_type == "hierarchical":
            return AdvancedHierarchicalLayout(
                slide_width=self.slide_width,
                slide_height=self.slide_height
            )
        elif diagram_type == "flowchart":
            return FlowLayoutEngine(
                slide_width=self.slide_width,
                slide_height=self.slide_height
            )
        elif diagram_type == "network":
            return NetworkLayoutEngine(
                slide_width=self.slide_width,
                slide_height=self.slide_height
            )
        else:
            # Default to hierarchical
            logger.warning(f"Unknown diagram type: {diagram_type}, using hierarchical")
            return AdvancedHierarchicalLayout(
                slide_width=self.slide_width,
                slide_height=self.slide_height
            )

    def _count_elements(self, spec: Dict[str, Any]) -> int:
        """Count elements in specification."""
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


# ==================== CONVENIENCE FUNCTIONS ====================

def generate_patent_diagram(
    prompt: str,
    output_path: str,
    api_key: str,
    quality: str = "high"
) -> str:
    """
    Quick function to generate a patent diagram.

    Args:
        prompt: Diagram description
        output_path: Where to save PPTX
        api_key: Anthropic API key
        quality: "high" or "fast"

    Returns:
        Path to generated file
    """
    pipeline = PatentDiagramPipeline(api_key)
    result = pipeline.generate(prompt, output_path, quality=quality)
    return result['output_path']
