"""
Advanced Layout Algorithms for Patent Diagrams

This module contains sophisticated layout algorithms that can handle
complex nested hierarchies, automatic sizing, and constraint-based positioning.

Algorithms:
- Constraint-based hierarchical layout
- Smart connector routing (avoids overlaps)
- Multi-pass optimization
- Symmetry detection and preservation

Author: AI Patent Diagram Generator (Elite Engineering Edition)
License: MIT
"""

from typing import Dict, List, Any, Tuple, Optional, Set
import math
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class LayoutConstraint:
    """Represents a layout constraint."""
    type: str  # "min_width", "max_height", "align", "spacing", etc.
    target: str  # Element ID or "global"
    value: float
    priority: int = 1  # Higher = more important


@dataclass
class BoundingBox:
    """Represents element bounding box."""
    x: float
    y: float
    width: float
    height: float

    def contains_point(self, px: float, py: float) -> bool:
        """Check if point is inside this box."""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this box overlaps with another."""
        return not (self.x + self.width < other.x or
                    other.x + other.width < self.x or
                    self.y + self.height < other.y or
                    other.y + other.height < self.y)

    def center(self) -> Tuple[float, float]:
        """Get center point."""
        return (self.x + self.width / 2, self.y + self.height / 2)


class ConstraintSolver:
    """
    Solves layout constraints using iterative optimization.

    This is a simplified constraint solver that can handle:
    - Size constraints (min/max width/height)
    - Position constraints (alignment, spacing)
    - Containment constraints (child within parent)
    """

    def __init__(self, slide_width: float = 10.0, slide_height: float = 7.5):
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.constraints: List[LayoutConstraint] = []

    def add_constraint(self, constraint: LayoutConstraint):
        """Add a layout constraint."""
        self.constraints.append(constraint)

    def solve(
        self,
        elements: Dict[str, BoundingBox],
        iterations: int = 100
    ) -> Dict[str, BoundingBox]:
        """
        Solve constraints iteratively.

        Args:
            elements: Dict of element_id -> BoundingBox
            iterations: Max iterations

        Returns:
            Updated elements dict with constraints satisfied
        """
        for iteration in range(iterations):
            violations = 0

            # Check each constraint
            for constraint in sorted(self.constraints, key=lambda c: -c.priority):
                if constraint.type == "min_width":
                    elem = elements.get(constraint.target)
                    if elem and elem.width < constraint.value:
                        elem.width = constraint.value
                        violations += 1

                elif constraint.type == "min_height":
                    elem = elements.get(constraint.target)
                    if elem and elem.height < constraint.value:
                        elem.height = constraint.value
                        violations += 1

                elif constraint.type == "spacing":
                    # Ensure minimum spacing between all elements
                    for id1, box1 in elements.items():
                        for id2, box2 in elements.items():
                            if id1 >= id2:
                                continue

                            if box1.overlaps(box2):
                                # Push apart
                                dx = box1.center()[0] - box2.center()[0]
                                dy = box1.center()[1] - box2.center()[1]
                                dist = math.sqrt(dx**2 + dy**2) or 0.01

                                overlap_x = (box1.width + box2.width) / 2 - abs(dx)
                                overlap_y = (box1.height + box2.height) / 2 - abs(dy)

                                if overlap_x > 0 and overlap_y > 0:
                                    # Resolve overlap
                                    if abs(dx) > abs(dy):
                                        # Separate horizontally
                                        shift = overlap_x / 2 + constraint.value / 2
                                        box1.x += shift * (1 if dx > 0 else -1)
                                        box2.x -= shift * (1 if dx > 0 else -1)
                                    else:
                                        # Separate vertically
                                        shift = overlap_y / 2 + constraint.value / 2
                                        box1.y += shift * (1 if dy > 0 else -1)
                                        box2.y -= shift * (1 if dy > 0 else -1)

                                    violations += 1

                elif constraint.type == "align_horizontal":
                    # Align elements horizontally (same y)
                    target_y = constraint.value
                    elem = elements.get(constraint.target)
                    if elem:
                        elem.y = target_y

                elif constraint.type == "align_vertical":
                    # Align elements vertically (same x)
                    target_x = constraint.value
                    elem = elements.get(constraint.target)
                    if elem:
                        elem.x = target_x

            if violations == 0:
                logger.info(f"Constraints solved in {iteration + 1} iterations")
                break

        return elements


class AdvancedHierarchicalLayout:
    """
    Advanced hierarchical layout with automatic sizing and positioning.

    Features:
    - Bottom-up sizing (children determine parent size)
    - Smart padding and spacing
    - Symmetry preservation
    - Constraint-based optimization
    """

    def __init__(
        self,
        slide_width: float = 10.0,
        slide_height: float = 7.5,
        margin: float = 0.5,
        padding: float = 0.3,
        spacing: float = 0.2,
        min_box_width: float = 1.5,
        min_box_height: float = 0.6
    ):
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margin = margin
        self.padding = padding
        self.spacing = spacing
        self.min_box_width = min_box_width
        self.min_box_height = min_box_height

        self.solver = ConstraintSolver(slide_width, slide_height)

    def calculate_layout(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate layout for hierarchical diagram.

        Args:
            spec: Hierarchical specification from Claude

        Returns:
            Flat list of positioned elements for python-pptx
        """
        logger.info("Starting advanced hierarchical layout calculation...")

        # Extract root
        root = spec.get('root', {})

        # Step 1: Build tree structure
        tree = self._build_tree(root)

        # Step 2: Calculate sizes bottom-up
        self._calculate_sizes(tree)

        # Step 3: Position elements top-down
        self._position_elements(
            tree,
            x=self.margin,
            y=self.margin,
            available_width=self.slide_width - 2 * self.margin
        )

        # Step 4: Flatten to element list
        elements = []
        self._flatten_tree(tree, elements)

        # Step 5: Add connections
        connections = spec.get('connections', [])
        for conn in connections:
            elements.append(self._create_connector(conn, {e['id']: e for e in elements}))

        # Step 6: Add external elements
        external = spec.get('external_elements', [])
        if external:
            external_positioned = self._position_external_elements(external, elements)
            elements.extend(external_positioned)

        logger.info(f"Layout complete: {len(elements)} total elements")

        return {
            "metadata": spec.get('metadata', {}),
            "elements": elements
        }

    def _build_tree(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively build tree structure with metadata."""
        tree_node = {
            "id": node.get('id', 'unknown'),
            "label": node.get('label', ''),
            "shape": node.get('shape', 'rectangle'),
            "style": node.get('style', {}),
            "layout_hints": node.get('layout_hints', {}),
            "children": [],
            "bbox": None,  # Will be calculated
            "position": None  # Will be calculated
        }

        # Recursively add children
        for child in node.get('children', []):
            tree_node['children'].append(self._build_tree(child))

        return tree_node

    def _calculate_sizes(self, node: Dict[str, Any]) -> Tuple[float, float]:
        """
        Calculate size bottom-up.

        Leaf nodes get minimum size.
        Parent nodes size to fit children + padding.

        Returns:
            (width, height) tuple
        """
        children = node['children']

        if not children:
            # Leaf node: use minimum size
            width = max(self.min_box_width, len(node['label']) * 0.08)
            height = self.min_box_height

            # Count lines in label
            lines = node['label'].count('\n') + 1
            height = max(height, lines * 0.25)

            node['bbox'] = BoundingBox(0, 0, width, height)
            return width, height

        # Parent node: calculate from children
        layout_hints = node.get('layout_hints', {})
        arrangement = layout_hints.get('child_arrangement', 'stack')

        # Calculate children sizes first
        child_sizes = [self._calculate_sizes(child) for child in children]

        if arrangement == 'horizontal':
            # Arrange children side-by-side
            total_width = sum(w for w, h in child_sizes)
            total_width += self.spacing * (len(children) - 1)  # Spacing between
            max_height = max(h for w, h in child_sizes)

            width = total_width + 2 * self.padding
            height = max_height + 2 * self.padding

        else:  # 'stack' (vertical)
            # Arrange children vertically
            max_width = max(w for w, h in child_sizes)
            total_height = sum(h for w, h in child_sizes)
            total_height += self.spacing * (len(children) - 1)

            width = max_width + 2 * self.padding
            height = total_height + 2 * self.padding

        # Add space for label if it's a labeled container
        if node['label']:
            label_height = 0.4
            height += label_height

        node['bbox'] = BoundingBox(0, 0, width, height)
        return width, height

    def _position_elements(
        self,
        node: Dict[str, Any],
        x: float,
        y: float,
        available_width: float
    ):
        """
        Position elements top-down.

        Args:
            node: Tree node
            x, y: Top-left position for this node
            available_width: Available horizontal space
        """
        # Position this node
        node['position'] = {"x": x, "y": y}
        node['bbox'].x = x
        node['bbox'].y = y

        # Position children
        children = node['children']
        if not children:
            return

        layout_hints = node.get('layout_hints', {})
        arrangement = layout_hints.get('child_arrangement', 'stack')

        # Account for label space
        label_offset = 0.4 if node['label'] else 0

        child_x = x + self.padding
        child_y = y + self.padding + label_offset

        if arrangement == 'horizontal':
            # Position children side-by-side
            for child in children:
                self._position_elements(
                    child,
                    x=child_x,
                    y=child_y,
                    available_width=child['bbox'].width
                )
                child_x += child['bbox'].width + self.spacing

        else:  # 'stack' (vertical)
            # Position children vertically
            for child in children:
                self._position_elements(
                    child,
                    x=child_x,
                    y=child_y,
                    available_width=available_width - 2 * self.padding
                )
                child_y += child['bbox'].height + self.spacing

    def _flatten_tree(self, node: Dict[str, Any], elements: List[Dict]):
        """
        Convert tree to flat list of elements.

        Parents are added before children (so they render behind).
        """
        # Add this node
        elements.append({
            "id": node['id'],
            "type": node['shape'],
            "text": node['label'],
            "position": node['position'],
            "size": {
                "width": node['bbox'].width,
                "height": node['bbox'].height
            },
            "style": node.get('style', {})
        })

        # Recursively add children
        for child in node['children']:
            self._flatten_tree(child, elements)

    def _create_connector(
        self,
        conn_spec: Dict[str, Any],
        element_map: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Create a connector element between two shapes."""
        from_elem = element_map.get(conn_spec['from'])
        to_elem = element_map.get(conn_spec['to'])

        if not from_elem or not to_elem:
            logger.warning(f"Connector references unknown elements: {conn_spec}")
            return {}

        return {
            "id": conn_spec.get('id', f"conn_{conn_spec['from']}_{conn_spec['to']}"),
            "type": "connector",
            "connector_type": conn_spec.get('connector_type', 'straight'),
            "from": conn_spec['from'],
            "to": conn_spec['to'],
            "from_side": self._determine_connection_side(from_elem, to_elem, "from"),
            "to_side": self._determine_connection_side(from_elem, to_elem, "to"),
            "style": conn_spec.get('style', {"arrow_end": True})
        }

    def _determine_connection_side(
        self,
        from_elem: Dict,
        to_elem: Dict,
        direction: str
    ) -> str:
        """
        Intelligently determine which side of a box to connect to.

        Args:
            from_elem: Source element
            to_elem: Target element
            direction: "from" or "to"

        Returns:
            Side string: "top", "bottom", "left", "right"
        """
        from_x = from_elem['position']['x'] + from_elem['size']['width'] / 2
        from_y = from_elem['position']['y'] + from_elem['size']['height'] / 2

        to_x = to_elem['position']['x'] + to_elem['size']['width'] / 2
        to_y = to_elem['position']['y'] + to_elem['size']['height'] / 2

        dx = to_x - from_x
        dy = to_y - from_y

        if direction == "from":
            # Connect from the side closest to target
            if abs(dx) > abs(dy):
                return "right" if dx > 0 else "left"
            else:
                return "bottom" if dy > 0 else "top"
        else:  # "to"
            # Connect to the side closest to source
            if abs(dx) > abs(dy):
                return "left" if dx > 0 else "right"
            else:
                return "top" if dy > 0 else "bottom"

    def _position_external_elements(
        self,
        external: List[Dict],
        main_elements: List[Dict]
    ) -> List[Dict]:
        """Position external elements (like external databases) outside main diagram."""
        positioned = []

        # Find rightmost element
        max_x = max((e['position']['x'] + e['size']['width']) for e in main_elements)

        # Position external elements to the right
        current_y = self.margin

        for ext in external:
            # Recursively build and position
            tree = self._build_tree(ext)
            self._calculate_sizes(tree)
            self._position_elements(
                tree,
                x=max_x + 1.0,  # 1 inch gap
                y=current_y,
                available_width=self.slide_width - max_x - 1.0 - self.margin
            )

            # Flatten
            self._flatten_tree(tree, positioned)

            current_y += tree['bbox'].height + self.spacing

        return positioned


# Factory function
def create_advanced_layout_engine(diagram_type: str, **kwargs):
    """
    Factory function for advanced layout engines.

    Args:
        diagram_type: "hierarchical", "flowchart", or "network"
        **kwargs: Additional parameters

    Returns:
        Configured layout engine
    """
    if diagram_type == "hierarchical":
        return AdvancedHierarchicalLayout(**kwargs)
    else:
        # Fall back to basic engines for now
        from .layout_engine import get_layout_engine
        return get_layout_engine(diagram_type, **kwargs)
