import argparse

from loguru import logger


class ArgsNamespace(argparse.Namespace):
    debug: bool = False


parser = argparse.ArgumentParser()

parser.add_argument(
    "-d",
    "--debug",
    help="Run in debug mode.",
    default=False,
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args(namespace=ArgsNamespace())

if args.debug:
    logger.warning("Running in debug mode.")
