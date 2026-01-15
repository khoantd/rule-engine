# Rule Engine API - Quick Start Guide

Get the Rule Engine API running in minutes!

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
python run_api.py
```

Or using uvicorn directly:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 3. Access the API

- **API Server**: http://localhost:8000
- **Interactive Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Quick Test

### Test Rule Execution

```bash
curl -X POST http://localhost:8000/api/v1/rules/execute \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "issue": 35,
      "title": "Superman",
      "publisher": "DC"
    }
  }'
```

### Test Health Check

```bash
curl http://localhost:8000/health
```

### Test Workflow Execution

```bash
curl -X POST http://localhost:8000/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "process_name": "test_process",
    "stages": ["NEW", "INPROGESS", "FINISHED"],
    "data": {
      "id": 1,
      "name": "Test"
    }
  }'
```

## Configuration

### Optional: Enable API Key Authentication

```bash
export API_KEY_ENABLED=true
export API_KEY=your-secret-api-key
python run_api.py
```

Then include the API key in requests:

```bash
curl -H "X-API-Key: your-secret-api-key" \
  -X POST http://localhost:8000/api/v1/rules/execute \
  -H "Content-Type: application/json" \
  -d '{"data": {...}}'
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Server host |
| `API_PORT` | `8000` | Server port |
| `API_KEY_ENABLED` | `false` | Enable API key auth |
| `API_KEY` | - | API key (if enabled) |

## Documentation

For detailed API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

For interactive API documentation, visit http://localhost:8000/docs

## Python Client Example

```python
import requests

# Execute rules
response = requests.post(
    'http://localhost:8000/api/v1/rules/execute',
    json={
        'data': {
            'issue': 35,
            'title': 'Superman',
            'publisher': 'DC'
        }
    }
)

result = response.json()
print(f"Total Points: {result['total_points']}")
print(f"Action: {result['action_recommendation']}")
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, change it:

```bash
export API_PORT=8080
python run_api.py
```

### Module Not Found

Make sure you're in the project root directory and dependencies are installed:

```bash
pip install -r requirements.txt
```

### Configuration Errors

Check that configuration files exist in `config/` and `data/input/` directories.

For more help, see the full [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

