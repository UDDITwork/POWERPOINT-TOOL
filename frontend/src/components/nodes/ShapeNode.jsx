import { memo, useState, useCallback } from 'react';
import { Handle, Position, NodeResizer } from 'reactflow';

const ShapeNode = ({ data, selected, id }) => {
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

  const fill = data.backgroundColor || '#ffffff';
  const stroke = data.borderColor || '#333333';
  const strokeWidth = data.borderWidth || 2;
  const textColor = data.textColor || '#333333';
  const fontSize = data.fontSize || 14;

  const renderContent = () => {
    if (isEditing) {
      return (
        <textarea
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          autoFocus
          style={{
            width: '90%',
            height: '80%',
            border: 'none',
            background: 'transparent',
            textAlign: 'center',
            resize: 'none',
            fontSize: fontSize,
            color: textColor,
            fontFamily: 'inherit',
            outline: 'none',
          }}
        />
      );
    }
    return (
      <div
        onDoubleClick={handleDoubleClick}
        style={{
          width: '100%',
          textAlign: 'center',
          cursor: 'text',
          wordBreak: 'break-word',
          fontSize: fontSize,
          color: textColor,
          padding: '4px',
        }}
      >
        {label || ''}
      </div>
    );
  };

  const SVGShape = ({ children, viewBox = "0 0 100 100" }) => (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <svg width="100%" height="100%" viewBox={viewBox} preserveAspectRatio="none">
        {children}
      </svg>
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '80%',
        height: '70%',
      }}>
        {renderContent()}
      </div>
    </div>
  );

  const renderShape = () => {
    const shape = data.shape || 'rectangle';

    // Basic div-based shapes
    const divStyle = {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: fill,
      borderColor: stroke,
      borderWidth: strokeWidth,
      borderStyle: 'solid',
      padding: '8px',
      boxSizing: 'border-box',
      overflow: 'hidden',
    };

    switch (shape) {
      // ===== BASIC SHAPES =====
      case 'rectangle':
      case 'process':
      case 'square':
        return <div style={{ ...divStyle, borderRadius: 2 }}>{renderContent()}</div>;

      case 'roundedRectangle':
      case 'terminator':
        return <div style={{ ...divStyle, borderRadius: 20 }}>{renderContent()}</div>;

      case 'circle':
      case 'connector':
      case 'or':
        return <div style={{ ...divStyle, borderRadius: '50%' }}>{renderContent()}</div>;

      case 'oval':
        return <div style={{ ...divStyle, borderRadius: '50%' }}>{renderContent()}</div>;

      case 'diamond':
      case 'decision':
        return (
          <SVGShape>
            <polygon points="50,2 98,50 50,98 2,50" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'triangle':
      case 'extract':
        return (
          <SVGShape>
            <polygon points="50,5 95,95 5,95" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'triangleDown':
      case 'merge':
        return (
          <SVGShape>
            <polygon points="5,5 95,5 50,95" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'pentagon':
      case 'offPageConnector':
        return (
          <SVGShape>
            <polygon points="50,2 98,38 80,98 20,98 2,38" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'hexagon':
      case 'preparation':
        return (
          <SVGShape>
            <polygon points="25,2 75,2 98,50 75,98 25,98 2,50" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'octagon':
        return (
          <SVGShape>
            <polygon points="30,2 70,2 98,30 98,70 70,98 30,98 2,70 2,30" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'star':
        return (
          <SVGShape>
            <polygon points="50,2 61,35 98,35 68,57 79,91 50,70 21,91 32,57 2,35 39,35" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'star4':
        return (
          <SVGShape>
            <polygon points="50,2 60,40 98,50 60,60 50,98 40,60 2,50 40,40" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'cross':
      case 'plus':
        return (
          <SVGShape>
            <polygon points="35,2 65,2 65,35 98,35 98,65 65,65 65,98 35,98 35,65 2,65 2,35 35,35" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      // ===== FLOWCHART SHAPES =====
      case 'parallelogram':
      case 'data':
        return (
          <SVGShape>
            <polygon points="20,2 98,2 80,98 2,98" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'document':
        return (
          <SVGShape>
            <path d="M2,2 L98,2 L98,85 Q75,70 50,85 Q25,100 2,85 Z" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'multiDocument':
        return (
          <SVGShape>
            <path d="M8,8 L92,8 L92,75 Q72,63 52,75 Q32,87 12,75 L12,15 L8,15 Z" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <path d="M4,4 L4,12 M96,4 L96,12" stroke={stroke} strokeWidth={strokeWidth} fill="none" />
            <rect x="4" y="2" width="92" height="8" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'predefinedProcess':
        return (
          <SVGShape>
            <rect x="2" y="2" width="96" height="96" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="12" y1="2" x2="12" y2="98" stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="88" y1="2" x2="88" y2="98" stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'internalStorage':
        return (
          <SVGShape>
            <rect x="2" y="2" width="96" height="96" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="2" y1="20" x2="98" y2="20" stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="20" y1="2" x2="20" y2="98" stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'manualInput':
        return (
          <SVGShape>
            <polygon points="2,20 98,2 98,98 2,98" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'manualOperation':
        return (
          <SVGShape>
            <polygon points="2,2 98,2 85,98 15,98" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'storedData':
        return (
          <SVGShape>
            <path d="M15,2 L98,2 Q85,50 98,98 L15,98 Q2,50 15,2" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'delay':
        return (
          <SVGShape>
            <path d="M2,2 L70,2 Q98,50 70,98 L2,98 Z" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'summing':
        return (
          <SVGShape>
            <circle cx="50" cy="50" r="46" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="50" y1="10" x2="50" y2="90" stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="10" y1="50" x2="90" y2="50" stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      // ===== ARROWS =====
      case 'arrowRight':
        return (
          <SVGShape>
            <polygon points="2,30 70,30 70,10 98,50 70,90 70,70 2,70" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'arrowLeft':
        return (
          <SVGShape>
            <polygon points="98,30 30,30 30,10 2,50 30,90 30,70 98,70" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'arrowUp':
        return (
          <SVGShape>
            <polygon points="30,98 30,30 10,30 50,2 90,30 70,30 70,98" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'arrowDown':
        return (
          <SVGShape>
            <polygon points="30,2 30,70 10,70 50,98 90,70 70,70 70,2" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'arrowBidirectional':
        return (
          <SVGShape>
            <polygon points="2,50 20,25 20,40 80,40 80,25 98,50 80,75 80,60 20,60 20,75" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'chevronRight':
        return (
          <SVGShape>
            <polygon points="2,2 75,2 98,50 75,98 2,98 25,50" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'chevronLeft':
        return (
          <SVGShape>
            <polygon points="98,2 25,2 2,50 25,98 98,98 75,50" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'arrowPentagon':
        return (
          <SVGShape>
            <polygon points="2,20 75,20 98,50 75,80 2,80" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      // ===== CALLOUTS =====
      case 'calloutRect':
        return (
          <SVGShape>
            <path d="M2,2 L98,2 L98,70 L40,70 L30,98 L35,70 L2,70 Z" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'calloutRounded':
        return (
          <SVGShape>
            <path d="M15,2 L85,2 Q98,2 98,15 L98,55 Q98,68 85,68 L40,68 L30,95 L35,68 L15,68 Q2,68 2,55 L2,15 Q2,2 15,2" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'calloutOval':
        return (
          <SVGShape>
            <ellipse cx="50" cy="40" rx="46" ry="36" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <polygon points="35,70 45,95 50,70" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'calloutCloud':
      case 'cloud':
        return (
          <SVGShape>
            <path d="M25,70 Q5,70 10,50 Q2,35 20,30 Q15,10 40,15 Q50,2 70,15 Q95,10 90,35 Q98,50 85,60 Q90,75 70,70 Q50,80 25,70" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      // ===== CONTAINERS =====
      case 'cylinder':
      case 'database':
      case 'can':
        return (
          <SVGShape>
            <ellipse cx="50" cy="15" rx="46" ry="12" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <rect x="4" y="15" width="92" height="70" fill={fill} stroke="none" />
            <line x1="4" y1="15" x2="4" y2="85" stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="96" y1="15" x2="96" y2="85" stroke={stroke} strokeWidth={strokeWidth} />
            <ellipse cx="50" cy="85" rx="46" ry="12" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'cube':
        return (
          <SVGShape>
            <polygon points="15,25 85,25 85,95 15,95" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <polygon points="15,25 30,5 98,5 85,25" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <polygon points="85,25 98,5 98,75 85,95" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'folder':
        return (
          <SVGShape>
            <path d="M2,20 L2,95 L98,95 L98,20 L45,20 L40,8 L2,8 Z" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'card':
        return (
          <SVGShape>
            <polygon points="20,2 98,2 98,98 2,98 2,20" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'frame':
        return (
          <SVGShape>
            <rect x="2" y="2" width="96" height="96" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <rect x="12" y="12" width="76" height="76" fill="none" stroke={stroke} strokeWidth={strokeWidth/2} />
          </SVGShape>
        );

      // ===== SYMBOLS =====
      case 'lightning':
        return (
          <SVGShape>
            <polygon points="55,2 20,45 45,45 30,98 80,40 50,40 70,2" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'heart':
        return (
          <SVGShape>
            <path d="M50,90 Q2,50 20,20 Q35,2 50,20 Q65,2 80,20 Q98,50 50,90" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'gear':
        return (
          <SVGShape>
            <path d="M45,5 L55,5 L58,15 L68,10 L75,20 L65,28 L72,38 L82,38 L85,48 L75,52 L80,62 L88,68 L82,78 L72,72 L65,82 L68,92 L58,95 L55,85 L45,85 L42,95 L32,92 L35,82 L28,72 L18,78 L12,68 L20,62 L25,52 L15,48 L18,38 L28,38 L35,28 L25,20 L32,10 L42,15 Z" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <circle cx="50" cy="50" r="15" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'shield':
        return (
          <SVGShape>
            <path d="M50,2 L95,15 L95,45 Q95,80 50,98 Q5,80 5,45 L5,15 Z" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
          </SVGShape>
        );

      case 'checkmark':
        return (
          <SVGShape>
            <rect x="2" y="2" width="96" height="96" rx="10" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <polyline points="20,50 40,70 80,30" fill="none" stroke={stroke} strokeWidth={strokeWidth * 2} strokeLinecap="round" strokeLinejoin="round" />
          </SVGShape>
        );

      case 'xmark':
        return (
          <SVGShape>
            <rect x="2" y="2" width="96" height="96" rx="10" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="25" y1="25" x2="75" y2="75" stroke={stroke} strokeWidth={strokeWidth * 2} strokeLinecap="round" />
            <line x1="75" y1="25" x2="25" y2="75" stroke={stroke} strokeWidth={strokeWidth * 2} strokeLinecap="round" />
          </SVGShape>
        );

      case 'warning':
        return (
          <SVGShape>
            <polygon points="50,5 95,90 5,90" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <line x1="50" y1="35" x2="50" y2="60" stroke={stroke} strokeWidth={strokeWidth * 2} strokeLinecap="round" />
            <circle cx="50" cy="75" r="4" fill={stroke} />
          </SVGShape>
        );

      case 'info':
        return (
          <SVGShape>
            <circle cx="50" cy="50" r="46" fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
            <circle cx="50" cy="25" r="5" fill={stroke} />
            <line x1="50" y1="40" x2="50" y2="75" stroke={stroke} strokeWidth={strokeWidth * 2} strokeLinecap="round" />
          </SVGShape>
        );

      // ===== LINES (rendered as shapes) =====
      case 'line':
      case 'lineArrow':
      case 'lineDouble':
        return (
          <SVGShape>
            <line x1="5" y1="50" x2="95" y2="50" stroke={stroke} strokeWidth={strokeWidth * 2} />
            {(shape === 'lineArrow' || shape === 'lineDouble') && (
              <polygon points="95,50 80,40 80,60" fill={stroke} />
            )}
            {shape === 'lineDouble' && (
              <polygon points="5,50 20,40 20,60" fill={stroke} />
            )}
          </SVGShape>
        );

      // Default fallback
      default:
        return <div style={{ ...divStyle, borderRadius: 4 }}>{renderContent()}</div>;
    }
  };

  return (
    <>
      <NodeResizer
        minWidth={50}
        minHeight={50}
        isVisible={selected}
        lineClassName="resize-line"
        handleClassName="resize-handle"
      />

      <Handle type="target" position={Position.Top} id="top" />
      <Handle type="target" position={Position.Left} id="left" />
      <Handle type="source" position={Position.Bottom} id="bottom" />
      <Handle type="source" position={Position.Right} id="right" />

      {renderShape()}
    </>
  );
};

export default memo(ShapeNode);
