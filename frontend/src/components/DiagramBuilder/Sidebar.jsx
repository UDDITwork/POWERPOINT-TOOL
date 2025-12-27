import { memo, useState } from 'react';
import './Sidebar.css';

const shapeCategories = [
  {
    name: 'Basic Shapes',
    expanded: true,
    shapes: [
      { type: 'rectangle', label: 'Rectangle', icon: '▭' },
      { type: 'roundedRectangle', label: 'Rounded Rect', icon: '▢' },
      { type: 'circle', label: 'Circle', icon: '●' },
      { type: 'oval', label: 'Oval', icon: '⬭' },
      { type: 'square', label: 'Square', icon: '■' },
      { type: 'diamond', label: 'Diamond', icon: '◆' },
      { type: 'triangle', label: 'Triangle', icon: '▲' },
      { type: 'triangleDown', label: 'Triangle Down', icon: '▼' },
      { type: 'pentagon', label: 'Pentagon', icon: '⬠' },
      { type: 'hexagon', label: 'Hexagon', icon: '⬡' },
      { type: 'octagon', label: 'Octagon', icon: '⯃' },
      { type: 'star', label: 'Star', icon: '★' },
      { type: 'star4', label: '4-Point Star', icon: '✦' },
      { type: 'cross', label: 'Cross', icon: '✚' },
      { type: 'plus', label: 'Plus', icon: '➕' },
    ]
  },
  {
    name: 'Flowchart',
    expanded: true,
    shapes: [
      { type: 'process', label: 'Process', icon: '▭' },
      { type: 'decision', label: 'Decision', icon: '◇' },
      { type: 'terminator', label: 'Terminator', icon: '⬭' },
      { type: 'data', label: 'Data (I/O)', icon: '▱' },
      { type: 'document', label: 'Document', icon: '📄' },
      { type: 'multiDocument', label: 'Multi-Document', icon: '📑' },
      { type: 'predefinedProcess', label: 'Predefined', icon: '⧈' },
      { type: 'storedData', label: 'Stored Data', icon: '⌓' },
      { type: 'internalStorage', label: 'Internal Storage', icon: '⊞' },
      { type: 'manualInput', label: 'Manual Input', icon: '⌸' },
      { type: 'manualOperation', label: 'Manual Op', icon: '⏢' },
      { type: 'preparation', label: 'Preparation', icon: '⬡' },
      { type: 'delay', label: 'Delay', icon: '⌛' },
      { type: 'connector', label: 'Connector', icon: '○' },
      { type: 'offPageConnector', label: 'Off-Page', icon: '⬠' },
      { type: 'merge', label: 'Merge', icon: '▽' },
      { type: 'extract', label: 'Extract', icon: '△' },
      { type: 'or', label: 'OR', icon: '⊕' },
      { type: 'summing', label: 'Summing', icon: '⊗' },
    ]
  },
  {
    name: 'Arrows',
    expanded: false,
    shapes: [
      { type: 'arrowRight', label: 'Right Arrow', icon: '→' },
      { type: 'arrowLeft', label: 'Left Arrow', icon: '←' },
      { type: 'arrowUp', label: 'Up Arrow', icon: '↑' },
      { type: 'arrowDown', label: 'Down Arrow', icon: '↓' },
      { type: 'arrowBidirectional', label: 'Bidirectional', icon: '↔' },
      { type: 'arrowVertical', label: 'Vertical', icon: '↕' },
      { type: 'arrowBent', label: 'Bent Arrow', icon: '↱' },
      { type: 'arrowUturn', label: 'U-Turn', icon: '↩' },
      { type: 'arrowCurved', label: 'Curved', icon: '↷' },
      { type: 'arrowCircular', label: 'Circular', icon: '↻' },
      { type: 'chevronRight', label: 'Chevron Right', icon: '›' },
      { type: 'chevronLeft', label: 'Chevron Left', icon: '‹' },
      { type: 'arrowPentagon', label: 'Pentagon Arrow', icon: '⯈' },
      { type: 'arrowNotched', label: 'Notched', icon: '⮞' },
      { type: 'arrowStriped', label: 'Striped', icon: '⇨' },
    ]
  },
  {
    name: 'Callouts',
    expanded: false,
    shapes: [
      { type: 'calloutRect', label: 'Rect Callout', icon: '🗨' },
      { type: 'calloutRounded', label: 'Rounded Callout', icon: '💬' },
      { type: 'calloutOval', label: 'Oval Callout', icon: '🗯' },
      { type: 'calloutCloud', label: 'Cloud Callout', icon: '☁' },
      { type: 'calloutLine', label: 'Line Callout', icon: '📍' },
      { type: 'annotation', label: 'Annotation', icon: '📝' },
      { type: 'bracket', label: 'Bracket', icon: '{' },
      { type: 'brace', label: 'Brace', icon: '[' },
    ]
  },
  {
    name: 'Containers',
    expanded: false,
    shapes: [
      { type: 'cylinder', label: 'Cylinder', icon: '⬭' },
      { type: 'database', label: 'Database', icon: '🗄' },
      { type: 'cube', label: 'Cube', icon: '⬛' },
      { type: 'can', label: 'Can', icon: '⬭' },
      { type: 'folder', label: 'Folder', icon: '📁' },
      { type: 'card', label: 'Card', icon: '🗂' },
      { type: 'tape', label: 'Tape', icon: '📼' },
      { type: 'frame', label: 'Frame', icon: '🖼' },
    ]
  },
  {
    name: 'Symbols',
    expanded: false,
    shapes: [
      { type: 'cloud', label: 'Cloud', icon: '☁' },
      { type: 'lightning', label: 'Lightning', icon: '⚡' },
      { type: 'heart', label: 'Heart', icon: '❤' },
      { type: 'moon', label: 'Moon', icon: '☽' },
      { type: 'sun', label: 'Sun', icon: '☀' },
      { type: 'gear', label: 'Gear', icon: '⚙' },
      { type: 'puzzle', label: 'Puzzle', icon: '🧩' },
      { type: 'shield', label: 'Shield', icon: '🛡' },
      { type: 'lock', label: 'Lock', icon: '🔒' },
      { type: 'key', label: 'Key', icon: '🔑' },
      { type: 'flag', label: 'Flag', icon: '🚩' },
      { type: 'checkmark', label: 'Checkmark', icon: '✓' },
      { type: 'xmark', label: 'X Mark', icon: '✗' },
      { type: 'warning', label: 'Warning', icon: '⚠' },
      { type: 'info', label: 'Info', icon: 'ℹ' },
    ]
  },
  {
    name: 'Lines & Connectors',
    expanded: false,
    shapes: [
      { type: 'line', label: 'Line', icon: '─' },
      { type: 'lineArrow', label: 'Arrow Line', icon: '→' },
      { type: 'lineDouble', label: 'Double Arrow', icon: '↔' },
      { type: 'lineDashed', label: 'Dashed Line', icon: '┄' },
      { type: 'lineDotted', label: 'Dotted Line', icon: '┈' },
      { type: 'elbow', label: 'Elbow', icon: '⌐' },
      { type: 'curve', label: 'Curve', icon: '∿' },
      { type: 'arc', label: 'Arc', icon: '⌒' },
    ]
  },
];

const Sidebar = () => {
  const [expandedCategories, setExpandedCategories] = useState(
    shapeCategories.reduce((acc, cat) => {
      acc[cat.name] = cat.expanded;
      return acc;
    }, {})
  );

  const toggleCategory = (categoryName) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryName]: !prev[categoryName]
    }));
  };

  const onDragStart = (event, shapeType) => {
    event.dataTransfer.setData('application/reactflow', shapeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  const totalShapes = shapeCategories.reduce((sum, cat) => sum + cat.shapes.length, 0);

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Shapes</h2>
        <span className="shape-count">{totalShapes} shapes</span>
      </div>

      <div className="sidebar-scroll">
        {shapeCategories.map((category) => (
          <div key={category.name} className="sidebar-section">
            <button
              className="category-header"
              onClick={() => toggleCategory(category.name)}
            >
              <span className="category-arrow">
                {expandedCategories[category.name] ? '▼' : '▶'}
              </span>
              <span className="category-name">{category.name}</span>
              <span className="category-count">{category.shapes.length}</span>
            </button>

            {expandedCategories[category.name] && (
              <div className="shapes-grid">
                {category.shapes.map((shape) => (
                  <div
                    key={shape.type}
                    className="shape-item"
                    draggable
                    onDragStart={(e) => onDragStart(e, shape.type)}
                    title={shape.label}
                  >
                    <span className="shape-icon">{shape.icon}</span>
                    <span className="shape-label">{shape.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        <div className="sidebar-section">
          <h3 className="sidebar-title">Tips</h3>
          <ul className="tips-list">
            <li>Drag shapes to canvas</li>
            <li>Double-click to edit text</li>
            <li>Drag from handles to connect</li>
            <li>Select + Delete to remove</li>
            <li>Ctrl+Z / Ctrl+Y for undo/redo</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default memo(Sidebar);
