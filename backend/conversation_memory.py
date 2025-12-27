"""
Conversation Memory Manager for Human Feedback Loop

This module manages the conversation context between the user and the LLM,
enabling iterative diagram refinement based on human feedback.

Key Features:
1. Memory buffer for conversation history (no vector DB needed)
2. Screenshot analysis with Claude Vision
3. Context-aware diagram refinement
4. Session-based memory management

Author: AI Patent Diagram Generator
License: MIT
"""

import logging
import base64
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FeedbackType(Enum):
    """Types of human feedback."""
    TEXT_ONLY = "text_only"
    SCREENSHOT_WITH_TEXT = "screenshot_with_text"
    SCREENSHOT_ONLY = "screenshot_only"


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # For screenshot feedback
    has_image: bool = False
    image_analysis: Optional[str] = None


@dataclass
class DiagramVersion:
    """A version of the diagram in the conversation."""
    version_id: str
    v2_spec: Dict[str, Any]  # Claude's logical structure
    v1_spec: Dict[str, Any]  # Layout engine output
    validation_issues: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    prompt: str = ""
    is_refinement: bool = False
    parent_version_id: Optional[str] = None


@dataclass
class HumanFeedback:
    """Human feedback with optional screenshot."""
    feedback_text: str
    screenshot_base64: Optional[str] = None
    screenshot_analysis: Optional[str] = None
    feedback_type: FeedbackType = FeedbackType.TEXT_ONLY
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Extracted issues from feedback
    identified_issues: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)


class ConversationMemory:
    """
    Memory buffer for maintaining conversation context with the LLM.

    This class keeps track of:
    1. All messages in the conversation
    2. All diagram versions generated
    3. Human feedback with screenshot analysis
    4. Context needed for intelligent refinement

    No vector database needed - uses a simple in-memory buffer
    that gets summarized when needed.
    """

    # Maximum messages to keep in full detail
    MAX_DETAILED_MESSAGES = 20

    # Maximum diagram versions to keep full specs
    MAX_FULL_VERSIONS = 5

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[ConversationMessage] = []
        self.diagram_versions: List[DiagramVersion] = []
        self.feedback_history: List[HumanFeedback] = []
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

        # Summary of older context (when messages exceed MAX_DETAILED_MESSAGES)
        self.context_summary: Optional[str] = None

        logger.info(f"[Memory] Created new conversation memory for session {session_id}")

    def add_user_message(
        self,
        content: str,
        has_image: bool = False,
        image_analysis: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Add a user message to the conversation."""
        message = ConversationMessage(
            role=MessageRole.USER,
            content=content,
            has_image=has_image,
            image_analysis=image_analysis,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.utcnow()

        # Manage memory size
        self._maybe_summarize_old_context()

        logger.info(f"[Memory] Added user message: {content[:50]}...")
        return message

    def add_assistant_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Add an assistant message to the conversation."""
        message = ConversationMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.utcnow()

        logger.info(f"[Memory] Added assistant message: {content[:50]}...")
        return message

    def add_diagram_version(
        self,
        version_id: str,
        v2_spec: Dict[str, Any],
        v1_spec: Dict[str, Any],
        validation_issues: List[Dict[str, Any]],
        prompt: str,
        is_refinement: bool = False,
        parent_version_id: Optional[str] = None
    ) -> DiagramVersion:
        """Add a new diagram version to the history."""
        version = DiagramVersion(
            version_id=version_id,
            v2_spec=v2_spec,
            v1_spec=v1_spec,
            validation_issues=validation_issues,
            prompt=prompt,
            is_refinement=is_refinement,
            parent_version_id=parent_version_id
        )
        self.diagram_versions.append(version)

        # Keep only the most recent full versions
        if len(self.diagram_versions) > self.MAX_FULL_VERSIONS:
            # Summarize old versions
            self._summarize_old_versions()

        logger.info(f"[Memory] Added diagram version {version_id}, total versions: {len(self.diagram_versions)}")
        return version

    def add_feedback(
        self,
        feedback_text: str,
        screenshot_base64: Optional[str] = None,
        screenshot_analysis: Optional[str] = None
    ) -> HumanFeedback:
        """Add human feedback to the history."""
        feedback_type = FeedbackType.TEXT_ONLY
        if screenshot_base64 and feedback_text:
            feedback_type = FeedbackType.SCREENSHOT_WITH_TEXT
        elif screenshot_base64:
            feedback_type = FeedbackType.SCREENSHOT_ONLY

        feedback = HumanFeedback(
            feedback_text=feedback_text,
            screenshot_base64=screenshot_base64,
            screenshot_analysis=screenshot_analysis,
            feedback_type=feedback_type
        )
        self.feedback_history.append(feedback)

        logger.info(f"[Memory] Added feedback ({feedback_type.value}): {feedback_text[:50]}...")
        return feedback

    def get_latest_diagram_version(self) -> Optional[DiagramVersion]:
        """Get the most recent diagram version."""
        if not self.diagram_versions:
            return None
        return self.diagram_versions[-1]

    def get_context_for_llm(self, include_full_history: bool = False) -> Dict[str, Any]:
        """
        Build context object to send to LLM for refinement.

        This is the key method that prepares all relevant context
        for the LLM to understand what's happened and what needs fixing.
        """
        context = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add context summary if we have one (from older messages)
        if self.context_summary:
            context["previous_context_summary"] = self.context_summary

        # Add recent conversation messages
        recent_messages = self._get_recent_messages()
        context["recent_conversation"] = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "has_image": msg.has_image,
                "image_analysis": msg.image_analysis
            }
            for msg in recent_messages
        ]

        # Add current diagram state
        latest_version = self.get_latest_diagram_version()
        if latest_version:
            context["current_diagram"] = {
                "version_id": latest_version.version_id,
                "original_prompt": latest_version.prompt,
                "node_count": len(latest_version.v2_spec.get("nodes", [])),
                "edge_count": len(latest_version.v2_spec.get("edges", [])),
                "validation_issues": latest_version.validation_issues,
                "v2_spec": latest_version.v2_spec if include_full_history else self._summarize_spec(latest_version.v2_spec)
            }

        # Add recent feedback
        if self.feedback_history:
            latest_feedback = self.feedback_history[-1]
            context["latest_feedback"] = {
                "type": latest_feedback.feedback_type.value,
                "text": latest_feedback.feedback_text,
                "screenshot_analysis": latest_feedback.screenshot_analysis,
                "identified_issues": latest_feedback.identified_issues
            }

        # Add diagram history summary
        context["diagram_history"] = {
            "total_versions": len(self.diagram_versions),
            "versions": [
                {
                    "version_id": v.version_id,
                    "prompt": v.prompt[:100] + "..." if len(v.prompt) > 100 else v.prompt,
                    "is_refinement": v.is_refinement,
                    "issue_count": len(v.validation_issues)
                }
                for v in self.diagram_versions[-5:]  # Last 5 versions
            ]
        }

        return context

    def build_refinement_prompt(
        self,
        feedback: HumanFeedback,
        include_screenshot_analysis: bool = True
    ) -> str:
        """
        Build a prompt for the LLM to refine the diagram based on feedback.

        This combines:
        1. The original diagram context
        2. The human feedback (text + screenshot analysis)
        3. Instructions for targeted refinement
        """
        latest_version = self.get_latest_diagram_version()

        prompt_parts = []

        # Section 1: Current Context
        prompt_parts.append("## Current Diagram Context")
        if latest_version:
            prompt_parts.append(f"Original prompt: {latest_version.prompt}")
            prompt_parts.append(f"Current nodes: {len(latest_version.v2_spec.get('nodes', []))}")
            prompt_parts.append(f"Current edges: {len(latest_version.v2_spec.get('edges', []))}")

            if latest_version.validation_issues:
                prompt_parts.append("\nExisting validation issues:")
                for issue in latest_version.validation_issues[:5]:
                    prompt_parts.append(f"  - [{issue.get('severity', 'unknown')}] {issue.get('message', '')}")

        # Section 2: Human Feedback
        prompt_parts.append("\n## Human Feedback")
        prompt_parts.append(f"User says: {feedback.feedback_text}")

        # Section 3: Screenshot Analysis (if available)
        if include_screenshot_analysis and feedback.screenshot_analysis:
            prompt_parts.append("\n## Screenshot Analysis")
            prompt_parts.append("The user uploaded a screenshot of the diagram. Here's what was observed:")
            prompt_parts.append(feedback.screenshot_analysis)

        # Section 4: Identified Issues
        if feedback.identified_issues:
            prompt_parts.append("\n## Identified Issues")
            for i, issue in enumerate(feedback.identified_issues, 1):
                prompt_parts.append(f"{i}. {issue}")

        # Section 5: Instructions
        prompt_parts.append("\n## Your Task")
        prompt_parts.append("Based on the human feedback and screenshot analysis, refine the diagram specification.")
        prompt_parts.append("Focus on fixing the specific issues mentioned.")
        prompt_parts.append("Keep all other elements unchanged unless they need adjustment to fix the issues.")

        return "\n".join(prompt_parts)

    def _get_recent_messages(self, count: int = 10) -> List[ConversationMessage]:
        """Get the most recent messages."""
        return self.messages[-count:] if len(self.messages) > count else self.messages

    def _maybe_summarize_old_context(self):
        """Summarize old messages when we exceed the limit."""
        if len(self.messages) > self.MAX_DETAILED_MESSAGES:
            # Keep the last MAX_DETAILED_MESSAGES messages
            old_messages = self.messages[:-self.MAX_DETAILED_MESSAGES]

            # Create summary of old messages
            summary_parts = [
                f"Previous conversation summary ({len(old_messages)} messages):",
            ]

            for msg in old_messages:
                role = msg.role.value
                content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                if msg.has_image:
                    content_preview += " [with screenshot]"
                summary_parts.append(f"  - {role}: {content_preview}")

            # Update context summary
            if self.context_summary:
                self.context_summary += "\n" + "\n".join(summary_parts)
            else:
                self.context_summary = "\n".join(summary_parts)

            # Trim old messages
            self.messages = self.messages[-self.MAX_DETAILED_MESSAGES:]

            logger.info(f"[Memory] Summarized {len(old_messages)} old messages")

    def _summarize_old_versions(self):
        """Summarize old diagram versions to save memory."""
        if len(self.diagram_versions) > self.MAX_FULL_VERSIONS:
            # Keep only summaries of old versions
            old_versions = self.diagram_versions[:-self.MAX_FULL_VERSIONS]

            for version in old_versions:
                # Replace full specs with summaries
                version.v1_spec = self._summarize_spec(version.v1_spec)
                version.v2_spec = self._summarize_spec(version.v2_spec)

            logger.info(f"[Memory] Summarized {len(old_versions)} old diagram versions")

    def _summarize_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of a diagram spec."""
        return {
            "_summarized": True,
            "metadata": spec.get("metadata", {}),
            "node_count": len(spec.get("nodes", spec.get("elements", []))),
            "edge_count": len(spec.get("edges", [])),
            "node_types": list(set(
                n.get("type", "unknown")
                for n in spec.get("nodes", spec.get("elements", []))
            ))
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the conversation memory to a dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": len(self.messages),
            "diagram_version_count": len(self.diagram_versions),
            "feedback_count": len(self.feedback_history),
            "context_summary": self.context_summary
        }


class MemoryManager:
    """
    Manages conversation memories across multiple sessions.

    In production, this would be backed by Redis or a database.
    For now, it's an in-memory store.
    """

    def __init__(self):
        self.memories: Dict[str, ConversationMemory] = {}
        logger.info("[MemoryManager] Initialized")

    def get_or_create(self, session_id: str) -> ConversationMemory:
        """Get existing memory or create a new one."""
        if session_id not in self.memories:
            self.memories[session_id] = ConversationMemory(session_id)
        return self.memories[session_id]

    def get(self, session_id: str) -> Optional[ConversationMemory]:
        """Get memory for a session (returns None if not found)."""
        return self.memories.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete memory for a session."""
        if session_id in self.memories:
            del self.memories[session_id]
            logger.info(f"[MemoryManager] Deleted memory for session {session_id}")
            return True
        return False

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        cutoff = datetime.utcnow()
        to_delete = []

        for session_id, memory in self.memories.items():
            age = (cutoff - memory.last_activity).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(session_id)

        for session_id in to_delete:
            del self.memories[session_id]

        if to_delete:
            logger.info(f"[MemoryManager] Cleaned up {len(to_delete)} old sessions")

        return len(to_delete)


# Global memory manager instance
memory_manager = MemoryManager()
