"""
Intelligent Diagram Validation Agent

This module validates generated diagrams with REASONING capabilities:
1. No overlapping shapes
2. All connectors reference valid shapes
3. All shapes are within slide bounds
4. Minimum spacing is maintained
5. **NEW: Connector path analysis - detects if connectors cross shapes**
6. **NEW: Smart connector type selection (straight vs elbow)**
7. **NEW: Reasoning about fixes and alternatives**

The validation loop can retry layout and REASON about what needs to change.

Author: AI Patent Diagram Generator
License: MIT
"""

import logging
import math
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectorType(Enum):
    """Types of connectors available."""
    STRAIGHT = "straight"
    ELBOW = "elbow"
    CURVE = "curve"


@dataclass
class ValidationIssue:
    """Represents a single validation issue with reasoning."""
    issue_type: str  # 'overlap', 'missing_connection', 'out_of_bounds', 'blocked_path', 'bad_routing'
    severity: str    # 'error', 'warning'
    message: str
    elements: List[str]  # IDs of affected elements
    suggestion: Optional[str] = None
    fix_action: Optional[Dict[str, Any]] = None  # Specific fix to apply


@dataclass
class BoundingBox:
    """Represents a shape's bounding box for collision detection."""
    x: float
    y: float
    width: float
    height: float
    id: str = ""

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def contains_point(self, px: float, py: float, margin: float = 0.05) -> bool:
        """Check if a point is inside this box (with margin)."""
        return (self.left - margin <= px <= self.right + margin and
                self.top - margin <= py <= self.bottom + margin)

    def overlaps(self, other: 'BoundingBox', margin: float = 0.05) -> bool:
        """Check if this box overlaps with another."""
        return not (
            self.right + margin < other.left or
            other.right + margin < self.left or
            self.bottom + margin < other.top or
            other.bottom + margin < self.top
        )


@dataclass
class ConnectorPath:
    """Represents a connector's path for analysis."""
    id: str
    from_id: str
    to_id: str
    from_point: Tuple[float, float]  # (x, y) start point
    to_point: Tuple[float, float]    # (x, y) end point
    connector_type: str = "straight"
    crosses_shapes: List[str] = field(default_factory=list)


class DiagramValidator:
    """
    Intelligent validator that REASONS about diagram quality.

    Key capabilities:
    - Detects connector paths that cross shapes
    - Suggests elbow connectors when straight lines won't work
    - Validates visual quality, not just data integrity
    """

    # Slide dimensions (inches)
    SLIDE_WIDTH = 10.0
    SLIDE_HEIGHT = 7.5
    MARGIN = 0.3

    # Minimum spacing between shapes (inches)
    MIN_SPACING = 0.1

    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.shapes: Dict[str, BoundingBox] = {}
        self.connectors: List[ConnectorPath] = []

    def validate(self, spec: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Run all validation checks including INTELLIGENT path analysis.

        Args:
            spec: V1 diagram specification with elements array

        Returns:
            List of validation issues with reasoning and fix suggestions
        """
        self.issues = []
        self.shapes = {}
        self.connectors = []

        elements = spec.get('elements', [])
        shape_elements = [e for e in elements if e.get('type') != 'connector']
        connector_elements = [e for e in elements if e.get('type') == 'connector']

        logger.info(f"Validating diagram with {len(shape_elements)} shapes and {len(connector_elements)} connectors")

        # Build shape registry for path analysis
        self._build_shape_registry(shape_elements)

        # Run checks
        self._check_overlaps(shape_elements)
        self._check_bounds(shape_elements)
        self._check_connectors(connector_elements, shape_elements)
        self._check_spacing(shape_elements)

        # NEW: Intelligent connector path analysis
        self._analyze_connector_paths(connector_elements)

        # Log results
        errors = [i for i in self.issues if i.severity == 'error']
        warnings = [i for i in self.issues if i.severity == 'warning']

        if errors:
            logger.warning(f"Validation found {len(errors)} errors and {len(warnings)} warnings")
            for error in errors:
                logger.warning(f"  [{error.issue_type}] {error.message}")
                if error.suggestion:
                    logger.info(f"    Suggestion: {error.suggestion}")
        else:
            logger.info(f"Validation passed with {len(warnings)} warnings")

        return self.issues

    def _build_shape_registry(self, shapes: List[Dict[str, Any]]) -> None:
        """Build a registry of shape bounding boxes for path analysis."""
        for shape in shapes:
            shape_id = shape.get('id', '')
            pos = shape.get('position', {})
            size = shape.get('size', {})

            self.shapes[shape_id] = BoundingBox(
                x=pos.get('x', 0),
                y=pos.get('y', 0),
                width=size.get('width', 1),
                height=size.get('height', 1),
                id=shape_id
            )

    def _analyze_connector_paths(self, connectors: List[Dict[str, Any]]) -> None:
        """
        INTELLIGENT: Analyze each connector's path to detect crossings.

        This is the KEY missing piece - we check if a straight line connector
        would pass through any other shapes.
        """
        for connector in connectors:
            conn_id = connector.get('id', 'unknown')
            from_id = connector.get('from')
            to_id = connector.get('to')
            connector_type = connector.get('connector_type', 'straight')

            if not from_id or not to_id:
                continue

            from_shape = self.shapes.get(from_id)
            to_shape = self.shapes.get(to_id)

            if not from_shape or not to_shape:
                continue

            # Calculate connection points (center to center for analysis)
            from_point = (from_shape.center_x, from_shape.center_y)
            to_point = (to_shape.center_x, to_shape.center_y)

            # Check if straight line crosses any OTHER shapes
            crossed_shapes = self._find_shapes_crossed_by_line(
                from_point, to_point,
                exclude_ids={from_id, to_id}
            )

            if crossed_shapes:
                # This is a problem! The connector crosses other shapes
                crossed_names = ', '.join(crossed_shapes)

                self.issues.append(ValidationIssue(
                    issue_type='blocked_path',
                    severity='error',
                    message=f"Connector '{conn_id}' ({from_id} -> {to_id}) crosses shapes: {crossed_names}",
                    elements=[conn_id] + crossed_shapes,
                    suggestion=f"Use elbow connector to route around {crossed_names}",
                    fix_action={
                        'action': 'change_connector_type',
                        'connector_id': conn_id,
                        'new_type': 'elbow'
                    }
                ))

            # Check if shapes are not aligned and might need elbow
            if connector_type == 'straight':
                needs_elbow = self._should_use_elbow(from_shape, to_shape)
                if needs_elbow and not crossed_shapes:
                    # Not an error, but a suggestion
                    self.issues.append(ValidationIssue(
                        issue_type='bad_routing',
                        severity='warning',
                        message=f"Connector '{conn_id}' could use elbow routing for cleaner appearance",
                        elements=[conn_id],
                        suggestion="Consider using elbow connector for better visual flow",
                        fix_action={
                            'action': 'change_connector_type',
                            'connector_id': conn_id,
                            'new_type': 'elbow'
                        }
                    ))

    def _find_shapes_crossed_by_line(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        exclude_ids: Set[str]
    ) -> List[str]:
        """
        Find all shapes that a straight line from p1 to p2 would cross.

        Uses line-rectangle intersection algorithm.
        """
        crossed = []

        for shape_id, box in self.shapes.items():
            if shape_id in exclude_ids:
                continue

            if self._line_intersects_box(p1, p2, box):
                crossed.append(shape_id)

        return crossed

    def _line_intersects_box(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        box: BoundingBox
    ) -> bool:
        """
        Check if a line segment intersects a bounding box.

        Uses Cohen-Sutherland style algorithm.
        """
        x1, y1 = p1
        x2, y2 = p2

        # Check if line endpoints are on opposite sides of the box
        # in either x or y dimension

        # Quick reject: if both points are entirely on one side
        if x1 < box.left and x2 < box.left:
            return False
        if x1 > box.right and x2 > box.right:
            return False
        if y1 < box.top and y2 < box.top:
            return False
        if y1 > box.bottom and y2 > box.bottom:
            return False

        # Check intersection with each edge
        edges = [
            ((box.left, box.top), (box.right, box.top)),      # Top
            ((box.right, box.top), (box.right, box.bottom)),  # Right
            ((box.right, box.bottom), (box.left, box.bottom)), # Bottom
            ((box.left, box.bottom), (box.left, box.top))     # Left
        ]

        for edge_p1, edge_p2 in edges:
            if self._segments_intersect(p1, p2, edge_p1, edge_p2):
                return True

        # Also check if line passes through box interior
        # Sample points along the line
        num_samples = 10
        for i in range(1, num_samples):
            t = i / num_samples
            px = x1 + t * (x2 - x1)
            py = y1 + t * (y2 - y1)
            if box.contains_point(px, py):
                return True

        return False

    def _segments_intersect(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float]
    ) -> bool:
        """Check if two line segments intersect."""
        def ccw(A, B, C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

        return (ccw(p1, p3, p4) != ccw(p2, p3, p4) and
                ccw(p1, p2, p3) != ccw(p1, p2, p4))

    def _should_use_elbow(self, from_shape: BoundingBox, to_shape: BoundingBox) -> bool:
        """
        Determine if an elbow connector would be better than straight.

        Elbow is better when:
        - Shapes are diagonally positioned (not aligned horizontally or vertically)
        - The diagonal angle is steep (not close to 45 degrees where straight looks ok)
        """
        dx = abs(to_shape.center_x - from_shape.center_x)
        dy = abs(to_shape.center_y - from_shape.center_y)

        # If shapes are roughly aligned (one dimension dominates), straight is fine
        if dx < 0.5 or dy < 0.5:
            return False

        # Calculate angle
        angle = math.atan2(dy, dx) * 180 / math.pi

        # If angle is close to 45 degrees (30-60 range), straight looks ok
        # If angle is more extreme, elbow might be better
        if 30 <= angle <= 60:
            return False

        # Significant diagonal - elbow might help
        return dx > 1.0 and dy > 1.0

    def _check_overlaps(self, shapes: List[Dict[str, Any]]) -> None:
        """Check for overlapping shapes."""
        for i, shape1 in enumerate(shapes):
            for shape2 in shapes[i + 1:]:
                if self._shapes_overlap(shape1, shape2):
                    self.issues.append(ValidationIssue(
                        issue_type='overlap',
                        severity='error',
                        message=f"Shapes '{shape1.get('id')}' and '{shape2.get('id')}' overlap",
                        elements=[shape1.get('id', ''), shape2.get('id', '')],
                        suggestion=f"Move shapes apart by at least {self.MIN_SPACING} inches",
                        fix_action={
                            'action': 'separate_shapes',
                            'shape_ids': [shape1.get('id'), shape2.get('id')]
                        }
                    ))

    def _shapes_overlap(self, shape1: Dict, shape2: Dict) -> bool:
        """Check if two shapes overlap."""
        pos1 = shape1.get('position', {})
        size1 = shape1.get('size', {})
        pos2 = shape2.get('position', {})
        size2 = shape2.get('size', {})

        x1, y1 = pos1.get('x', 0), pos1.get('y', 0)
        w1, h1 = size1.get('width', 1), size1.get('height', 1)
        x2, y2 = pos2.get('x', 0), pos2.get('y', 0)
        w2, h2 = size2.get('width', 1), size2.get('height', 1)

        margin = 0.05
        return not (
            x1 + w1 + margin < x2 or
            x2 + w2 + margin < x1 or
            y1 + h1 + margin < y2 or
            y2 + h2 + margin < y1
        )

    def _check_bounds(self, shapes: List[Dict[str, Any]]) -> None:
        """Check if all shapes are within slide bounds."""
        for shape in shapes:
            pos = shape.get('position', {})
            size = shape.get('size', {})
            shape_id = shape.get('id', 'unknown')

            x, y = pos.get('x', 0), pos.get('y', 0)
            w, h = size.get('width', 1), size.get('height', 1)

            issues = []

            if x < 0:
                issues.append('left edge is off-slide')
            if y < 0:
                issues.append('top edge is off-slide')
            if x + w > self.SLIDE_WIDTH:
                issues.append('right edge extends beyond slide')
            if y + h > self.SLIDE_HEIGHT:
                issues.append('bottom edge extends beyond slide')

            if issues:
                self.issues.append(ValidationIssue(
                    issue_type='out_of_bounds',
                    severity='error',
                    message=f"Shape '{shape_id}': {', '.join(issues)}",
                    elements=[shape_id],
                    suggestion="Adjust position to fit within slide bounds",
                    fix_action={
                        'action': 'move_to_bounds',
                        'shape_id': shape_id
                    }
                ))

    def _check_connectors(self, connectors: List[Dict], shapes: List[Dict]) -> None:
        """Check if all connectors reference valid shapes."""
        shape_ids = {s.get('id') for s in shapes}

        for connector in connectors:
            conn_id = connector.get('id', 'unknown')
            from_id = connector.get('from')
            to_id = connector.get('to')

            if not from_id or not to_id:
                self.issues.append(ValidationIssue(
                    issue_type='missing_connection',
                    severity='error',
                    message=f"Connector '{conn_id}' is missing from/to reference",
                    elements=[conn_id],
                    suggestion="Ensure connector has both 'from' and 'to' fields"
                ))
                continue

            missing = []
            if from_id not in shape_ids:
                missing.append(f"source '{from_id}'")
            if to_id not in shape_ids:
                missing.append(f"target '{to_id}'")

            if missing:
                self.issues.append(ValidationIssue(
                    issue_type='missing_connection',
                    severity='error',
                    message=f"Connector '{conn_id}' references non-existent {' and '.join(missing)}",
                    elements=[conn_id, from_id, to_id],
                    suggestion="Verify that shape IDs match between shapes and connectors"
                ))

    def _check_spacing(self, shapes: List[Dict[str, Any]]) -> None:
        """Check if shapes have minimum spacing (warning only)."""
        for i, shape1 in enumerate(shapes):
            for shape2 in shapes[i + 1:]:
                distance = self._get_min_distance(shape1, shape2)
                if 0 < distance < self.MIN_SPACING:
                    self.issues.append(ValidationIssue(
                        issue_type='spacing',
                        severity='warning',
                        message=f"Shapes '{shape1.get('id')}' and '{shape2.get('id')}' are very close ({distance:.2f}\")",
                        elements=[shape1.get('id', ''), shape2.get('id', '')],
                        suggestion=f"Increase spacing to at least {self.MIN_SPACING} inches"
                    ))

    def _get_min_distance(self, shape1: Dict, shape2: Dict) -> float:
        """Calculate minimum distance between two shapes."""
        pos1 = shape1.get('position', {})
        size1 = shape1.get('size', {})
        pos2 = shape2.get('position', {})
        size2 = shape2.get('size', {})

        x1, y1 = pos1.get('x', 0), pos1.get('y', 0)
        w1, h1 = size1.get('width', 1), size1.get('height', 1)
        x2, y2 = pos2.get('x', 0), pos2.get('y', 0)
        w2, h2 = size2.get('width', 1), size2.get('height', 1)

        dx = max(0, max(x1 - (x2 + w2), x2 - (x1 + w1)))
        dy = max(0, max(y1 - (y2 + h2), y2 - (y1 + h1)))

        if dx > 0 and dy > 0:
            return (dx ** 2 + dy ** 2) ** 0.5
        return max(dx, dy)

    def is_valid(self, spec: Dict[str, Any]) -> bool:
        """Quick check if diagram is valid (no errors)."""
        issues = self.validate(spec)
        errors = [i for i in issues if i.severity == 'error']
        return len(errors) == 0

    def get_error_summary(self) -> str:
        """Get a human-readable summary of validation errors."""
        errors = [i for i in self.issues if i.severity == 'error']
        if not errors:
            return "No errors found"

        lines = [f"Found {len(errors)} validation error(s):"]
        for i, error in enumerate(errors, 1):
            lines.append(f"  {i}. [{error.issue_type}] {error.message}")
            if error.suggestion:
                lines.append(f"     Suggestion: {error.suggestion}")

        return "\n".join(lines)


class ValidationLoop:
    """
    INTELLIGENT validation loop that can REASON and FIX issues.

    Key improvements:
    - Applies specific fixes based on issue type
    - Changes connector types when paths are blocked
    - Re-routes connectors around obstacles
    """

    MAX_ATTEMPTS = 3

    def __init__(self, layout_engine, validator: Optional[DiagramValidator] = None):
        self.layout_engine = layout_engine
        self.validator = validator or DiagramValidator()

    def generate_with_validation(
        self,
        v2_spec: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
        """
        Generate a validated diagram with INTELLIGENT retry loop.

        The loop now:
        1. Generates layout
        2. Validates with path analysis
        3. Applies targeted fixes (not just generic adjustments)
        4. Re-validates the FIXED spec (not regenerating layout)
        5. Retries until valid or max attempts
        """
        best_spec = None
        best_issues = None

        # First pass: generate initial layout
        logger.info(f"Layout attempt 1/{self.MAX_ATTEMPTS}")
        v1_spec = self.layout_engine.layout(v2_spec)

        for attempt in range(self.MAX_ATTEMPTS):
            # Validate with intelligent analysis
            issues = self.validator.validate(v1_spec)
            errors = [i for i in issues if i.severity == 'error']

            logger.info(f"Validation attempt {attempt + 1}: {len(errors)} errors found")

            if not errors:
                logger.info("Validation passed - no errors")
                return v1_spec, issues

            # Keep track of best result
            if best_issues is None or len(errors) < len([i for i in best_issues if i.severity == 'error']):
                best_spec = v1_spec.copy()
                best_spec['elements'] = [e.copy() for e in v1_spec.get('elements', [])]
                best_issues = issues

            # Apply intelligent fixes TO THE SAME SPEC (don't regenerate layout)
            if attempt < self.MAX_ATTEMPTS - 1:
                logger.info(f"Applying fixes for attempt {attempt + 2}...")
                v1_spec = self._apply_intelligent_fixes(v1_spec, errors)

        logger.warning(f"Could not resolve all issues after {self.MAX_ATTEMPTS} attempts")
        # Return the fixed spec (even if some issues remain)
        return v1_spec, self.validator.validate(v1_spec)

    def _apply_intelligent_fixes(
        self,
        spec: Dict[str, Any],
        errors: List[ValidationIssue]
    ) -> Dict[str, Any]:
        """
        Apply INTELLIGENT fixes based on error type and fix_action.

        This is the KEY improvement - we use the reasoning from validation
        to make targeted fixes.
        """
        elements = spec.get('elements', [])

        for error in errors:
            fix_action = error.fix_action

            if not fix_action:
                # Fall back to generic fixes
                if error.issue_type == 'overlap':
                    self._fix_overlap(elements, error.elements)
                elif error.issue_type == 'out_of_bounds':
                    self._fix_bounds(elements, error.elements)
                continue

            action_type = fix_action.get('action')

            if action_type == 'change_connector_type':
                # Change connector from straight to elbow
                connector_id = fix_action.get('connector_id')
                new_type = fix_action.get('new_type', 'elbow')
                self._change_connector_type(elements, connector_id, new_type)
                logger.info(f"Fixed: Changed connector '{connector_id}' to {new_type}")

                # ALSO: Try to reposition shapes to avoid crossing
                # Find the connector and its endpoints
                connector = next((e for e in elements if e.get('id') == connector_id), None)
                if connector and error.issue_type == 'blocked_path':
                    crossed_shapes = [eid for eid in error.elements if eid != connector_id]
                    from_id = connector.get('from')
                    to_id = connector.get('to')

                    # Move the target shape to avoid crossing
                    self._reposition_to_avoid_crossing(elements, from_id, to_id, crossed_shapes)

            elif action_type == 'separate_shapes':
                shape_ids = fix_action.get('shape_ids', [])
                self._fix_overlap(elements, shape_ids)
                logger.info(f"Fixed: Separated shapes {shape_ids}")

            elif action_type == 'move_to_bounds':
                shape_id = fix_action.get('shape_id')
                self._fix_bounds(elements, [shape_id])
                logger.info(f"Fixed: Moved shape '{shape_id}' into bounds")

        return spec

    def _reposition_to_avoid_crossing(
        self,
        elements: List[Dict],
        from_id: str,
        to_id: str,
        crossed_shape_ids: List[str]
    ) -> None:
        """
        Reposition shapes to avoid connector crossings.

        Strategy: Move the target shape so the connector doesn't cross obstacles.
        """
        from_shape = next((e for e in elements if e.get('id') == from_id and e.get('type') != 'connector'), None)
        to_shape = next((e for e in elements if e.get('id') == to_id and e.get('type') != 'connector'), None)

        if not from_shape or not to_shape:
            return

        # Get the crossed shape(s)
        crossed_shapes = [e for e in elements if e.get('id') in crossed_shape_ids and e.get('type') != 'connector']

        if not crossed_shapes:
            return

        # Calculate new position for to_shape that avoids crossing
        from_pos = from_shape.get('position', {})
        to_pos = to_shape.get('position', {})
        crossed_pos = crossed_shapes[0].get('position', {})
        crossed_size = crossed_shapes[0].get('size', {})

        # Strategy: If the to_shape is below the crossed shape, move it more to the right
        # so the connector can go around
        from_x = from_pos.get('x', 0)
        from_y = from_pos.get('y', 0)
        to_x = to_pos.get('x', 0)
        to_y = to_pos.get('y', 0)
        crossed_x = crossed_pos.get('x', 0)
        crossed_right = crossed_x + crossed_size.get('width', 2)

        # Move to_shape to the right of the crossed shape
        if to_x < crossed_right + 0.5:
            new_x = crossed_right + 1.0  # Move to the right of the obstacle
            to_pos['x'] = min(new_x, 7.0)  # Don't go off slide
            logger.info(f"Repositioned '{to_id}' to x={to_pos['x']:.2f} to avoid crossing '{crossed_shape_ids[0]}'")

        # Alternative: if that doesn't work, move it to align with from_shape
        # This creates a straight vertical path
        elif abs(from_x - to_x) > 0.5:
            to_pos['x'] = from_x
            logger.info(f"Aligned '{to_id}' vertically with '{from_id}' to x={to_pos['x']:.2f}")

    def _change_connector_type(
        self,
        elements: List[Dict],
        connector_id: str,
        new_type: str
    ) -> None:
        """Change a connector's type (e.g., straight to elbow)."""
        for element in elements:
            if element.get('id') == connector_id and element.get('type') == 'connector':
                old_type = element.get('connector_type', 'straight')
                element['connector_type'] = new_type
                logger.debug(f"Changed connector '{connector_id}' from {old_type} to {new_type}")
                return

    def _fix_overlap(self, elements: List[Dict], shape_ids: List[str]) -> None:
        """Fix overlapping shapes by pushing them apart."""
        if len(shape_ids) < 2:
            return

        shapes = {e['id']: e for e in elements if e.get('id') in shape_ids and e.get('type') != 'connector'}

        if len(shapes) < 2:
            return

        shape1 = shapes.get(shape_ids[0])
        shape2 = shapes.get(shape_ids[1])

        if not shape1 or not shape2:
            return

        # Calculate centers
        x1 = shape1['position']['x'] + shape1['size']['width'] / 2
        y1 = shape1['position']['y'] + shape1['size']['height'] / 2
        x2 = shape2['position']['x'] + shape2['size']['width'] / 2
        y2 = shape2['position']['y'] + shape2['size']['height'] / 2

        # Calculate separation direction
        dx = x2 - x1
        dy = y2 - y1
        distance = (dx ** 2 + dy ** 2) ** 0.5 or 0.01

        # Normalize and apply separation
        separation = 0.5  # Move each shape 0.5 inches
        dx = (dx / distance) * separation
        dy = (dy / distance) * separation

        # Move shapes apart
        shape1['position']['x'] -= dx
        shape1['position']['y'] -= dy
        shape2['position']['x'] += dx
        shape2['position']['y'] += dy

    def _fix_bounds(self, elements: List[Dict], shape_ids: List[str]) -> None:
        """Fix out-of-bounds shapes by moving them into the slide."""
        for element in elements:
            if element.get('id') not in shape_ids:
                continue
            if element.get('type') == 'connector':
                continue

            pos = element.get('position', {})
            size = element.get('size', {})

            x, y = pos.get('x', 0), pos.get('y', 0)
            w, h = size.get('width', 1), size.get('height', 1)

            # Clamp to slide bounds
            margin = 0.3
            x = max(margin, min(10.0 - margin - w, x))
            y = max(margin, min(7.5 - margin - h, y))

            pos['x'] = x
            pos['y'] = y


# Convenience function
def validate_diagram(spec: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
    """
    Quick validation of a diagram spec with intelligent analysis.

    Args:
        spec: V1 diagram specification

    Returns:
        Tuple of (is_valid, list of issues)
    """
    validator = DiagramValidator()
    issues = validator.validate(spec)
    is_valid = all(i.severity != 'error' for i in issues)
    return is_valid, issues
