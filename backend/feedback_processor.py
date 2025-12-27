"""
Human Feedback Processor with Screenshot Analysis

This module processes human feedback including:
1. Text feedback parsing
2. Screenshot analysis using Claude Vision
3. Issue extraction and categorization
4. Fix suggestion generation

Author: AI Patent Diagram Generator
License: MIT
"""

import logging
import base64
import json
import re
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import anthropic

from conversation_memory import (
    ConversationMemory,
    HumanFeedback,
    FeedbackType,
    memory_manager
)

logger = logging.getLogger(__name__)


class IssueCategory(Enum):
    """Categories of diagram issues that can be identified."""
    LAYOUT = "layout"           # Position, spacing, alignment issues
    CONNECTOR = "connector"     # Arrow routing, connection issues
    TEXT = "text"               # Label, text content issues
    SHAPE = "shape"             # Wrong shape type, size issues
    MISSING = "missing"         # Missing elements
    EXTRA = "extra"             # Unnecessary elements
    STYLE = "style"             # Color, border, styling issues
    GENERAL = "general"         # General feedback


@dataclass
class IdentifiedIssue:
    """A specific issue identified from feedback."""
    category: IssueCategory
    description: str
    severity: str = "medium"  # low, medium, high
    affected_elements: List[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "description": self.description,
            "severity": self.severity,
            "affected_elements": self.affected_elements,
            "suggested_fix": self.suggested_fix
        }


class FeedbackProcessor:
    """
    Processes human feedback to extract actionable issues.

    Capabilities:
    1. Analyze screenshots using Claude Vision
    2. Parse text feedback for specific issues
    3. Combine screenshot + text analysis
    4. Generate targeted fix suggestions
    """

    # System prompt for screenshot analysis
    SCREENSHOT_ANALYSIS_PROMPT = """You are analyzing a diagram screenshot to identify issues.

The user has uploaded a screenshot of a diagram and may have feedback about what's wrong.

Your task is to:
1. Describe what you see in the diagram
2. Identify any visual issues like:
   - Overlapping boxes
   - Arrows going through shapes
   - Misaligned elements
   - Text that's cut off or hard to read
   - Missing connections
   - Wrong shape types
   - Poor layout/arrangement
3. Note which specific elements have problems (if you can identify them)

Output your analysis in this JSON format:
{
    "diagram_description": "Brief description of what the diagram shows",
    "element_count": "Approximate number of shapes",
    "identified_issues": [
        {
            "category": "layout|connector|text|shape|missing|extra|style",
            "description": "What's wrong",
            "severity": "low|medium|high",
            "location": "Where in the diagram (top-left, center, etc.)"
        }
    ],
    "overall_quality": "good|acceptable|poor",
    "key_recommendations": ["List of main fixes needed"]
}

Be specific and actionable in your analysis."""

    # Keywords for issue categorization
    ISSUE_KEYWORDS = {
        IssueCategory.LAYOUT: [
            "overlap", "overlapping", "position", "move", "align", "spacing",
            "too close", "too far", "arrangement", "layout", "misaligned"
        ],
        IssueCategory.CONNECTOR: [
            "arrow", "connector", "connection", "line", "link", "route",
            "path", "crosses", "crossing", "through", "elbow", "straight"
        ],
        IssueCategory.TEXT: [
            "text", "label", "title", "name", "word", "typo", "spelling",
            "rename", "change text", "wrong name"
        ],
        IssueCategory.SHAPE: [
            "shape", "box", "diamond", "rectangle", "circle", "size",
            "bigger", "smaller", "type", "wrong shape"
        ],
        IssueCategory.MISSING: [
            "missing", "add", "need", "should have", "forgot", "where is",
            "no connection", "not connected"
        ],
        IssueCategory.EXTRA: [
            "remove", "delete", "extra", "unnecessary", "don't need",
            "shouldn't be", "wrong"
        ],
        IssueCategory.STYLE: [
            "color", "border", "thick", "thin", "style", "transparent",
            "fill", "background"
        ]
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

        if not self.client:
            logger.warning("[FeedbackProcessor] No API key - screenshot analysis disabled")

    async def process_feedback(
        self,
        session_id: str,
        feedback_text: str,
        screenshot_base64: Optional[str] = None
    ) -> Tuple[HumanFeedback, List[IdentifiedIssue]]:
        """
        Process human feedback and extract issues.

        Args:
            session_id: Session identifier
            feedback_text: User's text feedback
            screenshot_base64: Base64-encoded screenshot (optional)

        Returns:
            Tuple of (HumanFeedback object, list of identified issues)
        """
        logger.info(f"[FeedbackProcessor] Processing feedback for session {session_id}")

        # Get conversation memory
        memory = memory_manager.get_or_create(session_id)

        # Analyze screenshot if provided
        screenshot_analysis = None
        if screenshot_base64 and self.client:
            logger.info("[FeedbackProcessor] Analyzing screenshot with Claude Vision...")
            screenshot_analysis = await self._analyze_screenshot(
                screenshot_base64,
                feedback_text
            )

        # Parse text feedback
        text_issues = self._parse_text_feedback(feedback_text)

        # Combine screenshot and text issues
        all_issues = self._combine_issues(text_issues, screenshot_analysis)

        # Create feedback object
        feedback = HumanFeedback(
            feedback_text=feedback_text,
            screenshot_base64=screenshot_base64,
            screenshot_analysis=json.dumps(screenshot_analysis) if screenshot_analysis else None,
            feedback_type=FeedbackType.SCREENSHOT_WITH_TEXT if screenshot_base64 else FeedbackType.TEXT_ONLY,
            identified_issues=[issue.description for issue in all_issues],
            suggested_fixes=[issue.suggested_fix for issue in all_issues if issue.suggested_fix]
        )

        # Add to memory
        memory.add_feedback(
            feedback_text=feedback_text,
            screenshot_base64=screenshot_base64,
            screenshot_analysis=feedback.screenshot_analysis
        )

        # Also add as a user message in conversation
        memory.add_user_message(
            content=feedback_text,
            has_image=screenshot_base64 is not None,
            image_analysis=feedback.screenshot_analysis
        )

        logger.info(f"[FeedbackProcessor] Identified {len(all_issues)} issues")
        return feedback, all_issues

    async def _analyze_screenshot(
        self,
        screenshot_base64: str,
        user_feedback: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a screenshot using Claude Vision.

        Args:
            screenshot_base64: Base64-encoded image
            user_feedback: Optional user text to provide context

        Returns:
            Dictionary with analysis results
        """
        try:
            # Prepare the prompt
            prompt = self.SCREENSHOT_ANALYSIS_PROMPT
            if user_feedback:
                prompt += f"\n\nThe user's feedback about this diagram: \"{user_feedback}\""
                prompt += "\n\nPay special attention to issues the user mentions."

            # Determine image type
            image_type = "image/png"
            if screenshot_base64.startswith("/9j/"):
                image_type = "image/jpeg"

            # Call Claude Vision
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250514",  # Vision-capable model
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_type,
                                    "data": screenshot_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Parse the response
            response_text = response.content[0].text

            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    analysis = json.loads(json_match.group())
                    logger.info(f"[FeedbackProcessor] Screenshot analysis: {analysis.get('overall_quality', 'unknown')} quality")
                    return analysis
                except json.JSONDecodeError:
                    pass

            # Fallback: return raw analysis
            return {
                "diagram_description": response_text,
                "identified_issues": [],
                "overall_quality": "unknown",
                "key_recommendations": []
            }

        except Exception as e:
            logger.error(f"[FeedbackProcessor] Screenshot analysis failed: {e}")
            return None

    def _parse_text_feedback(self, feedback_text: str) -> List[IdentifiedIssue]:
        """
        Parse text feedback to identify specific issues.

        Uses keyword matching and pattern recognition.
        """
        issues = []
        feedback_lower = feedback_text.lower()

        # Check for each category
        for category, keywords in self.ISSUE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in feedback_lower:
                    # Extract the sentence containing the keyword
                    sentences = re.split(r'[.!?]', feedback_text)
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            issue = IdentifiedIssue(
                                category=category,
                                description=sentence.strip(),
                                severity=self._estimate_severity(sentence),
                                suggested_fix=self._suggest_fix(category, sentence)
                            )
                            # Avoid duplicates
                            if not any(i.description == issue.description for i in issues):
                                issues.append(issue)
                    break

        # If no specific issues found, create a general issue
        if not issues and feedback_text.strip():
            issues.append(IdentifiedIssue(
                category=IssueCategory.GENERAL,
                description=feedback_text,
                severity="medium"
            ))

        return issues

    def _estimate_severity(self, text: str) -> str:
        """Estimate issue severity based on language."""
        text_lower = text.lower()

        high_severity_words = ["wrong", "broken", "can't", "doesn't work", "error", "major"]
        low_severity_words = ["minor", "small", "slightly", "could", "maybe", "prefer"]

        if any(word in text_lower for word in high_severity_words):
            return "high"
        elif any(word in text_lower for word in low_severity_words):
            return "low"
        return "medium"

    def _suggest_fix(self, category: IssueCategory, description: str) -> Optional[str]:
        """Generate a fix suggestion based on the issue category."""
        suggestions = {
            IssueCategory.LAYOUT: "Reposition the affected elements to improve spacing and alignment",
            IssueCategory.CONNECTOR: "Change the connector routing or type (straight vs elbow)",
            IssueCategory.TEXT: "Update the text content as specified",
            IssueCategory.SHAPE: "Change the shape type or resize as needed",
            IssueCategory.MISSING: "Add the missing element and its connections",
            IssueCategory.EXTRA: "Remove the unnecessary element",
            IssueCategory.STYLE: "Update the styling (colors, borders) as specified"
        }
        return suggestions.get(category)

    def _combine_issues(
        self,
        text_issues: List[IdentifiedIssue],
        screenshot_analysis: Optional[Dict[str, Any]]
    ) -> List[IdentifiedIssue]:
        """
        Combine issues from text parsing and screenshot analysis.

        Prioritizes screenshot analysis when available since it's more accurate.
        """
        combined = list(text_issues)

        if screenshot_analysis:
            for issue_data in screenshot_analysis.get("identified_issues", []):
                try:
                    category = IssueCategory(issue_data.get("category", "general"))
                except ValueError:
                    category = IssueCategory.GENERAL

                issue = IdentifiedIssue(
                    category=category,
                    description=issue_data.get("description", ""),
                    severity=issue_data.get("severity", "medium"),
                    suggested_fix=self._suggest_fix(category, issue_data.get("description", ""))
                )

                # Check if this is a new issue
                is_duplicate = any(
                    i.description.lower() in issue.description.lower() or
                    issue.description.lower() in i.description.lower()
                    for i in combined
                )

                if not is_duplicate and issue.description:
                    combined.append(issue)

            # Add key recommendations as issues
            for rec in screenshot_analysis.get("key_recommendations", []):
                if rec and not any(rec.lower() in i.description.lower() for i in combined):
                    combined.append(IdentifiedIssue(
                        category=IssueCategory.GENERAL,
                        description=rec,
                        severity="medium"
                    ))

        return combined


class FeedbackAwareRefiner:
    """
    Refines diagrams based on human feedback.

    Uses conversation memory to understand context and
    applies targeted fixes based on identified issues.
    """

    REFINEMENT_SYSTEM_PROMPT = """You are a diagram refinement assistant. Your task is to modify a diagram specification based on human feedback.

You will receive:
1. The current diagram specification (nodes and edges)
2. Human feedback about what needs to change
3. Screenshot analysis (if available)
4. Conversation history for context

Your response must be a VALID JSON diagram specification with the same structure as the input, but with the requested changes applied.

Rules:
1. Only modify what the user asks to change
2. Keep all other elements exactly as they are
3. Maintain all existing connections unless specifically asked to change them
4. Use position hints (like "below:nodeId") instead of exact coordinates
5. Return ONLY valid JSON - no explanations before or after

Output format:
{
    "metadata": {...},
    "nodes": [...],
    "edges": [...]
}"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    async def refine_diagram(
        self,
        session_id: str,
        feedback: HumanFeedback,
        issues: List[IdentifiedIssue]
    ) -> Dict[str, Any]:
        """
        Refine a diagram based on human feedback.

        Args:
            session_id: Session identifier
            feedback: Human feedback object
            issues: List of identified issues

        Returns:
            Refined V2 diagram specification
        """
        memory = memory_manager.get(session_id)
        if not memory:
            raise ValueError(f"No memory found for session {session_id}")

        latest_version = memory.get_latest_diagram_version()
        if not latest_version:
            raise ValueError(f"No diagram found for session {session_id}")

        # Build the refinement prompt
        prompt = self._build_refinement_prompt(
            memory=memory,
            feedback=feedback,
            issues=issues,
            current_spec=latest_version.v2_spec
        )

        logger.info(f"[Refiner] Refining diagram for session {session_id}")
        logger.info(f"[Refiner] Issues to address: {len(issues)}")

        try:
            # Call Claude for refinement
            response = self.client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250514"),
                max_tokens=8000,
                system=self.REFINEMENT_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.content[0].text

            # Parse the JSON response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                refined_spec = json.loads(json_match.group())

                # Validate the response has required fields
                if "nodes" in refined_spec and "edges" in refined_spec:
                    logger.info(f"[Refiner] Successfully refined diagram: {len(refined_spec['nodes'])} nodes")

                    # Add assistant message to memory
                    memory.add_assistant_message(
                        content=f"Refined the diagram based on your feedback. Made {len(issues)} changes.",
                        metadata={"refined_spec": refined_spec}
                    )

                    return refined_spec

            raise ValueError("Claude did not return a valid diagram specification")

        except json.JSONDecodeError as e:
            logger.error(f"[Refiner] Failed to parse Claude response: {e}")
            raise ValueError(f"Failed to parse refined diagram: {e}")
        except Exception as e:
            logger.error(f"[Refiner] Refinement failed: {e}")
            raise

    def _build_refinement_prompt(
        self,
        memory: ConversationMemory,
        feedback: HumanFeedback,
        issues: List[IdentifiedIssue],
        current_spec: Dict[str, Any]
    ) -> str:
        """Build the prompt for diagram refinement."""
        parts = []

        # Part 1: Current diagram specification
        parts.append("## Current Diagram Specification")
        parts.append("```json")
        parts.append(json.dumps(current_spec, indent=2))
        parts.append("```")

        # Part 2: Human feedback
        parts.append("\n## Human Feedback")
        parts.append(f"User says: \"{feedback.feedback_text}\"")

        # Part 3: Screenshot analysis (if available)
        if feedback.screenshot_analysis:
            parts.append("\n## Screenshot Analysis")
            try:
                analysis = json.loads(feedback.screenshot_analysis)
                parts.append(f"Overall quality: {analysis.get('overall_quality', 'unknown')}")
                parts.append(f"Description: {analysis.get('diagram_description', 'N/A')}")

                if analysis.get('key_recommendations'):
                    parts.append("\nKey recommendations:")
                    for rec in analysis['key_recommendations']:
                        parts.append(f"  - {rec}")
            except:
                parts.append(feedback.screenshot_analysis)

        # Part 4: Identified issues
        if issues:
            parts.append("\n## Identified Issues to Fix")
            for i, issue in enumerate(issues, 1):
                parts.append(f"{i}. [{issue.category.value}] {issue.description}")
                if issue.suggested_fix:
                    parts.append(f"   Suggested fix: {issue.suggested_fix}")

        # Part 5: Conversation context summary
        context = memory.get_context_for_llm()
        if context.get("diagram_history", {}).get("total_versions", 0) > 1:
            parts.append("\n## Previous Context")
            parts.append(f"This is version {context['diagram_history']['total_versions']} of the diagram.")
            parts.append("Previous versions:")
            for v in context['diagram_history'].get('versions', [])[-3:]:
                parts.append(f"  - {v['prompt'][:50]}...")

        # Part 6: Instructions
        parts.append("\n## Instructions")
        parts.append("Please modify the diagram specification to address the issues above.")
        parts.append("Return ONLY the complete modified JSON specification.")

        return "\n".join(parts)


# Global instances
feedback_processor = FeedbackProcessor()
feedback_refiner = FeedbackAwareRefiner()
