import asyncio
from typing import Any, Dict, List

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InputMediaPhoto, InputMediaVideo
from loguru import logger

from newsreposter.core import post_parsers

FULL_POST_MAX_LEN = 1024


async def aiogram_post_item(
    item: Dict[str, Any],
    bot: Bot,
    chat_id: int,
    *,
    full_post_max_len: int = FULL_POST_MAX_LEN,
) -> None:
    logger.debug("Processing item for posting: {}", item)
    title = (item.get("title") or "").strip()
    link = (item.get("link") or item.get("url") or "").strip()
    pre_description = (item.get("description") or "").strip()

    if not title:
        logger.error("Item missing title")
        raise ValueError("Item missing title")
    if not link:
        logger.error("Item missing link/url")
        raise ValueError("Item missing link/url")

    post_data = await asyncio.to_thread(post_parsers.parse, link)

    photos: List[str] = []
    videos: List[str] = []
    description: str = ""
    if isinstance(post_data, dict):
        photos = list(post_data.get("photo") or [])
        videos = list(post_data.get("video") or [])
        description = "\n".join(post_data.get("description") or [""])
    else:
        logger.debug("Unknown media format or empty: {}", type(post_data))

    if (
        not description
        or len(description) < 30
        or len(description) / 2 == description.count("\n")  # anti-moron protection jic
    ):
        description = pre_description or ""

    full_text = (
        f"<b>{title}</b>\n\n{description}\n\n{link}"
        if description
        else f"<b>{title}</b>\n\n{link}"
    )

    if len(full_text) >= full_post_max_len:
        short_text = f"<b>{title}</b>\n\n{link}"
        to_send = short_text
        disable_preview = True
    else:
        to_send = full_text
        disable_preview = False

    try:
        if videos:
            input_media = []
            for i, v in enumerate(videos[:10]):
                if i == 0:
                    input_media.append(
                        InputMediaVideo(media=v, caption=to_send, parse_mode="HTML")
                    )
                else:
                    input_media.append(InputMediaVideo(media=v))
            await bot.send_media_group(chat_id, input_media)
            logger.info(
                "Posted to TG (media_group, videos: {}): {}", len(videos), title
            )
            return

        if photos:
            if len(photos) == 1:
                await bot.send_photo(
                    chat_id, photos[0], caption=to_send, parse_mode="HTML"
                )
                logger.info("Posted to TG (photo): {}", title)
            else:
                input_media = []
                for i, p in enumerate(photos[:10]):
                    if i == 0:
                        input_media.append(
                            InputMediaPhoto(media=p, caption=to_send, parse_mode="HTML")
                        )
                    else:
                        input_media.append(InputMediaPhoto(media=p))
                await bot.send_media_group(chat_id, input_media)
                logger.info(
                    "Posted to TG (media_group, photos: {}): {}", len(photos), title
                )
            return

        await bot.send_message(
            chat_id,
            to_send,
            parse_mode="HTML",
            disable_web_page_preview=disable_preview,
        )
        logger.info("Posted to TG (text only): {}", title)

    except TelegramAPIError:
        logger.exception("Telegram API error while posting item: {}", title)
        await bot.send_message(
            chat_id, to_send, parse_mode="HTML", disable_web_page_preview=True
        )
        logger.info("Posted to TG (text fallback after TelegramAPIError): {}", title)
