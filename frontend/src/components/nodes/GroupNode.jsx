import { memo, useState, useCallback } from 'react';
import { Handle, Position, NodeResizer } from 'reactflow';

/**
 * GroupNode - A container node for grouping related elements.
 *
 * Features:
 * - Dashed border (default gray)
 * - Label at top-left
 * - Transparent background
 * - Children nodes are positioned inside via React Flow's parentNode
 */
const GroupNode = ({ data, selected, id }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [label, setLabel] = useState(data.label || '');

  const handleDoubleClick = useCallback(() => {
    setIsEditing(true);
  }, []);

  const handleBlur = useCallback(() => {
    setIsEditing(false);
    if (data.onLabelChange) {
      data.onLabelChange(id, label);
    }
  }, [data, id, label]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleBlur();
    }
  }, [handleBlur]);

  // Container styling
  const borderColor = data.borderColor || '#666666';
  const borderWidth = data.borderWidth || 2;
  const textColor = data.textColor || '#333333';
  const fontSize = data.fontSize || 12;
  const backgroundColor = data.backgroundColor || 'rgba(240, 240, 240, 0.3)';

  const containerStyle = {
    width: '100%',
    height: '100%',
    border: `${borderWidth}px dashed ${borderColor}`,
    borderRadius: 8,
    backgroundColor: backgroundColor,
    padding: '8px',
    boxSizing: 'border-box',
    position: 'relative',
  };

  const labelStyle = {
    position: 'absolute',
    top: 8,
    left: 8,
    fontSize: fontSize,
    fontWeight: 'bold',
    color: textColor,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    padding: '2px 8px',
    borderRadius: 4,
    cursor: 'text',
    maxWidth: 'calc(100% - 20px)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  };

  const editInputStyle = {
    width: '200px',
    border: '1px solid #3b82f6',
    borderRadius: 4,
    padding: '2px 6px',
    fontSize: fontSize,
    fontWeight: 'bold',
    color: textColor,
    outline: 'none',
    background: 'white',
  };

  const renderLabel = () => {
    if (isEditing) {
      return (
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          autoFocus
          style={editInputStyle}
        />
      );
    }

    return (
      <div onDoubleClick={handleDoubleClick} style={labelStyle}>
        {label || 'Group'}
      </div>
    );
  };

  return (
    <>
      <NodeResizer
        minWidth={150}
        minHeight={100}
        isVisible={selected}
        lineClassName="resize-line"
        handleClassName="resize-handle"
      />

      {/* Handles for connections to/from the container */}
      <Handle type="target" position={Position.Top} id="top" />
      <Handle type="target" position={Position.Left} id="left" />
      <Handle type="source" position={Position.Bottom} id="bottom" />
      <Handle type="source" position={Position.Right} id="right" />

      <div style={containerStyle}>
        {renderLabel()}
        {/* Children are rendered by React Flow using parentNode relationship */}
      </div>
    </>
  );
};

export default memo(GroupNode);
