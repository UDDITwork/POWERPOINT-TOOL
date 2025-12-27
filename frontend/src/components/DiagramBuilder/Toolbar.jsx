import { memo } from 'react';
import './Toolbar.css';

const Toolbar = ({
  selectedNode,
  onStyleChange,
  onUndo,
  onRedo,
  onDelete,
  onExport,
  onSave,
  onLoad,
  canUndo,
  canRedo,
}) => {
  const colors = [
    '#ffffff', '#f3f4f6', '#fef3c7', '#d1fae5', '#dbeafe',
    '#ede9fe', '#fce7f3', '#fee2e2', '#ffedd5', '#e0e7ff'
  ];

  const borderColors = [
    '#333333', '#6b7280', '#f59e0b', '#10b981', '#3b82f6',
    '#8b5cf6', '#ec4899', '#ef4444', '#f97316', '#6366f1'
  ];

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button
          className="toolbar-btn"
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Ctrl+Z)"
        >
          ↩
        </button>
        <button
          className="toolbar-btn"
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Ctrl+Y)"
        >
          ↪
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button
          className="toolbar-btn"
          onClick={onDelete}
          disabled={!selectedNode}
          title="Delete (Del)"
        >
          🗑
        </button>
      </div>

      <div className="toolbar-divider" />

      {selectedNode && (
        <>
          <div className="toolbar-group">
            <span className="toolbar-label">Fill:</span>
            <div className="color-picker">
              {colors.map((color) => (
                <button
                  key={color}
                  className="color-swatch"
                  style={{ backgroundColor: color }}
                  onClick={() => onStyleChange('backgroundColor', color)}
                  title={color}
                />
              ))}
            </div>
          </div>

          <div className="toolbar-divider" />

          <div className="toolbar-group">
            <span className="toolbar-label">Border:</span>
            <div className="color-picker">
              {borderColors.map((color) => (
                <button
                  key={color}
                  className="color-swatch"
                  style={{ backgroundColor: color }}
                  onClick={() => onStyleChange('borderColor', color)}
                  title={color}
                />
              ))}
            </div>
          </div>

          <div className="toolbar-divider" />

          <div className="toolbar-group">
            <span className="toolbar-label">Border Width:</span>
            <select
              className="toolbar-select"
              value={selectedNode?.data?.borderWidth || 2}
              onChange={(e) => onStyleChange('borderWidth', parseInt(e.target.value))}
            >
              <option value="1">1px</option>
              <option value="2">2px</option>
              <option value="3">3px</option>
              <option value="4">4px</option>
            </select>
          </div>

          <div className="toolbar-divider" />
        </>
      )}

      <div className="toolbar-spacer" />

      <div className="toolbar-group">
        <button className="toolbar-btn" onClick={onSave} title="Save Diagram">
          💾 Save
        </button>
        <button className="toolbar-btn" onClick={onLoad} title="Load Diagram">
          📂 Load
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button className="toolbar-btn export-btn" onClick={() => onExport('pptx')} title="Export as PowerPoint (Editable)">
          📊 PPTX
        </button>
        <button className="toolbar-btn" onClick={() => onExport('json')} title="Export as JSON">
          📄 JSON
        </button>
      </div>
    </div>
  );
};

export default memo(Toolbar);
