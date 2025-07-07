"""Entry point to run the MYCA orchestrator service."""

import uvicorn
from orchestrator import app


def main() -> None:
    """Start the orchestrator API using Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
