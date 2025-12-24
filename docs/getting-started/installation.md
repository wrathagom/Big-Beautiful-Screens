# Installation

Big Beautiful Screens can be deployed in several ways depending on your needs.

## Docker (Recommended)

The easiest way to run Big Beautiful Screens is with Docker:

```bash
docker run -d \
  -p 8000:8000 \
  -v screens_data:/app/data \
  ghcr.io/wrathagom/big-beautiful-screens
```

Or with Docker Compose:

```yaml
# docker-compose.yml
version: '3.8'
services:
  screens:
    image: ghcr.io/wrathagom/big-beautiful-screens
    ports:
      - "8000:8000"
    volumes:
      - screens_data:/app/data

volumes:
  screens_data:
```

```bash
docker-compose up -d
```

## Manual Installation

### Prerequisites

- Python 3.11 or higher
- pip

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/wrathagom/Big-Beautiful-Screens.git
   cd Big-Beautiful-Screens
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

The server will be available at `http://localhost:8000`.

## Cloud Deployment

### Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/...)

1. Click the button above or create a new project
2. Connect your GitHub repository
3. Railway will auto-detect the Dockerfile and deploy

### Render

1. Create a new Web Service
2. Connect your GitHub repository
3. Use these settings:
   - **Build Command**: (leave empty, uses Dockerfile)
   - **Start Command**: (leave empty, uses Dockerfile)

### Fly.io

```bash
fly launch
fly deploy
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SQLITE_PATH` | Path to SQLite database | `data/screens.db` |
| `HOST` | Host to bind to | `0.0.0.0` |
| `PORT` | Port to bind to | `8000` |

## Verify Installation

After starting the server, verify it's working:

```bash
# Health check
curl http://localhost:8000/health

# Create a test screen
curl -X POST http://localhost:8000/api/v1/screens
```

Visit `http://localhost:8000/admin/screens` to access the admin dashboard.
