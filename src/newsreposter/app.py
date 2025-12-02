import asyncio

from newsreposter.core import logging
from newsreposter.core.argparse import args

logging.setup_logger(level="DEBUG" if args.debug else "INFO")

async def run():
    from functools import partial

    from loguru import logger

    from newsreposter.core.config import settings
    from newsreposter.core.post import aiogram_post_item
    from newsreposter.services.bot import BotService, BotServiceConfig
    from newsreposter.services.news_checker import NewsChecker
    from newsreposter.services.news_queue import FileQueue, QueuePoster

    logger = logger.opt(colors=True)

    logger.debug("Starting application")
    queue = FileQueue()
    logger.debug("FileQueue created")

    newschecker = NewsChecker(q=queue)
    logger.debug("NewsChecker initialized")

    botservice = BotService(service_config=BotServiceConfig(token=settings.TOKEN))
    logger.debug("BotService created")
    await botservice.initialize()
    logger.debug("BotService initialized")

    poster = QueuePoster(
        queue, partial(aiogram_post_item, bot=botservice.bot, chat_id=settings.CHAT_ID)
    )
    logger.debug("QueuePoster created")

    await newschecker.start()
    logger.info("<C>NewsChecker started.</C>")
    await poster.start()
    logger.info("<C>QueuePoster started.</C>")

    logger.info("<G>Started unified app!</G>")
    try:
        await asyncio.Event().wait()
    except asyncio.exceptions.CancelledError:
        pass
    logger.info("<R>Shutting down...</R>")

    await botservice.bot.session.close()
    await poster.stop()
    await newschecker.close()

    logger.warning("<Y><black>Script stopped.</black></Y>")
