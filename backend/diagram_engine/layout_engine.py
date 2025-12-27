"""
Advanced Layout Engine for Complex Patent Diagrams

This module handles automatic positioning of diagram elements,
especially for nested/hierarchical structures like patent system diagrams.

Supports:
- Hierarchical layouts (boxes within boxes)
- Tree layouts (flowcharts)
- Force-directed layouts (network diagrams)

Author: AI Patent Diagram Generator
License: MIT
"""

from typing import Dict, List, Any, Tuple
import math


class LayoutEngine:
    """Base class for layout algorithms."""

    def __init__(self, slide_width: float = 10.0, slide_height: float = 7.5):
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margin = 0.5

    def calculate_positions(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate positions for all elements in spec."""
        raise NotImplementedError


class HierarchicalLayoutEngine(LayoutEngine):
    """
    Layout engine for nested hierarchical diagrams.

    Handles diagrams like patent FIG. 2 where components are nested
    within parent containers (Computer System > Time Series Model > Embeddings).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_box_width = 2.5
        self.default_box_height = 0.8
        self.padding = 0.3  # Padding inside parent containers
        self.spacing = 0.2  # Spacing between siblings

    def calculate_positions(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate positions for hierarchical structure.

        Input spec format:
        {
            "type": "hierarchy",
            "root": {
                "id": "202",
                "label": "Computer System 202",
                "children": [
                    {"id": "210A", "label": "System Metrics 210A"},
                    {
                        "id": "212",
                        "label": "TSFM 212",
                        "children": [...]
                    }
                ]
            }
        }

        Output: python-pptx compatible spec with positions
        """
        elements = []

        # Process root element
        root = spec.get('root', {})

        # Calculate layout recursively
        root_layout = self._layout_node(
            root,
            x=self.margin,
            y=self.margin,
            available_width=self.slide_width - 2 * self.margin,
            available_height=self.slide_height - 2 * self.margin
        )

        # Convert to flat list of elements for python-pptx
        self._flatten_layout(root_layout, elements)

        return {
            "metadata": spec.get('metadata', {}),
            "elements": elements
        }

    def _layout_node(
        self,
        node: Dict[str, Any],
        x: float,
        y: float,
        available_width: float,
        available_height: float
    ) -> Dict[str, Any]:
        """
        Recursively calculate layout for a node and its children.

        Returns node with calculated position and size.
        """
        node_id = node.get('id', 'unknown')
        label = node.get('label', '')
        children = node.get('children', [])

        # If no children, use default size
        if not children:
            return {
                "id": node_id,
                "type": node.get('shape', 'rectangle'),
                "text": label,
                "position": {"x": x, "y": y},
                "size": {
                    "width": min(self.default_box_width, available_width),
                    "height": self.default_box_height
                },
                "style": node.get('style', {}),
                "children": []
            }

        # Calculate layout for children first (bottom-up)
        child_layouts = []
        current_y = y + self.padding
        max_child_width = 0

        for child in children:
            child_layout = self._layout_node(
                child,
                x=x + self.padding,
                y=current_y,
                available_width=available_width - 2 * self.padding,
                available_height=available_height - (current_y - y)
            )
            child_layouts.append(child_layout)

            # Update position for next child
            current_y += child_layout["size"]["height"] + self.spacing
            max_child_width = max(max_child_width, child_layout["size"]["width"])

        # Calculate parent size to fit all children
        parent_width = max_child_width + 2 * self.padding
        parent_height = (current_y - y) + self.padding

        return {
            "id": node_id,
            "type": node.get('shape', 'rectangle'),
            "text": label,
            "position": {"x": x, "y": y},
            "size": {"width": parent_width, "height": parent_height},
            "style": node.get('style', {"fill_color": "FFFFFF", "line_width": 2}),
            "children": child_layouts
        }

    def _flatten_layout(self, node: Dict[str, Any], elements: List[Dict]):
        """
        Convert hierarchical layout to flat list for python-pptx.

        Renders parents first (so they appear behind children).
        """
        # Add parent node
        elements.append({
            "id": node["id"],
            "type": node["type"],
            "text": node["text"],
            "position": node["position"],
            "size": node["size"],
            "style": node.get("style", {})
        })

        # Recursively add children
        for child in node.get("children", []):
            self._flatten_layout(child, elements)


class FlowLayoutEngine(LayoutEngine):
    """
    Layout engine for flowcharts (FIG. 5 style).

    Arranges boxes in vertical or horizontal flow with arrows.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.box_width = 6.0
        self.box_height = 0.8
        self.vertical_spacing = 0.5

    def calculate_positions(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate positions for flowchart.

        Input spec format:
        {
            "type": "flowchart",
            "direction": "vertical",  # or "horizontal"
            "steps": [
                {"id": "502", "label": "Receive system metrics..."},
                {"id": "504", "label": "Generate embeddings..."},
                ...
            ]
        }
        """
        steps = spec.get('steps', [])
        direction = spec.get('direction', 'vertical')

        elements = []
        connectors = []

        # Calculate positions
        if direction == 'vertical':
            start_x = (self.slide_width - self.box_width) / 2
            start_y = self.margin

            for i, step in enumerate(steps):
                y_pos = start_y + i * (self.box_height + self.vertical_spacing)

                # Add box
                elements.append({
                    "id": step['id'],
                    "type": "rectangle",
                    "text": step['label'],
                    "position": {"x": start_x, "y": y_pos},
                    "size": {"width": self.box_width, "height": self.box_height},
                    "style": {"fill_color": "FFFFFF", "line_width": 1.5}
                })

                # Add connector to next step
                if i < len(steps) - 1:
                    connectors.append({
                        "id": f"arrow_{i}",
                        "type": "connector",
                        "connector_type": "straight",
                        "from": step['id'],
                        "to": steps[i + 1]['id'],
                        "from_side": "bottom",
                        "to_side": "top",
                        "style": {"arrow_end": True, "line_width": 1.5}
                    })

        return {
            "metadata": spec.get('metadata', {}),
            "elements": elements + connectors
        }


class NetworkLayoutEngine(LayoutEngine):
    """
    Layout engine for network diagrams.

    Uses force-directed algorithm for natural node positioning.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iterations = 50
        self.k = 1.0  # Optimal distance between nodes

    def calculate_positions(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate positions using force-directed layout.

        Input spec format:
        {
            "type": "network",
            "nodes": [
                {"id": "100", "label": "Server"},
                {"id": "110", "label": "Database"},
                ...
            ],
            "edges": [
                {"from": "100", "to": "110"},
                ...
            ]
        }
        """
        nodes = spec.get('nodes', [])
        edges = spec.get('edges', [])

        # Initialize random positions
        positions = {}
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / len(nodes)
            radius = min(self.slide_width, self.slide_height) / 3
            positions[node['id']] = {
                "x": self.slide_width / 2 + radius * math.cos(angle),
                "y": self.slide_height / 2 + radius * math.sin(angle)
            }

        # Force-directed algorithm (simplified Fruchterman-Reingold)
        for iteration in range(self.iterations):
            # Calculate repulsive forces between all nodes
            forces = {node['id']: {"x": 0, "y": 0} for node in nodes}

            for i, node1 in enumerate(nodes):
                for node2 in nodes[i + 1:]:
                    dx = positions[node1['id']]['x'] - positions[node2['id']]['x']
                    dy = positions[node1['id']]['y'] - positions[node2['id']]['y']
                    distance = math.sqrt(dx**2 + dy**2) or 0.01

                    # Repulsive force
                    force = (self.k ** 2) / distance
                    forces[node1['id']]['x'] += (dx / distance) * force
                    forces[node1['id']]['y'] += (dy / distance) * force
                    forces[node2['id']]['x'] -= (dx / distance) * force
                    forces[node2['id']]['y'] -= (dy / distance) * force

            # Calculate attractive forces along edges
            for edge in edges:
                from_id = edge['from']
                to_id = edge['to']

                dx = positions[from_id]['x'] - positions[to_id]['x']
                dy = positions[from_id]['y'] - positions[to_id]['y']
                distance = math.sqrt(dx**2 + dy**2) or 0.01

                # Attractive force
                force = (distance ** 2) / self.k
                forces[from_id]['x'] -= (dx / distance) * force
                forces[from_id]['y'] -= (dy / distance) * force
                forces[to_id]['x'] += (dx / distance) * force
                forces[to_id]['y'] += (dy / distance) * force

            # Update positions
            temp = max(0.1, 1.0 - iteration / self.iterations)
            for node in nodes:
                node_id = node['id']
                displacement = math.sqrt(forces[node_id]['x']**2 + forces[node_id]['y']**2) or 0.01
                positions[node_id]['x'] += (forces[node_id]['x'] / displacement) * min(displacement, temp)
                positions[node_id]['y'] += (forces[node_id]['y'] / displacement) * min(displacement, temp)

                # Keep within bounds
                positions[node_id]['x'] = max(self.margin, min(self.slide_width - self.margin, positions[node_id]['x']))
                positions[node_id]['y'] = max(self.margin, min(self.slide_height - self.margin, positions[node_id]['y']))

        # Convert to elements
        elements = []
        for node in nodes:
            elements.append({
                "id": node['id'],
                "type": "rectangle",
                "text": node['label'],
                "position": positions[node['id']],
                "size": {"width": 1.5, "height": 0.8},
                "style": node.get('style', {})
            })

        # Add connectors
        for edge in edges:
            elements.append({
                "id": f"conn_{edge['from']}_{edge['to']}",
                "type": "connector",
                "connector_type": "straight",
                "from": edge['from'],
                "to": edge['to'],
                "style": {"arrow_end": True}
            })

        return {
            "metadata": spec.get('metadata', {}),
            "elements": elements
        }


# Factory function
def get_layout_engine(diagram_type: str, **kwargs) -> LayoutEngine:
    """
    Get appropriate layout engine based on diagram type.

    Args:
        diagram_type: "hierarchy", "flowchart", or "network"
        **kwargs: Additional parameters for layout engine

    Returns:
        Configured layout engine
    """
    engines = {
        "hierarchy": HierarchicalLayoutEngine,
        "flowchart": FlowLayoutEngine,
        "network": NetworkLayoutEngine
    }

    engine_class = engines.get(diagram_type, HierarchicalLayoutEngine)
    return engine_class(**kwargs)
