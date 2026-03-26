#!/bin/bash
# Start the LinkD Agent web application.
#
# Usage: ./start.sh [react|dev|gradio]
#   react   - Production: FastAPI serves API + React build on single port (default)
#   dev     - Development: separate FastAPI (hot reload) + Vite dev server
#   gradio  - Legacy Gradio interface (app.py)
#
# Environment variables:
#   PORT           - Server port for react mode (default: 8000)
#   BACKEND_PORT   - Backend port for dev mode (default: 8000)
#   FRONTEND_PORT  - Frontend port for dev mode (default: 5173)
#   CONDA_ENV      - Conda environment name (default: ttdrug)

MODE="${1:-react}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONDA_ENV="${CONDA_ENV:-ttdrug}"

kill_port() {
    local PORT=$1
    local PID=$(lsof -ti :"$PORT" 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "Killing process on port $PORT (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 1
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID" 2>/dev/null
    fi
}

build_frontend() {
    echo "Checking frontend build..."
    cd "$SCRIPT_DIR/frontend"

    # Install deps if node_modules missing
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        conda run -n "$CONDA_ENV" npm install
    fi

    # Build if dist missing or source is newer
    if [ ! -d "dist" ] || [ "src" -nt "dist" ]; then
        echo "Building frontend..."
        conda run -n "$CONDA_ENV" npm run build
    else
        echo "Frontend build is up to date."
    fi
}

# ============================================================

if [ "$MODE" = "react" ]; then
    PORT="${PORT:-8000}"
    kill_port "$PORT"
    build_frontend

    echo ""
    echo "=========================================="
    echo "  LinkD Agent"
    echo "  URL:      http://localhost:$PORT"
    echo "  API docs: http://localhost:$PORT/docs"
    echo "=========================================="
    echo ""

    cd "$SCRIPT_DIR/backend"
    exec python -m uvicorn main:app --host 0.0.0.0 --port "$PORT"

elif [ "$MODE" = "dev" ]; then
    BACKEND_PORT="${BACKEND_PORT:-8000}"
    FRONTEND_PORT="${FRONTEND_PORT:-5173}"
    kill_port "$BACKEND_PORT"
    kill_port "$FRONTEND_PORT"

    # Install frontend deps if needed
    if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
        echo "Installing frontend dependencies..."
        cd "$SCRIPT_DIR/frontend" && conda run -n "$CONDA_ENV" npm install
    fi

    echo "Starting backend (hot reload) on port $BACKEND_PORT..."
    cd "$SCRIPT_DIR/backend"
    python -m uvicorn main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
    BACKEND_PID=$!

    echo "Starting frontend dev server on port $FRONTEND_PORT..."
    cd "$SCRIPT_DIR/frontend"
    npm run dev -- --port "$FRONTEND_PORT" &
    FRONTEND_PID=$!

    echo ""
    echo "=========================================="
    echo "  LinkD Agent (dev mode)"
    echo "  Frontend: http://localhost:$FRONTEND_PORT"
    echo "  Backend:  http://localhost:$BACKEND_PORT"
    echo "  API docs: http://localhost:$BACKEND_PORT/docs"
    echo "=========================================="
    echo ""
    echo "Press Ctrl+C to stop."

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
    wait

elif [ "$MODE" = "gradio" ]; then
    PORT="${GRADIO_SERVER_PORT:-7860}"
    kill_port "$PORT"
    cd "$SCRIPT_DIR"
    export GRADIO_SERVER_PORT="$PORT"
    echo "Starting Gradio on http://localhost:$PORT ..."
    exec python app.py

else
    echo "Usage: ./start.sh [react|dev|gradio]"
    echo "  react   - Production mode (default)"
    echo "  dev     - Development mode with hot reload"
    echo "  gradio  - Legacy Gradio interface"
    exit 1
fi
