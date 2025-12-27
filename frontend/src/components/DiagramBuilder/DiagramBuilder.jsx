import { useState, useCallback, useRef, useMemo } from 'react';
import ReactFlow, {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

import ShapeNode from '../nodes/ShapeNode';
import Sidebar from './Sidebar';
import Toolbar from './Toolbar';
import AIPromptPanel from './AIPromptPanel';
import './DiagramBuilder.css';

import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const nodeTypes = {
  shape: ShapeNode,
};

const defaultEdgeOptions = {
  type: 'smoothstep',
  markerEnd: {
    type: MarkerType.ArrowClosed,
    color: '#333',
  },
  style: {
    strokeWidth: 2,
    stroke: '#333',
  },
};

const DiagramBuilder = () => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [history, setHistory] = useState([{ nodes: [], edges: [] }]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [aiLoading, setAILoading] = useState(false);
  const [aiProgress, setAIProgress] = useState(0);
  const [aiLogs, setAILogs] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  // Save state to history
  const saveToHistory = useCallback((newNodes, newEdges) => {
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({ nodes: newNodes, edges: newEdges });
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  }, [history, historyIndex]);

  // Handle node changes
  const onNodesChange = useCallback((changes) => {
    setNodes((nds) => {
      const newNodes = applyNodeChanges(changes, nds);
      return newNodes;
    });
  }, []);

  // Handle edge changes
  const onEdgesChange = useCallback((changes) => {
    setEdges((eds) => {
      const newEdges = applyEdgeChanges(changes, eds);
      return newEdges;
    });
  }, []);

  // Handle new connections
  const onConnect = useCallback((connection) => {
    setEdges((eds) => {
      const newEdges = addEdge({
        ...connection,
        type: 'smoothstep',
        markerEnd: { type: MarkerType.ArrowClosed, color: '#333' },
        style: { strokeWidth: 2, stroke: '#333' },
      }, eds);
      saveToHistory(nodes, newEdges);
      return newEdges;
    });
  }, [nodes, saveToHistory]);

  // Handle node selection
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Handle label change (defined before onDrop which uses it)
  const handleLabelChange = useCallback((nodeId, newLabel) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, label: newLabel } }
          : node
      )
    );
  }, []);

  // Handle drag over
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop
  const onDrop = useCallback((event) => {
    event.preventDefault();

    const type = event.dataTransfer.getData('application/reactflow');
    console.log('Drop event - shape type:', type);

    if (typeof type === 'undefined' || !type) {
      console.log('No shape type in drop data');
      return;
    }

    if (!reactFlowInstance) {
      console.error('ReactFlow instance not ready');
      return;
    }

    console.log('Creating node of type:', type);

    const position = reactFlowInstance.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    const newNode = {
      id: uuidv4(),
      type: 'shape',
      position,
      data: {
        label: '',
        shape: type,
        backgroundColor: '#ffffff',
        borderColor: '#333333',
        borderWidth: 2,
        textColor: '#333333',
        fontSize: 14,
        onLabelChange: handleLabelChange,
      },
      style: {
        width: 120,
        height: 80,
      },
    };

    setNodes((nds) => {
      const newNodes = [...nds, newNode];
      console.log('Added new node, total nodes:', newNodes.length);
      saveToHistory(newNodes, edges);
      return newNodes;
    });
  }, [reactFlowInstance, edges, saveToHistory, handleLabelChange]);

  // Handle style change
  const handleStyleChange = useCallback((property, value) => {
    if (!selectedNode) return;

    setNodes((nds) => {
      const newNodes = nds.map((node) =>
        node.id === selectedNode.id
          ? { ...node, data: { ...node.data, [property]: value } }
          : node
      );
      saveToHistory(newNodes, edges);
      return newNodes;
    });

    setSelectedNode((prev) => ({
      ...prev,
      data: { ...prev.data, [property]: value },
    }));
  }, [selectedNode, edges, saveToHistory]);

  // Undo
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setNodes(history[newIndex].nodes);
      setEdges(history[newIndex].edges);
    }
  }, [history, historyIndex]);

  // Redo
  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      setHistoryIndex(newIndex);
      setNodes(history[newIndex].nodes);
      setEdges(history[newIndex].edges);
    }
  }, [history, historyIndex]);

  // Delete selected
  const handleDelete = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => {
        const newNodes = nds.filter((n) => n.id !== selectedNode.id);
        setEdges((eds) => {
          const newEdges = eds.filter(
            (e) => e.source !== selectedNode.id && e.target !== selectedNode.id
          );
          saveToHistory(newNodes, newEdges);
          return newEdges;
        });
        return newNodes;
      });
      setSelectedNode(null);
    }
  }, [selectedNode, saveToHistory]);

  // Convert React Flow nodes to backend spec format
  // Note: Backend expects positions in inches (slide is 10" x 7.5")
  // ReactFlow uses pixels, so we need to convert
  const PIXELS_PER_INCH = 96;
  const SLIDE_WIDTH_INCHES = 10;
  const SLIDE_HEIGHT_INCHES = 7.5;

  const convertNodesToSpec = useCallback((nodes, edges) => {
    // Map frontend shape names to backend shape names (snake_case)
    const shapeNameMap = {
      'roundedRectangle': 'rounded_rectangle',
      'triangleDown': 'inverted_triangle',
      'star4': 'star_4_point',
      'arrowRight': 'right_arrow',
      'arrowLeft': 'left_arrow',
      'arrowUp': 'up_arrow',
      'arrowDown': 'down_arrow',
      'arrowBidirectional': 'left_right_arrow',
      'chevronRight': 'chevron',
      'chevronLeft': 'chevron',
      'calloutRect': 'rectangular_callout',
      'calloutRounded': 'rounded_rectangular_callout',
      'calloutOval': 'oval_callout',
      'calloutCloud': 'cloud_callout',
    };

    // Convert shape elements
    const shapeElements = nodes.map((node) => {
      const frontendShape = node.data.shape || 'rectangle';
      const backendShape = shapeNameMap[frontendShape] || frontendShape.toLowerCase();

      // Convert pixels to inches, with bounds checking
      const xInches = Math.max(0.5, Math.min(SLIDE_WIDTH_INCHES - 1, node.position.x / PIXELS_PER_INCH));
      const yInches = Math.max(0.5, Math.min(SLIDE_HEIGHT_INCHES - 1, node.position.y / PIXELS_PER_INCH));
      const widthInches = Math.max(0.5, (node.style?.width || 120) / PIXELS_PER_INCH);
      const heightInches = Math.max(0.4, (node.style?.height || 80) / PIXELS_PER_INCH);

      return {
        id: node.id,
        type: backendShape,  // Use shape type directly (not 'shape')
        position: {
          x: xInches,
          y: yInches,
        },
        size: {
          width: widthInches,
          height: heightInches,
        },
        text: node.data.label || '',
        style: {
          fill_color: node.data.backgroundColor || '#ffffff',
          line_color: node.data.borderColor || '#333333',
          line_width: node.data.borderWidth || 2,
        },
      };
    });

    // Convert edge connectors - include in elements array as backend expects
    const connectorElements = edges.map((edge) => ({
      id: edge.id,
      type: 'connector',  // Must be 'connector' for backend to recognize
      connector_type: 'elbow',  // 'straight', 'elbow', or 'curve'
      from: edge.source,
      to: edge.target,
      from_side: edge.sourceHandle || 'bottom',
      to_side: edge.targetHandle || 'top',
      style: {
        line_color: '#333333',
        line_width: 2,
      },
      label: edge.label || '',
    }));

    // Combine shapes and connectors into single elements array
    const elements = [...shapeElements, ...connectorElements];

    return {
      metadata: {
        title: 'Diagram Export',
        created_from: 'web_editor',
      },
      elements,
      layout: {
        type: 'manual',
      },
    };
  }, []);

  // Export diagram
  const handleExport = useCallback(async (format) => {
    if (format === 'json') {
      const data = JSON.stringify({ nodes, edges }, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'diagram.json';
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === 'pptx') {
      if (nodes.length === 0) {
        alert('No shapes to export. Add some shapes first!');
        return;
      }

      // Convert canvas nodes/edges to spec format for backend
      const spec = convertNodesToSpec(nodes, edges);

      try {
        // Send to backend for PPTX generation
        const response = await axios.post(`${API_URL}/api/diagram/export-pptx`, {
          spec: spec,
        });

        const jobId = response.data.job_id;

        // Poll for completion
        const pollInterval = setInterval(async () => {
          try {
            const statusResponse = await axios.get(`${API_URL}/api/diagram/status/${jobId}`);

            if (statusResponse.data.status === 'completed') {
              clearInterval(pollInterval);
              // Download the file
              window.open(`${API_URL}/api/diagram/download/${jobId}.pptx`, '_blank');
            } else if (statusResponse.data.status === 'failed') {
              clearInterval(pollInterval);
              alert(`Export failed: ${statusResponse.data.error}`);
            }
          } catch (err) {
            clearInterval(pollInterval);
            alert(`Export error: ${err.message}`);
          }
        }, 1000);
      } catch (err) {
        alert(`Export error: ${err.message}`);
      }
    }
  }, [nodes, edges, convertNodesToSpec]);

  // Save diagram
  const handleSave = useCallback(() => {
    const data = JSON.stringify({ nodes, edges });
    localStorage.setItem('diagram-autosave', data);
    alert('Diagram saved to browser storage!');
  }, [nodes, edges]);

  // Load diagram
  const handleLoad = useCallback(() => {
    const data = localStorage.getItem('diagram-autosave');
    if (data) {
      try {
        const { nodes: loadedNodes, edges: loadedEdges } = JSON.parse(data);
        // Re-attach callbacks
        const nodesWithCallbacks = loadedNodes.map((node) => ({
          ...node,
          data: { ...node.data, onLabelChange: handleLabelChange },
        }));
        setNodes(nodesWithCallbacks);
        setEdges(loadedEdges);
        saveToHistory(nodesWithCallbacks, loadedEdges);
        alert('Diagram loaded!');
      } catch (e) {
        alert('Failed to load diagram');
      }
    } else {
      alert('No saved diagram found');
    }
  }, [handleLabelChange, saveToHistory]);

  // AI Generation using Opus v3 endpoint with extended thinking
  const handleAIGenerate = useCallback(async (prompt) => {
    setAILoading(true);
    setAIProgress(0);
    setAILogs([]);

    try {
      setAILogs((prev) => [...prev, 'Starting AI generation with extended thinking...']);

      // Call backend v3 endpoint (Opus with extended thinking)
      const response = await axios.post(`${API_URL}/api/diagram/create-v3`, {
        prompt: prompt,
        thinking_budget: 16000,
        validate: true,
      });

      const jobId = response.data.job_id;
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);
      setAILogs((prev) => [...prev, `Job started: ${jobId.slice(0, 8)}...`]);

      // Poll for status
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get(`${API_URL}/api/diagram/status/${jobId}`);
          const status = statusResponse.data;

          setAIProgress(status.progress || 0);
          if (status.message) {
            setAILogs((prev) => {
              // Avoid duplicate messages
              if (prev[prev.length - 1] !== status.message) {
                return [...prev, status.message];
              }
              return prev;
            });
          }

          if (status.status === 'completed') {
            clearInterval(pollInterval);

            // Get the diagram spec
            if (status.spec) {
              convertSpecToNodes(status.spec);
              setAILogs((prev) => [...prev, '✅ Diagram generated successfully!']);
            }

            setAILoading(false);
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            setAILogs((prev) => [...prev, `❌ Error: ${status.error}`]);
            setAILoading(false);
          }
        } catch (err) {
          clearInterval(pollInterval);
          setAILogs((prev) => [...prev, `❌ Error: ${err.message}`]);
          setAILoading(false);
        }
      }, 2000);
    } catch (err) {
      setAILogs((prev) => [...prev, `❌ Error: ${err.message}`]);
      setAILoading(false);
    }
  }, []);

  // AI Refinement - refine existing diagram based on feedback
  const handleAIRefine = useCallback(async (refinementPrompt) => {
    if (nodes.length === 0) {
      setAILogs((prev) => [...prev, '⚠️ No diagram to refine. Generate one first.']);
      return;
    }

    setAILoading(true);
    setAIProgress(0);
    setAILogs([]);

    try {
      setAILogs((prev) => [...prev, 'Analyzing refinement request...']);

      // If we have a session, use feedback endpoint; otherwise create new
      if (sessionId) {
        const response = await axios.post(`${API_URL}/api/feedback/submit`, {
          session_id: sessionId,
          feedback_text: refinementPrompt,
        });

        if (response.data.refinement_job_id) {
          const jobId = response.data.refinement_job_id;
          setAILogs((prev) => [...prev, `Refinement job: ${jobId.slice(0, 8)}...`]);

          // Poll for status
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await axios.get(`${API_URL}/api/diagram/status/${jobId}`);
              const status = statusResponse.data;

              setAIProgress(status.progress || 0);
              if (status.message) {
                setAILogs((prev) => {
                  if (prev[prev.length - 1] !== status.message) {
                    return [...prev, status.message];
                  }
                  return prev;
                });
              }

              if (status.status === 'completed') {
                clearInterval(pollInterval);
                if (status.spec) {
                  convertSpecToNodes(status.spec);
                  setAILogs((prev) => [...prev, '✅ Diagram refined successfully!']);
                }
                setAILoading(false);
              } else if (status.status === 'failed') {
                clearInterval(pollInterval);
                setAILogs((prev) => [...prev, `❌ Error: ${status.error}`]);
                setAILoading(false);
              }
            } catch (err) {
              clearInterval(pollInterval);
              setAILogs((prev) => [...prev, `❌ Error: ${err.message}`]);
              setAILoading(false);
            }
          }, 2000);
        }
      } else {
        // No session - generate new diagram with the refinement as prompt
        setAILogs((prev) => [...prev, 'No active session. Creating new diagram...']);
        await handleAIGenerate(refinementPrompt);
      }
    } catch (err) {
      setAILogs((prev) => [...prev, `❌ Error: ${err.message}`]);
      setAILoading(false);
    }
  }, [nodes.length, sessionId, handleAIGenerate]);

  // Convert AI spec (V1 format from backend) to React Flow nodes
  // V1 format has elements array with both shapes and connectors
  // Positions are in INCHES, need to convert to PIXELS
  const convertSpecToNodes = useCallback((spec) => {
    const newNodes = [];
    const newEdges = [];
    const shapeIds = new Set();

    // Map backend shape types to frontend shape types
    const shapeTypeMap = {
      'rectangle': 'rectangle',
      'rounded_rectangle': 'roundedRectangle',
      'oval': 'circle',
      'circle': 'circle',
      'diamond': 'diamond',
      'parallelogram': 'parallelogram',
      'cylinder': 'cylinder',
      'hexagon': 'hexagon',
      'triangle': 'triangle',
      'process': 'rectangle',
      'decision': 'diamond',
      'terminator': 'roundedRectangle',
      'data': 'parallelogram',
      'document': 'rectangle',
      'predefined_process': 'rectangle',
      'database': 'cylinder',
      'cloud': 'cloud',
      'star': 'star',
      'gear': 'gear',
    };

    // Helper to convert hex color (handles both with and without #)
    const normalizeColor = (color) => {
      if (!color) return '#ffffff';
      return color.startsWith('#') ? color : `#${color}`;
    };

    // First pass: collect all shape IDs and create nodes
    if (spec.elements) {
      spec.elements.forEach((element, index) => {
        // Skip connectors in first pass
        if (element.type === 'connector') return;

        const id = element.id || uuidv4();
        shapeIds.add(id);

        // Convert position from inches to pixels
        // Backend sends inches, frontend uses pixels (96 DPI)
        const posX = element.position?.x || 1;
        const posY = element.position?.y || 1;
        const x = posX * PIXELS_PER_INCH;
        const y = posY * PIXELS_PER_INCH;

        // Convert size from inches to pixels
        const widthInches = element.size?.width || 2.5;
        const heightInches = element.size?.height || 1.0;
        const width = widthInches * PIXELS_PER_INCH;
        const height = heightInches * PIXELS_PER_INCH;

        // Map shape type
        const backendType = (element.type || 'rectangle').toLowerCase();
        const frontendShape = shapeTypeMap[backendType] || 'rectangle';

        // Get colors from style
        const style = element.style || {};
        const backgroundColor = normalizeColor(style.fill_color);
        const borderColor = normalizeColor(style.line_color || '333333');

        const node = {
          id,
          type: 'shape',
          position: { x, y },
          data: {
            label: element.text || '',
            shape: frontendShape,
            backgroundColor,
            borderColor,
            borderWidth: style.line_width || 2,
            textColor: '#333333',
            fontSize: 14,
            onLabelChange: handleLabelChange,
          },
          style: { width, height },
        };

        newNodes.push(node);
      });
    }

    // Second pass: create edges from connectors
    if (spec.elements) {
      spec.elements.forEach((element) => {
        if (element.type !== 'connector') return;

        const sourceId = element.from;
        const targetId = element.to;

        // Only add edge if both source and target shapes exist
        if (sourceId && targetId && shapeIds.has(sourceId) && shapeIds.has(targetId)) {
          newEdges.push({
            id: element.id || uuidv4(),
            source: sourceId,
            target: targetId,
            type: 'smoothstep',
            markerEnd: { type: MarkerType.ArrowClosed, color: '#333' },
            style: { strokeWidth: 2, stroke: '#333' },
            label: element.label || '',
          });
        } else {
          console.warn(`Skipping connector ${element.id}: source=${sourceId}, target=${targetId}`);
        }
      });
    }

    // Also check for legacy 'connectors' array format
    if (spec.connectors) {
      spec.connectors.forEach((connector) => {
        const sourceId = connector.from;
        const targetId = connector.to;

        if (sourceId && targetId && shapeIds.has(sourceId) && shapeIds.has(targetId)) {
          newEdges.push({
            id: connector.id || uuidv4(),
            source: sourceId,
            target: targetId,
            type: 'smoothstep',
            markerEnd: { type: MarkerType.ArrowClosed, color: '#333' },
            style: { strokeWidth: 2, stroke: '#333' },
            label: connector.label || '',
          });
        }
      });
    }

    console.log(`Converted spec to ${newNodes.length} nodes and ${newEdges.length} edges`);

    setNodes(newNodes);
    setEdges(newEdges);
    saveToHistory(newNodes, newEdges);
  }, [handleLabelChange, saveToHistory]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Delete' || event.key === 'Backspace') {
      handleDelete();
    } else if (event.ctrlKey && event.key === 'z') {
      handleUndo();
    } else if (event.ctrlKey && event.key === 'y') {
      handleRedo();
    }
  }, [handleDelete, handleUndo, handleRedo]);

  // Update selected node reference when nodes change
  const currentSelectedNode = useMemo(() => {
    if (!selectedNode) return null;
    return nodes.find((n) => n.id === selectedNode.id) || null;
  }, [nodes, selectedNode]);

  // Diagram info for the prompt panel
  const currentDiagramInfo = useMemo(() => ({
    nodeCount: nodes.length,
    edgeCount: edges.length,
  }), [nodes.length, edges.length]);

  return (
    <div className="diagram-builder" onKeyDown={handleKeyDown} tabIndex={0}>
      <Toolbar
        selectedNode={currentSelectedNode}
        onStyleChange={handleStyleChange}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onDelete={handleDelete}
        onExport={handleExport}
        onSave={handleSave}
        onLoad={handleLoad}
        canUndo={historyIndex > 0}
        canRedo={historyIndex < history.length - 1}
      />

      <div className="diagram-content">
        <Sidebar />

        <div className="canvas-wrapper" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
          >
            <Background variant="dots" gap={15} size={1} color="#d0d0d0" />
            <Controls />
            <MiniMap
              nodeColor={(n) => n.data?.backgroundColor || '#ffffff'}
              maskColor="rgba(240, 240, 240, 0.8)"
              style={{ background: '#ffffff' }}
            />
          </ReactFlow>
        </div>

        <AIPromptPanel
          onGenerate={handleAIGenerate}
          onRefine={handleAIRefine}
          isLoading={aiLoading}
          progress={aiProgress}
          logs={aiLogs}
          hasDiagram={nodes.length > 0}
          currentDiagramInfo={currentDiagramInfo}
        />
      </div>
    </div>
  );
};

export default DiagramBuilder;
