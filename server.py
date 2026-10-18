"""
SmartDrive - Web Server Launcher
Starts the FastAPI backend + React frontend on one port.

Usage (from the project folder):
    python server.py                 # http://127.0.0.1:8000  (opens your browser)
    python server.py --port 9000 --no-browser
"""
import argparse, threading, webbrowser

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SmartDrive web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--storage", default=None, help="Storage folder (default: ./storage)")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    try:
        import uvicorn
        from api.main import create_app
    except ImportError as e:
        raise SystemExit(f"Missing dependency ({e.name}). Run:  pip install -r requirements.txt")

    app = create_app(storage_dir=args.storage)
    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}"
    print(f"SmartDrive running at {url}   (API docs: {url}/docs)   Ctrl+C to stop")
    if not args.no_browser: threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")

if __name__ == "__main__":
    main()
