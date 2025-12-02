from dataclasses import dataclass
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode, UpdateType
from loguru import logger

from newsreposter.core import config


@dataclass
class BotServiceConfig:
    token: str


class BotService:
    def __init__(self, service_config: BotServiceConfig, session: Optional[AiohttpSession] = None) -> None:
        self._config: BotServiceConfig = service_config
        self._bot: Optional[Bot] = None
        self._dp: Optional[Dispatcher] = None
        self._session = session

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            raise RuntimeError("Bot is not initialized. Call initialize() first.")
        return self._bot

    @property
    def dp(self) -> Dispatcher:
        if self._dp is None:
            raise RuntimeError(
                "Dispatcher is not initialized. Call initialize() first."
            )
        return self._dp

    async def initialize(self) -> None:
        logger.debug("Initializing BotService")
        if (
            hasattr(config.settings, "LOCAL_SESSION_URL")
            and config.settings.LOCAL_SESSION_URL  # type: ignore
        ):
            logger.debug("Using local session URL: {}", config.settings.LOCAL_SESSION_URL)  # type: ignore
            self._session = AiohttpSession(
                api=TelegramAPIServer.from_base(
                    config.settings.LOCAL_SESSION_URL,  # type: ignore
                    is_local=True,
                )
            )
        self._dp = Dispatcher()
        self._bot = Bot(
            token=self._config.token,
            session=self._session,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML, link_preview_is_disabled=True
            ),
        )
        logger.debug("BotService initialized successfully")

    async def run(self) -> None:
        logger.debug("Starting BotService")
        if self._bot is None or self._dp is None:
            await self.initialize()
        if self._bot is None or self._dp is None:
            logger.error("The bot or dispatcher failed to initialize")
            raise RuntimeError("The bot or dispatcher failed to initialize.")

        logger.info("Starting polling")
        await self._dp.start_polling(self._bot, allowed_updates=[UpdateType.MESSAGE, UpdateType.CALLBACK_QUERY])
        logger.info("Polling stopped")
