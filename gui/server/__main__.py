"""Run the dashboard server: python3 -m gui.server [--port 8765]"""
from .app import serve
from .config import from_args

if __name__ == "__main__":
    serve(from_args())
