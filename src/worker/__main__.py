"""CLI entry point for running the worker."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.worker.poll import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
