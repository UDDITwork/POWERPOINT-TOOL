import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [prompt, setPrompt] = useState('')
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState([])  // Store all processing logs

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!prompt.trim()) return

    setLoading(true)
    setError(null)
    setStatus(null)
    setJobId(null)
    setLogs([])  // Clear previous logs

    try {
      const response = await axios.post(`${API_URL}/api/diagram/create`, {
        prompt: prompt,
        quality: 'high'
      })

      setJobId(response.data.job_id)
      pollStatus(response.data.job_id)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create diagram')
      setLoading(false)
    }
  }

  const pollStatus = async (id) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/api/diagram/status/${id}`)
        setStatus(response.data)

        // Add status to logs
        const timestamp = new Date().toLocaleTimeString()
        const logEntry = `[${timestamp}] ${response.data.message || 'Processing...'} (${response.data.progress || 0}%)`
        setLogs(prevLogs => {
          // Avoid duplicate logs
          if (prevLogs[prevLogs.length - 1] !== logEntry) {
            return [...prevLogs, logEntry]
          }
          return prevLogs
        })

        if (response.data.status === 'completed') {
          clearInterval(interval)
          setLoading(false)
          setLogs(prevLogs => [...prevLogs, `[${timestamp}] ✅ Diagram ready for download!`])
        } else if (response.data.status === 'failed') {
          clearInterval(interval)
          setError(response.data.error || 'Diagram generation failed')
          setLoading(false)
          setLogs(prevLogs => [...prevLogs, `[${timestamp}] ❌ Error: ${response.data.error}`])
        }
      } catch (err) {
        clearInterval(interval)
        setError('Failed to check status')
        setLoading(false)
        const timestamp = new Date().toLocaleTimeString()
        setLogs(prevLogs => [...prevLogs, `[${timestamp}] ❌ Network error: ${err.message}`])
      }
    }, 2000)
  }

  const handleDownload = () => {
    if (jobId) {
      window.open(`${API_URL}/api/diagram/download/${jobId}.pptx`, '_blank')
    }
  }

  return (
    <div className="App">
      <div className="container">
        <div className="header">
          <h1>AI Patent Diagram Generator</h1>
          <p>Generate professional, editable PowerPoint diagrams from text descriptions</p>
        </div>

        <form className="form" onSubmit={handleSubmit}>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your diagram...&#10;&#10;Example:&#10;Create a computer system with:&#10;- Computer System (100) containing:&#10;  - Processor (110)&#10;  - Memory (120) containing:&#10;    - Cache (122)&#10;    - RAM (124)&#10;  - Storage (130)"
            rows={12}
            disabled={loading}
          />

          <button type="submit" disabled={loading || !prompt.trim()}>
            {loading ? 'Generating...' : 'Generate Diagram'}
          </button>
        </form>

        {loading && status && (
          <div className="status-card">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${status.progress || 0}%` }}
              />
            </div>
            <div className="status-text">
              <span>{status.message || 'Processing...'}</span>
              <span className="progress-percent">{status.progress || 0}%</span>
            </div>
            {status.error && (
              <div className="error-details" style={{marginTop: '10px', fontSize: '12px', color: '#c33'}}>
                <strong>Debug Info:</strong><br/>
                {status.error}
              </div>
            )}
          </div>
        )}

        {logs.length > 0 && (
          <div className="logs-card" style={{
            marginTop: '20px',
            padding: '15px',
            backgroundColor: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '8px',
            maxHeight: '300px',
            overflowY: 'auto'
          }}>
            <h4 style={{marginTop: 0, color: '#9ca3af', fontSize: '14px'}}>Processing Logs:</h4>
            <div style={{fontFamily: 'monospace', fontSize: '12px', color: '#e5e7eb'}}>
              {logs.map((log, index) => (
                <div key={index} style={{padding: '4px 0', borderBottom: '1px solid #2a2a2a'}}>
                  {log}
                </div>
              ))}
            </div>
          </div>
        )}

        {status?.status === 'completed' && (
          <div className="success-card">
            <h3>Diagram Generated Successfully!</h3>
            <div className="details">
              <span>Elements: {status.element_count || 0}</span>
              <span>Type: {status.diagram_type || 'diagram'}</span>
            </div>
            <button className="download-btn" onClick={handleDownload}>
              Download PowerPoint File
            </button>
            <p className="edit-note">
              The downloaded .pptx file is fully editable in Microsoft PowerPoint
            </p>
          </div>
        )}

        {error && (
          <div className="error-card">
            <h3>Error</h3>
            <p>{error}</p>
          </div>
        )}

        <div className="footer">
          <p>Powered by Claude AI + python-pptx</p>
          <p className="small">100% editable PowerPoint output | Patent-quality diagrams</p>
        </div>
      </div>
    </div>
  )
}

export default App
