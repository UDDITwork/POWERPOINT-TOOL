"""
ELK-style Layout Engine for Diagram Generation

This module implements a hierarchical layout algorithm inspired by ELK (Eclipse Layout Kernel).
It calculates proper positions for nodes based on:
- Graph structure (edges define relationships)
- Position hints from Claude (relative positions like "below:nodeId")
- Collision detection (no overlapping shapes)

Key Features:
- Layered/hierarchical layout (Sugiyama-style)
- Collision detection and overlap removal
- Edge routing with proper spacing
- Support for position hints

Author: AI Patent Diagram Generator
License: MIT
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Represents the bounding box of a node."""
    x: float = 0.0
    y: float = 0.0
    width: float = 2.5
    height: float = 1.0

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

    def overlaps(self, other: 'BoundingBox', margin: float = 0.1) -> bool:
        """Check if this box overlaps with another (with optional margin)."""
        return not (
            self.right + margin < other.left or
            other.right + margin < self.left or
            self.bottom + margin < other.top or
            other.bottom + margin < self.top
        )


@dataclass
class LayoutNode:
    """A node with layout information."""
    id: str
    type: str
    text: str
    hint: Optional[str] = None
    size_hint: Optional[str] = None
    style: Optional[Dict] = None
    parent: Optional[str] = None  # Parent container ID
    is_container: bool = False    # True if this is a container/group

    # Layout properties (calculated)
    layer: int = 0
    order: int = 0
    box: BoundingBox = field(default_factory=BoundingBox)


@dataclass
class LayoutEdge:
    """An edge with layout information."""
    id: str
    from_node: str
    to_node: str
    label: Optional[str] = None
    style: Optional[Dict] = None


class ELKLayoutEngine:
    """
    Layout engine that calculates positions using a hierarchical algorithm.

    Algorithm steps:
    1. Parse nodes and edges from V2 spec
    2. Assign layers based on graph topology and hints
    3. Order nodes within layers to minimize edge crossings
    4. Calculate x,y coordinates with proper spacing
    5. Run collision detection and separate overlapping nodes
    6. Convert back to V1 format for PPTX generator
    """

    # Size presets (in inches)
    SIZE_PRESETS = {
        'small': (1.5, 0.6),
        'medium': (2.5, 1.0),
        'large': (3.5, 1.5),
        'wide': (4.0, 1.0),
        'tall': (2.0, 2.0),
    }

    # Slide dimensions (in inches)
    SLIDE_WIDTH = 10.0
    SLIDE_HEIGHT = 7.5
    MARGIN = 0.5

    # Spacing between nodes (in inches)
    LAYER_SPACING = 1.8  # Vertical spacing between layers
    NODE_SPACING = 0.8   # Horizontal spacing between nodes in same layer

    def __init__(self, slide_width: float = 10.0, slide_height: float = 7.5):
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.nodes: Dict[str, LayoutNode] = {}
        self.edges: List[LayoutEdge] = []
        self.layers: Dict[int, List[str]] = defaultdict(list)

    def layout(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: convert V2 spec to V1 spec with calculated positions.

        Args:
            spec: V2 diagram spec with nodes, edges, and hints

        Returns:
            V1 diagram spec with elements array containing positioned shapes
        """
        logger.info(f"Starting ELK layout for {len(spec.get('nodes', []))} nodes")

        # Reset state
        self.nodes = {}
        self.edges = []
        self.layers = defaultdict(list)

        # Parse input
        self._parse_spec(spec)

        # Run layout algorithm
        self._assign_layers()
        self._order_nodes_in_layers()
        self._calculate_positions()
        self._remove_overlaps()

        # Convert to V1 format
        return self._to_v1_spec(spec.get('metadata', {}))

    def _parse_spec(self, spec: Dict[str, Any]) -> None:
        """Parse V2 spec into internal node/edge structures."""
        # Get flow direction
        self.direction = spec.get('metadata', {}).get('direction', 'DOWN')

        # Parse nodes
        for node_data in spec.get('nodes', []):
            size = self._get_size(node_data.get('size_hint', 'medium'))
            node = LayoutNode(
                id=node_data['id'],
                type=node_data['type'],
                text=node_data.get('text', ''),
                hint=node_data.get('hint'),
                size_hint=node_data.get('size_hint'),
                style=node_data.get('style'),
                box=BoundingBox(width=size[0], height=size[1])
            )
            self.nodes[node.id] = node

        # Parse edges
        for edge_data in spec.get('edges', []):
            edge = LayoutEdge(
                id=edge_data['id'],
                from_node=edge_data['from'],
                to_node=edge_data['to'],
                label=edge_data.get('label'),
                style=edge_data.get('style')
            )
            self.edges.append(edge)

        logger.debug(f"Parsed {len(self.nodes)} nodes and {len(self.edges)} edges")

    def _get_size(self, size_hint: Optional[str]) -> Tuple[float, float]:
        """Convert size hint to actual dimensions."""
        if size_hint and size_hint.lower() in self.SIZE_PRESETS:
            return self.SIZE_PRESETS[size_hint.lower()]
        return self.SIZE_PRESETS['medium']

    def _assign_layers(self) -> None:
        """
        Assign nodes to layers based on graph topology and hints.

        Uses a combination of:
        1. Topological order (nodes flow from sources to sinks)
        2. Hint-based constraints (below:X means layer > X's layer)
        """
        # Build adjacency lists
        incoming: Dict[str, List[str]] = defaultdict(list)
        outgoing: Dict[str, List[str]] = defaultdict(list)

        for edge in self.edges:
            if edge.from_node in self.nodes and edge.to_node in self.nodes:
                outgoing[edge.from_node].append(edge.to_node)
                incoming[edge.to_node].append(edge.from_node)

        # Find roots (nodes with no incoming edges)
        roots = [nid for nid in self.nodes if not incoming[nid]]

        # If no roots found, pick the first node
        if not roots and self.nodes:
            roots = [list(self.nodes.keys())[0]]

        # BFS to assign layers
        visited: Set[str] = set()
        queue = [(nid, 0) for nid in roots]

        while queue:
            node_id, layer = queue.pop(0)

            if node_id in visited:
                # Update layer if we found a longer path
                if layer > self.nodes[node_id].layer:
                    self.nodes[node_id].layer = layer
                continue

            visited.add(node_id)
            self.nodes[node_id].layer = layer

            # Add children
            for child_id in outgoing[node_id]:
                if child_id not in visited:
                    queue.append((child_id, layer + 1))

        # Handle disconnected nodes
        for node_id in self.nodes:
            if node_id not in visited:
                self.nodes[node_id].layer = 0

        # Apply hint-based layer adjustments
        self._apply_hint_layers()

        # Group nodes by layer
        for node_id, node in self.nodes.items():
            self.layers[node.layer].append(node_id)

        logger.debug(f"Assigned {len(self.layers)} layers: {dict(self.layers)}")

    def _apply_hint_layers(self) -> None:
        """Adjust layers based on position hints like 'below:nodeId'."""
        MAX_ITERATIONS = 10

        for _ in range(MAX_ITERATIONS):
            changes = 0

            for node_id, node in self.nodes.items():
                if not node.hint:
                    continue

                hint = node.hint.lower()

                # Handle "below:nodeId" -> same column, layer + 1
                if hint.startswith('below:'):
                    ref_id = node.hint[6:]  # Original case
                    if ref_id in self.nodes:
                        ref_layer = self.nodes[ref_id].layer
                        if node.layer <= ref_layer:
                            node.layer = ref_layer + 1
                            changes += 1

                # Handle "above:nodeId" -> same column, layer - 1
                elif hint.startswith('above:'):
                    ref_id = node.hint[6:]
                    if ref_id in self.nodes:
                        ref_layer = self.nodes[ref_id].layer
                        if node.layer >= ref_layer:
                            node.layer = max(0, ref_layer - 1)
                            changes += 1

                # Handle "right-of:nodeId" or "left-of:nodeId" -> same layer
                elif hint.startswith('right-of:') or hint.startswith('left-of:'):
                    ref_id = node.hint.split(':')[1]
                    if ref_id in self.nodes:
                        node.layer = self.nodes[ref_id].layer
                        changes += 1

                # Handle "same-row:nodeId" -> same layer
                elif hint.startswith('same-row:'):
                    ref_id = node.hint[9:]
                    if ref_id in self.nodes:
                        node.layer = self.nodes[ref_id].layer
                        changes += 1

            if changes == 0:
                break

    def _order_nodes_in_layers(self) -> None:
        """Order nodes within each layer to minimize edge crossings."""
        # Rebuild layers dict after layer adjustments
        self.layers = defaultdict(list)
        for node_id, node in self.nodes.items():
            self.layers[node.layer].append(node_id)

        # Sort nodes in each layer
        for layer_idx in sorted(self.layers.keys()):
            layer_nodes = self.layers[layer_idx]

            # Use hints and edge connections for ordering
            ordered = self._order_layer_nodes(layer_nodes, layer_idx)
            self.layers[layer_idx] = ordered

            # Set order property
            for order, node_id in enumerate(ordered):
                self.nodes[node_id].order = order

    def _order_layer_nodes(self, node_ids: List[str], layer: int) -> List[str]:
        """Order nodes in a single layer based on hints and connections."""
        if len(node_ids) <= 1:
            return node_ids

        # Build ordering constraints from hints
        left_of: Dict[str, str] = {}  # node -> should be left of this node
        right_of: Dict[str, str] = {}  # node -> should be right of this node

        for node_id in node_ids:
            hint = self.nodes[node_id].hint
            if not hint:
                continue

            hint_lower = hint.lower()

            if hint_lower.startswith('right-of:'):
                ref_id = hint[9:]
                if ref_id in node_ids:
                    right_of[node_id] = ref_id

            elif hint_lower.startswith('left-of:'):
                ref_id = hint[8:]
                if ref_id in node_ids:
                    left_of[node_id] = ref_id

        # Simple ordering: start with nodes that have no left_of constraints
        ordered = []
        remaining = set(node_ids)

        # First, add nodes with no left constraint
        for node_id in node_ids:
            if node_id not in right_of:
                ordered.append(node_id)
                remaining.discard(node_id)

        # Then add the rest respecting right-of constraints
        while remaining:
            added = False
            for node_id in list(remaining):
                ref = right_of.get(node_id)
                if ref and ref in ordered:
                    # Insert after the reference
                    idx = ordered.index(ref) + 1
                    ordered.insert(idx, node_id)
                    remaining.discard(node_id)
                    added = True
                    break

            if not added:
                # No valid placement found, just append remaining
                ordered.extend(remaining)
                break

        return ordered

    def _calculate_positions(self) -> None:
        """Calculate x,y positions for all nodes based on layers and order."""
        if not self.layers:
            return

        num_layers = max(self.layers.keys()) + 1

        # Calculate total height needed
        total_height = num_layers * self.LAYER_SPACING
        start_y = self.MARGIN + (self.slide_height - 2 * self.MARGIN - total_height) / 2
        start_y = max(self.MARGIN, start_y)

        for layer_idx in sorted(self.layers.keys()):
            layer_nodes = self.layers[layer_idx]

            # Calculate y position for this layer
            y = start_y + layer_idx * self.LAYER_SPACING

            # Calculate total width of nodes in this layer
            total_width = sum(self.nodes[nid].box.width for nid in layer_nodes)
            total_width += (len(layer_nodes) - 1) * self.NODE_SPACING

            # Center the layer horizontally
            start_x = (self.slide_width - total_width) / 2
            start_x = max(self.MARGIN, start_x)

            # Position each node
            current_x = start_x
            for node_id in layer_nodes:
                node = self.nodes[node_id]
                node.box.x = current_x
                node.box.y = y
                current_x += node.box.width + self.NODE_SPACING

        # Apply hint-based position adjustments
        self._apply_position_hints()

    def _apply_position_hints(self) -> None:
        """Fine-tune positions based on absolute hints like 'top', 'center', etc."""
        for node_id, node in self.nodes.items():
            if not node.hint:
                continue

            hint = node.hint.lower()

            # Absolute position hints
            if hint == 'top':
                node.box.y = self.MARGIN
            elif hint == 'bottom':
                node.box.y = self.slide_height - self.MARGIN - node.box.height
            elif hint == 'left':
                node.box.x = self.MARGIN
            elif hint == 'right':
                node.box.x = self.slide_width - self.MARGIN - node.box.width
            elif hint == 'center':
                node.box.x = (self.slide_width - node.box.width) / 2
                node.box.y = (self.slide_height - node.box.height) / 2
            elif hint == 'top-left':
                node.box.x = self.MARGIN
                node.box.y = self.MARGIN
            elif hint == 'top-right':
                node.box.x = self.slide_width - self.MARGIN - node.box.width
                node.box.y = self.MARGIN
            elif hint == 'bottom-left':
                node.box.x = self.MARGIN
                node.box.y = self.slide_height - self.MARGIN - node.box.height
            elif hint == 'bottom-right':
                node.box.x = self.slide_width - self.MARGIN - node.box.width
                node.box.y = self.slide_height - self.MARGIN - node.box.height

    def _remove_overlaps(self) -> None:
        """
        Detect and remove overlapping nodes by pushing them apart.

        Uses an iterative approach:
        1. Find all overlapping pairs
        2. Calculate separation vectors
        3. Apply small movements
        4. Repeat until no overlaps
        """
        MAX_ITERATIONS = 50
        SEPARATION_STEP = 0.1

        node_list = list(self.nodes.values())

        for iteration in range(MAX_ITERATIONS):
            overlaps_found = False

            for i, node1 in enumerate(node_list):
                for node2 in node_list[i + 1:]:
                    if node1.box.overlaps(node2.box):
                        overlaps_found = True

                        # Calculate separation direction
                        dx = node2.box.center_x - node1.box.center_x
                        dy = node2.box.center_y - node1.box.center_y
                        distance = math.sqrt(dx * dx + dy * dy) or 0.01

                        # Normalize and apply separation
                        dx = (dx / distance) * SEPARATION_STEP
                        dy = (dy / distance) * SEPARATION_STEP

                        # Move nodes apart
                        node1.box.x -= dx / 2
                        node1.box.y -= dy / 2
                        node2.box.x += dx / 2
                        node2.box.y += dy / 2

            if not overlaps_found:
                logger.debug(f"Overlap removal converged in {iteration + 1} iterations")
                break

        # Clamp positions to slide bounds
        for node in self.nodes.values():
            node.box.x = max(self.MARGIN, min(self.slide_width - self.MARGIN - node.box.width, node.box.x))
            node.box.y = max(self.MARGIN, min(self.slide_height - self.MARGIN - node.box.height, node.box.y))

    def _to_v1_spec(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert internal layout to V1 format for PPTX generator.

        V1 format has 'elements' array with shapes and connectors.
        """
        elements = []

        # Add shapes (nodes)
        for node_id, node in self.nodes.items():
            element = {
                'id': node.id,
                'type': node.type,
                'text': node.text,
                'position': {
                    'x': round(node.box.x, 2),
                    'y': round(node.box.y, 2)
                },
                'size': {
                    'width': round(node.box.width, 2),
                    'height': round(node.box.height, 2)
                }
            }

            # ALWAYS enforce patent diagram styling:
            # - Transparent fill (no fill_color)
            # - Black border (1pt weight)
            # - Black text
            element['style'] = {
                'line_color': '000000',  # Black border
                'line_width': 1.0,       # 1pt border
                # No fill_color = transparent
            }

            # Text should be black
            element['text_format'] = {
                'color': '000000',        # Black text
                'align': 'center',
                'vertical_align': 'middle'
            }

            elements.append(element)

        # Add connectors (edges)
        for edge in self.edges:
            # Verify both endpoints exist
            if edge.from_node not in self.nodes or edge.to_node not in self.nodes:
                logger.warning(f"Edge {edge.id} references unknown node(s): {edge.from_node} -> {edge.to_node}")
                continue

            connector = {
                'id': edge.id,
                'type': 'connector',
                'connector_type': 'straight',
                'from': edge.from_node,
                'to': edge.to_node,
                'style': {
                    'arrow_end': True,
                    'line_width': 1.0,      # 1pt connector
                    'line_color': '000000'  # Black connector
                }
            }

            # Add label if present
            if edge.label:
                connector['label'] = edge.label

            # NOTE: Don't merge edge style from Claude - enforce patent style

            elements.append(connector)

        # Build V1 spec
        v1_spec = {
            'metadata': {
                'title': metadata.get('title', 'Generated Diagram'),
                'diagram_type': metadata.get('diagram_type', 'flowchart')
            },
            'elements': elements,
            'layout': {
                'type': 'elk',  # Mark as ELK-generated
                'direction': metadata.get('direction', 'DOWN')
            }
        }

        logger.info(f"Generated V1 spec with {len(elements)} elements")
        return v1_spec


class HierarchicalGroupLayout:
    """
    Layout engine that supports hierarchical containers/groups.

    This engine:
    1. Processes containers and their children
    2. Sizes containers to fit their children (bottom-up)
    3. Positions containers and then children within them (top-down)
    4. Creates dashed-border container shapes
    """

    # Size presets (in inches)
    SIZE_PRESETS = {
        'small': (1.5, 0.6),
        'medium': (2.5, 1.0),
        'large': (3.5, 1.5),
        'wide': (4.0, 1.0),
        'tall': (2.0, 2.0),
    }

    # Layout constants
    SLIDE_WIDTH = 10.0
    SLIDE_HEIGHT = 7.5
    MARGIN = 0.5
    CONTAINER_PADDING = 0.4  # Padding inside containers
    CONTAINER_LABEL_HEIGHT = 0.5  # Space for container label
    CONTAINER_SPACING = 0.6  # Space between sibling containers
    NODE_SPACING = 0.3  # Space between nodes in same container

    def __init__(self, slide_width: float = 10.0, slide_height: float = 7.5):
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.containers: Dict[str, Dict] = {}
        self.nodes: Dict[str, LayoutNode] = {}
        self.edges: List[LayoutEdge] = []
        self.container_children: Dict[str, List[str]] = {}  # container_id -> [node_ids]

    def layout(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: convert V2 spec with containers to V1 spec with positions.

        Args:
            spec: V2 diagram spec with containers, nodes, edges

        Returns:
            V1 diagram spec with elements array containing positioned shapes
        """
        logger.info(f"Starting hierarchical group layout")

        # Reset state
        self.containers = {}
        self.nodes = {}
        self.edges = []
        self.container_children = {}

        # Parse input
        self._parse_spec(spec)

        # Check if we have containers
        has_containers = len(self.containers) > 0

        if has_containers:
            # Run hierarchical layout
            self._calculate_container_sizes()
            self._position_containers()
            self._position_nodes_in_containers()
            self._position_orphan_nodes()  # Nodes without parents
        else:
            # Fall back to flat layout (use ELK)
            elk_engine = ELKLayoutEngine(self.slide_width, self.slide_height)
            return elk_engine.layout(spec)

        # Remove overlaps
        self._remove_overlaps()

        # Convert to V1 format
        return self._to_v1_spec(spec.get('metadata', {}))

    def _parse_spec(self, spec: Dict[str, Any]) -> None:
        """Parse V2 spec with containers into internal structures."""
        # Parse containers
        for container_data in spec.get('containers', []):
            container_id = container_data['id']
            self.containers[container_id] = {
                'id': container_id,
                'label': container_data.get('label', ''),
                'children': container_data.get('children', []),
                'style': container_data.get('style', {'border_style': 'dashed'}),
                'hint': container_data.get('hint'),
                'box': BoundingBox()  # Will be calculated
            }
            self.container_children[container_id] = container_data.get('children', [])

        # Parse nodes
        for node_data in spec.get('nodes', []):
            size = self._get_size(node_data.get('size_hint', 'medium'))
            node = LayoutNode(
                id=node_data['id'],
                type=node_data['type'],
                text=node_data.get('text', ''),
                hint=node_data.get('hint'),
                size_hint=node_data.get('size_hint'),
                style=node_data.get('style'),
                parent=node_data.get('parent'),  # Parent container ID
                box=BoundingBox(width=size[0], height=size[1])
            )
            self.nodes[node.id] = node

        # Parse edges
        for edge_data in spec.get('edges', []):
            edge = LayoutEdge(
                id=edge_data['id'],
                from_node=edge_data['from'],
                to_node=edge_data['to'],
                label=edge_data.get('label'),
                style=edge_data.get('style')
            )
            self.edges.append(edge)

        logger.debug(f"Parsed {len(self.containers)} containers, {len(self.nodes)} nodes, {len(self.edges)} edges")

    def _get_size(self, size_hint: Optional[str]) -> Tuple[float, float]:
        """Convert size hint to actual dimensions."""
        if size_hint and size_hint.lower() in self.SIZE_PRESETS:
            return self.SIZE_PRESETS[size_hint.lower()]
        return self.SIZE_PRESETS['medium']

    def _calculate_container_sizes(self) -> None:
        """
        Calculate container sizes based on their children (bottom-up sizing).

        Container size = children bounding box + padding + label height
        """
        for container_id, container in self.containers.items():
            children_ids = container['children']

            if not children_ids:
                # Empty container - give it minimum size
                container['box'] = BoundingBox(
                    width=2.0,
                    height=1.5
                )
                continue

            # Calculate total size needed for children
            child_nodes = [self.nodes[cid] for cid in children_ids if cid in self.nodes]

            if not child_nodes:
                container['box'] = BoundingBox(width=2.0, height=1.5)
                continue

            # Calculate children bounding box (stacked vertically by default)
            max_child_width = max(n.box.width for n in child_nodes)
            total_child_height = sum(n.box.height for n in child_nodes)
            total_child_height += self.NODE_SPACING * (len(child_nodes) - 1)

            # Container size = children + padding + label
            container_width = max_child_width + 2 * self.CONTAINER_PADDING
            container_height = total_child_height + 2 * self.CONTAINER_PADDING + self.CONTAINER_LABEL_HEIGHT

            container['box'] = BoundingBox(
                width=container_width,
                height=container_height
            )

        logger.debug(f"Calculated container sizes: {[(c, self.containers[c]['box'].width, self.containers[c]['box'].height) for c in self.containers]}")

    def _position_containers(self) -> None:
        """
        Position containers based on hints (top-down positioning).

        Supports hints like:
        - "left", "right", "top", "center"
        - "right-of:container_id"
        """
        positioned: Set[str] = set()
        remaining = list(self.containers.keys())

        current_x = self.MARGIN
        current_y = self.MARGIN

        # First pass: position containers with absolute hints
        for container_id in list(remaining):
            container = self.containers[container_id]
            hint = container.get('hint', '').lower()

            if hint in ['left', 'top-left', '']:
                container['box'].x = current_x
                container['box'].y = current_y
                positioned.add(container_id)
                remaining.remove(container_id)

        # Second pass: position containers with relative hints
        MAX_ITERATIONS = 10
        for _ in range(MAX_ITERATIONS):
            if not remaining:
                break

            for container_id in list(remaining):
                container = self.containers[container_id]
                hint = container.get('hint', '').lower()

                if hint.startswith('right-of:'):
                    ref_id = container['hint'][9:]  # Original case
                    if ref_id in positioned:
                        ref_container = self.containers[ref_id]
                        container['box'].x = ref_container['box'].right + self.CONTAINER_SPACING
                        container['box'].y = ref_container['box'].y
                        positioned.add(container_id)
                        remaining.remove(container_id)

                elif hint.startswith('below:'):
                    ref_id = container['hint'][6:]
                    if ref_id in positioned:
                        ref_container = self.containers[ref_id]
                        container['box'].x = ref_container['box'].x
                        container['box'].y = ref_container['box'].bottom + self.CONTAINER_SPACING
                        positioned.add(container_id)
                        remaining.remove(container_id)

                elif hint == 'right':
                    # Position at right side
                    max_x = self.MARGIN
                    for pid in positioned:
                        max_x = max(max_x, self.containers[pid]['box'].right)
                    container['box'].x = max_x + self.CONTAINER_SPACING
                    container['box'].y = self.MARGIN
                    positioned.add(container_id)
                    remaining.remove(container_id)

        # Position any remaining containers in a row
        next_x = self.MARGIN
        for pid in positioned:
            next_x = max(next_x, self.containers[pid]['box'].right + self.CONTAINER_SPACING)

        for container_id in remaining:
            container = self.containers[container_id]
            container['box'].x = next_x
            container['box'].y = self.MARGIN
            next_x = container['box'].right + self.CONTAINER_SPACING
            positioned.add(container_id)

        logger.debug(f"Positioned {len(positioned)} containers")

    def _position_nodes_in_containers(self) -> None:
        """
        Position nodes inside their parent containers.

        Nodes are stacked vertically inside their container.
        """
        for container_id, container in self.containers.items():
            children_ids = container['children']
            child_nodes = [self.nodes[cid] for cid in children_ids if cid in self.nodes]

            if not child_nodes:
                continue

            # Start position inside container (after label)
            start_x = container['box'].x + self.CONTAINER_PADDING
            start_y = container['box'].y + self.CONTAINER_LABEL_HEIGHT + self.CONTAINER_PADDING

            # Center children horizontally in container
            container_inner_width = container['box'].width - 2 * self.CONTAINER_PADDING

            current_y = start_y
            for node in child_nodes:
                # Center node horizontally
                node.box.x = start_x + (container_inner_width - node.box.width) / 2
                node.box.y = current_y
                current_y += node.box.height + self.NODE_SPACING

        logger.debug("Positioned nodes in containers")

    def _position_orphan_nodes(self) -> None:
        """Position nodes that don't belong to any container."""
        orphan_nodes = [n for n in self.nodes.values() if n.parent is None]

        if not orphan_nodes:
            return

        # Find rightmost container
        max_x = self.MARGIN
        for container in self.containers.values():
            max_x = max(max_x, container['box'].right)

        # Position orphan nodes to the right of containers
        start_x = max_x + self.CONTAINER_SPACING if self.containers else self.MARGIN
        current_y = self.MARGIN

        for node in orphan_nodes:
            node.box.x = start_x
            node.box.y = current_y
            current_y += node.box.height + self.NODE_SPACING

    def _remove_overlaps(self) -> None:
        """Remove any overlapping elements."""
        MAX_ITERATIONS = 30
        SEPARATION_STEP = 0.15

        all_boxes = []
        for container in self.containers.values():
            all_boxes.append(('container', container['id'], container['box']))

        for iteration in range(MAX_ITERATIONS):
            overlaps_found = False

            for i, (type1, id1, box1) in enumerate(all_boxes):
                for j, (type2, id2, box2) in enumerate(all_boxes[i + 1:], i + 1):
                    if box1.overlaps(box2):
                        overlaps_found = True

                        # Calculate separation
                        dx = box2.center_x - box1.center_x
                        dy = box2.center_y - box1.center_y
                        distance = math.sqrt(dx * dx + dy * dy) or 0.01

                        dx = (dx / distance) * SEPARATION_STEP
                        dy = (dy / distance) * SEPARATION_STEP

                        box1.x -= dx / 2
                        box1.y -= dy / 2
                        box2.x += dx / 2
                        box2.y += dy / 2

            if not overlaps_found:
                break

        # Reposition nodes in containers after container movement
        self._position_nodes_in_containers()

        # Clamp to slide bounds
        for container in self.containers.values():
            box = container['box']
            box.x = max(self.MARGIN, min(self.slide_width - self.MARGIN - box.width, box.x))
            box.y = max(self.MARGIN, min(self.slide_height - self.MARGIN - box.height, box.y))

        for node in self.nodes.values():
            box = node.box
            box.x = max(self.MARGIN, min(self.slide_width - self.MARGIN - box.width, box.x))
            box.y = max(self.MARGIN, min(self.slide_height - self.MARGIN - box.height, box.y))

    def _to_v1_spec(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert to V1 format with positioned elements.

        Containers become rectangles with dashed borders.
        """
        elements = []

        # Add containers first (so they render behind children)
        for container_id, container in self.containers.items():
            box = container['box']
            style = container.get('style', {})

            element = {
                'id': container_id,
                'type': 'rectangle',  # Containers are rectangles
                'text': container['label'],
                'position': {
                    'x': round(box.x, 2),
                    'y': round(box.y, 2)
                },
                'size': {
                    'width': round(box.width, 2),
                    'height': round(box.height, 2)
                },
                'style': {
                    'line_color': '666666',  # Gray dashed border
                    'line_width': 1.5,
                    'line_style': style.get('border_style', 'dashed'),
                    # No fill - transparent background
                },
                'is_container': True,  # Mark as container for PPTX grouping
                'children': container['children'],
                'text_format': {
                    'color': '333333',
                    'align': 'left',
                    'vertical_align': 'top'  # Label at top of container
                }
            }
            elements.append(element)

        # Add nodes
        for node_id, node in self.nodes.items():
            element = {
                'id': node.id,
                'type': node.type,
                'text': node.text,
                'position': {
                    'x': round(node.box.x, 2),
                    'y': round(node.box.y, 2)
                },
                'size': {
                    'width': round(node.box.width, 2),
                    'height': round(node.box.height, 2)
                },
                'style': {
                    'line_color': '000000',
                    'line_width': 1.0,
                },
                'text_format': {
                    'color': '000000',
                    'align': 'center',
                    'vertical_align': 'middle'
                }
            }

            # Add parent reference for grouping
            if node.parent:
                element['parent_id'] = node.parent

            elements.append(element)

        # Add connectors (edges)
        for edge in self.edges:
            # Check if edge connects containers or nodes
            from_exists = edge.from_node in self.nodes or edge.from_node in self.containers
            to_exists = edge.to_node in self.nodes or edge.to_node in self.containers

            if not from_exists or not to_exists:
                logger.warning(f"Edge {edge.id} references unknown node(s)")
                continue

            connector = {
                'id': edge.id,
                'type': 'connector',
                'connector_type': 'straight',
                'from': edge.from_node,
                'to': edge.to_node,
                'style': {
                    'arrow_end': True,
                    'line_width': 1.0,
                    'line_color': '000000'
                }
            }

            if edge.label:
                connector['label'] = edge.label

            elements.append(connector)

        v1_spec = {
            'metadata': {
                'title': metadata.get('title', 'Generated Diagram'),
                'diagram_type': metadata.get('diagram_type', 'hierarchical')
            },
            'elements': elements,
            'layout': {
                'type': 'hierarchical_group',
                'direction': metadata.get('direction', 'DOWN')
            }
        }

        logger.info(f"Generated V1 spec with {len(elements)} elements ({len(self.containers)} containers, {len(self.nodes)} nodes)")
        return v1_spec


# Convenience function
def apply_elk_layout(v2_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply layout to a V2 diagram spec.

    Uses HierarchicalGroupLayout if containers are present,
    otherwise falls back to ELKLayoutEngine.

    Args:
        v2_spec: Diagram spec with nodes, edges, and optional containers

    Returns:
        V1 diagram spec with calculated positions
    """
    # Check if spec has containers
    if v2_spec.get('containers'):
        engine = HierarchicalGroupLayout()
        return engine.layout(v2_spec)
    else:
        engine = ELKLayoutEngine()
        return engine.layout(v2_spec)
