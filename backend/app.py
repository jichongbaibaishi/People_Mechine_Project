"""Entry point for the student stress app auth/privacy backend."""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path

from auth_backend import Database, make_handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Student stress app auth/privacy backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind")
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent / "data" / "auth.sqlite3"),
        help="SQLite database path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database = Database(args.db)
    database.initialize()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(database))
    print(f"Auth/privacy backend running at http://{args.host}:{args.port}")
    print(f"SQLite database: {database.path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
