import asyncio
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    from newsreposter.app import run

    logger.opt(colors=True).info("<M>Starting unified app...</M>")
    logger.debug("Python version: {}", sys.version)
    logger.debug("Working directory: {}", Path.cwd())

    asyncio.run(run())
    logger.debug("Application finished")
    return


if __name__ == "__main__":
    main()
