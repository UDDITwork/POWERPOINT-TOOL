

# 🚀 Quick Start Guide

## Get Running in 5 Minutes

### Prerequisites

- Python 3.11+
- Anthropic API key ([Get one here](https://console.anthropic.com/))
- (Optional) Turso account for production
- (Optional) Pinecone API key for semantic search

---

## Local Development Setup

### 1. **Clone and Navigate**

```bash
cd patent-diagram-ai/backend
```

### 2. **Create Virtual Environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

✅ **All packages are pure Python - no C++ compiler needed!**

### 4. **Configure Environment**

```bash
# Copy example env file
cp ../.env.example .env

# Edit .env and add your API key
# Minimum required:
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 5. **Run the Server**

```bash
python main.py
```

Server starts at: `http://localhost:8000`

API docs: `http://localhost:8000/api/docs`

---

## Test Your First Diagram

### Option 1: Using API Docs (Easy)

1. Open `http://localhost:8000/api/docs`
2. Click on `POST /api/diagram/create`
3. Click "Try it out"
4. Paste this JSON:

```json
{
  "prompt": "Create a flowchart with 3 steps: Input (100), Processing (200), Output (300). Connect them with arrows."
}
```

5. Click "Execute"
6. Copy the `job_id` from response
7. Use `GET /api/diagram/status/{job_id}` to check status
8. When `status: "completed"`, download from the `download_url`

### Option 2: Using curl

```bash
# Create diagram
curl -X POST "http://localhost:8000/api/diagram/create" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a system architecture with server, database, and 3 clients"
  }'

# Output: {"job_id": "abc-123", "status": "queued", ...}

# Check status
curl "http://localhost:8000/api/diagram/status/abc-123"

# Download (when completed)
curl "http://localhost:8000/api/diagram/download/abc-123.pptx" -O
```

### Option 3: Using Python

```python
import requests

# Create diagram
response = requests.post("http://localhost:8000/api/diagram/create", json={
    "prompt": "Create a flowchart with data input, validation, processing, and output"
})

job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# Poll for completion
import time
while True:
    status = requests.get(f"http://localhost:8000/api/diagram/status/{job_id}").json()
    print(f"Status: {status['status']} - {status['progress']}%")

    if status["status"] == "completed":
        download_url = f"http://localhost:8000{status['download_url']}"
        print(f"Download: {download_url}")
        break

    time.sleep(2)
```

---

## Example Prompts

### Flowcharts
```
Create a method flowchart for a patent:
- Step 100: Receive user input
- Step 200: Validate data with decision diamond
- Step 300: Process with AI
- Step 400: Generate output
Add reference numbers and connect with arrows
```

### Block Diagrams
```
Draw a system architecture:
- Central server (100) in the middle
- Database (110) connected to server
- API Gateway (120) connected to server
- Three client devices (200, 210, 220) connecting to API Gateway
Use bidirectional arrows for connections
```

### Network Diagrams
```
Create a network topology:
- Router (100) at top
- Switch (110) below router
- 4 computers (200-230) connected to switch
- Firewall (120) between router and switch
Label all connections
```

---

## Common Issues

### Issue: "AI service not configured"

**Solution:** Make sure `ANTHROPIC_API_KEY` is set in `.env`

```bash
# Check if loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('ANTHROPIC_API_KEY'))"
```

### Issue: "Module not found"

**Solution:** Ensure you're in the venv and installed requirements

```bash
# Activate venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate  # Windows

# Reinstall
pip install -r requirements.txt
```

### Issue: Diagram generation takes too long

**Solution:** This is normal! Claude API + PPTX generation takes 5-15 seconds

- Use the status endpoint to track progress
- `progress` field shows percentage complete

---

## Next Steps

✅ **Local dev working?** Great! Now:

1. **Add Turso for persistence**: See [TURSO_SETUP.md](TURSO_SETUP.md)
2. **Deploy to Cloud Run**: See [CLOUD_RUN_DEPLOY.md](CLOUD_RUN_DEPLOY.md)
3. **Add frontend**: See [frontend/README.md](../frontend/README.md)
4. **(Optional) Add Pinecone**: See [PINECONE_SETUP.md](PINECONE_SETUP.md)

---

## Project Structure

```
patent-diagram-ai/
├── backend/
│   ├── main.py              ← FastAPI app (START HERE)
│   ├── requirements.txt      ← Dependencies
│   ├── .env                  ← Your config (create this)
│   ├── ai/
│   │   └── claude_agent.py   ← Claude integration
│   ├── diagram_engine/
│   │   └── pptx_generator.py ← PPTX creation
│   ├── models/
│   │   └── schemas.py        ← API models
│   └── generated_diagrams/   ← Output files (created automatically)
├── frontend/                 ← React app (optional)
├── docs/                     ← Documentation
└── examples/                 ← Sample prompts
```

---

## Quick Commands Cheat Sheet

```bash
# Start server
python main.py

# Start with auto-reload
uvicorn main:app --reload

# Run on different port
uvicorn main:app --port 8080

# View logs
tail -f *.log

# Test health
curl http://localhost:8000/api/health

# View API docs
open http://localhost:8000/api/docs
```

---

## Support

- **API Documentation**: http://localhost:8000/api/docs
- **Architecture**: See [../ARCHITECTURE.md](../ARCHITECTURE.md)
- **Issues**: GitHub Issues
- **Full README**: See [../README.md](../README.md)

---

**🎉 You're ready to generate patent diagrams with AI!**
