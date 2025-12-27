import { useState, useRef, useEffect } from 'react';
import './AIPromptPanel.css';

const AIPromptPanel = ({
  onGenerate,
  onRefine,
  isLoading,
  progress,
  logs,
  hasDiagram,
  currentDiagramInfo,
}) => {
  const [prompt, setPrompt] = useState('');
  const [mode, setMode] = useState('generate'); // 'generate' or 'refine'
  const logsEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Auto-switch to refine mode when diagram exists
  useEffect(() => {
    if (hasDiagram && mode === 'generate') {
      setMode('refine');
    }
  }, [hasDiagram]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;

    if (mode === 'generate' || !hasDiagram) {
      onGenerate(prompt);
    } else {
      onRefine(prompt);
    }
  };

  const examplePrompts = {
    generate: [
      'Create a flowchart for user authentication with login, validation, and error handling',
      'Block diagram showing a web server connected to database and 3 client devices',
      'Process flow: Input -> Validation -> Processing -> Output with error branch',
      'System architecture with frontend, API gateway, microservices, and database',
    ],
    refine: [
      'Add a logout step after the dashboard',
      'Move the error box to the right side',
      'Change the color of decision nodes to yellow',
      'Add connection labels showing data flow',
      'Make the boxes bigger and add more spacing',
    ],
  };

  const currentExamples = mode === 'generate' ? examplePrompts.generate : examplePrompts.refine;

  return (
    <div className="ai-prompt-panel">
      {/* Header */}
      <div className="panel-header">
        <div className="panel-title">
          <span>AI Diagram Assistant</span>
        </div>
        <div className="panel-subtitle">
          {hasDiagram ? 'Refine your diagram or generate a new one' : 'Describe your diagram to get started'}
        </div>
      </div>

      {/* Mode Toggle */}
      {hasDiagram && (
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === 'generate' ? 'active' : ''}`}
            onClick={() => setMode('generate')}
          >
            New Diagram
          </button>
          <button
            className={`mode-btn ${mode === 'refine' ? 'active' : ''}`}
            onClick={() => setMode('refine')}
          >
            Refine Current
          </button>
        </div>
      )}

      {/* Current Diagram Info */}
      {hasDiagram && mode === 'refine' && currentDiagramInfo && (
        <div className="diagram-info">
          <div className="info-label">Current Diagram:</div>
          <div className="info-content">
            <span className="info-stat">{currentDiagramInfo.nodeCount} shapes</span>
            <span className="info-stat">{currentDiagramInfo.edgeCount} connections</span>
          </div>
        </div>
      )}

      {/* Prompt Input */}
      <form onSubmit={handleSubmit} className="prompt-form">
        <textarea
          className="prompt-input"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={
            mode === 'generate'
              ? 'Describe the diagram you want to create...\n\nExample: Create a flowchart showing user registration process with email verification'
              : 'Describe the changes you want to make...\n\nExample: Add a retry loop after the error state'
          }
          disabled={isLoading}
          rows={6}
        />

        <button
          type="submit"
          className={`submit-btn ${isLoading ? 'loading' : ''}`}
          disabled={!prompt.trim() || isLoading}
        >
          {isLoading ? (
            <>
              <span className="spinner"></span>
              Processing...
            </>
          ) : mode === 'generate' ? (
            'Generate Diagram'
          ) : (
            'Apply Changes'
          )}
        </button>
      </form>

      {/* Progress Section */}
      {isLoading && (
        <div className="progress-section">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <div className="progress-text">{progress}% Complete</div>
        </div>
      )}

      {/* Logs */}
      {logs.length > 0 && (
        <div className="logs-section">
          <div className="logs-header">Activity Log</div>
          <div className="logs-container">
            {logs.map((log, index) => (
              <div key={index} className="log-entry">
                <span className="log-time">{new Date().toLocaleTimeString()}</span>
                <span className="log-message">{log}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {/* Example Prompts */}
      <div className="examples-section">
        <div className="examples-header">
          {mode === 'generate' ? 'Example Prompts' : 'Refinement Ideas'}
        </div>
        <div className="examples-list">
          {currentExamples.map((example, index) => (
            <button
              key={index}
              className="example-btn"
              onClick={() => setPrompt(example)}
              disabled={isLoading}
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Tips Section */}
      <div className="tips-section">
        <div className="tips-header">Pro Tips</div>
        <ul className="tips-list">
          {mode === 'generate' ? (
            <>
              <li>Be specific about the number of steps or components</li>
              <li>Mention the diagram type: flowchart, block diagram, architecture</li>
              <li>Include decision points for branching logic</li>
              <li>Specify colors or styles if needed</li>
            </>
          ) : (
            <>
              <li>Reference specific shapes by their labels</li>
              <li>Describe spatial changes: "move X to the right of Y"</li>
              <li>Ask for style changes: colors, sizes, spacing</li>
              <li>Add or remove connections between shapes</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
};

export default AIPromptPanel;
