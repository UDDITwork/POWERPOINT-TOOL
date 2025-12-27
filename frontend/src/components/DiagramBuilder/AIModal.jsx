import { useState, memo } from 'react';
import './AIModal.css';

const AIModal = ({ isOpen, onClose, onGenerate, isLoading, progress, logs }) => {
  const [prompt, setPrompt] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim()) {
      onGenerate(prompt);
    }
  };

  const examplePrompts = [
    "Create a flowchart showing user login process with authentication and error handling",
    "Design a system architecture with web server, database, and cache components",
    "Make an organizational chart with CEO, CTO, and their teams",
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Generate Diagram with AI</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <label className="modal-label">
              Describe your diagram:
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Example: Create a flowchart showing the user registration process with email verification..."
              rows={5}
              disabled={isLoading}
              className="modal-textarea"
            />

            <div className="example-prompts">
              <span className="example-label">Try an example:</span>
              {examplePrompts.map((example, index) => (
                <button
                  key={index}
                  type="button"
                  className="example-btn"
                  onClick={() => setPrompt(example)}
                  disabled={isLoading}
                >
                  {example.substring(0, 40)}...
                </button>
              ))}
            </div>

            {isLoading && (
              <div className="progress-section">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="progress-text">{progress}% - Generating diagram...</span>

                {logs.length > 0 && (
                  <div className="logs-container">
                    {logs.slice(-5).map((log, index) => (
                      <div key={index} className="log-entry">{log}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="modal-btn cancel-btn"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="modal-btn generate-btn"
              disabled={isLoading || !prompt.trim()}
            >
              {isLoading ? 'Generating...' : 'Generate Diagram'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default memo(AIModal);
