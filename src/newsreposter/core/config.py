from pathlib import Path
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict

logger.debug("Initializing config module")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent / ".env",
        env_nested_delimiter="__",
        extra="allow",
    )

    TOKEN: str
    CHAT_ID: int


logger.debug("Loading settings from environment")
settings = Settings()  # type: ignore
logger.debug("Settings loaded successfully")
