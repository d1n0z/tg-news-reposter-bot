import hashlib
import json
import os
import pickle
from datetime import datetime, timezone
import re
from typing import Any

import torch
from loguru import logger
from sentence_transformers import SentenceTransformer, util
from torch import Tensor
from transformers import logging as hf_logging

logger = logger.bind(filter_logger=True)

CACHE_FILE = "cache.pkl"
MAX_CACHE_SIZE = 1000
SIMILARITY_THRESHOLD = 0.80
RELEVANCE_THRESHOLD = 0.80

cache = []  # [{ "hash": str, "embedding": tensor (CPU), "date": datetime }]

hf_logging.set_verbosity_error()
hf_logging.disable_progress_bar()

model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)

with open("words.json", "r", encoding="utf-8") as f:
    KEYWORDS: list[str] = json.load(f)

keyword_embeddings = model.encode(
    KEYWORDS, show_progress_bar=False, convert_to_tensor=True
)


def normalize_text_for_hash(text: str) -> str:
    return " ".join(text.split()).lower()


def get_text_hash(text: str) -> str:
    norm = normalize_text_for_hash(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _to_tensor(x: Any, device: torch.device) -> Tensor:
    if torch.is_tensor(x):
        t = x.detach()
    else:
        t = torch.as_tensor(x)
    if t.dtype not in (torch.float32, torch.float):
        t = t.float()
    return t.to(device)


def load_cache():
    global cache
    logger.debug("Loading cache from {}", CACHE_FILE)
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                loaded = pickle.load(f)
            for item in loaded:
                emb = item.get("embedding")
                if not torch.is_tensor(emb):
                    emb = torch.as_tensor(emb)
                item["embedding"] = emb.cpu().detach()
            cache = loaded
            logger.debug("Cache loaded successfully, {} items", len(cache))
        except Exception as e:
            logger.exception("Failed to load cache: {}", e)
            cache = []
    else:
        logger.debug("Cache file does not exist, starting with empty cache")
        cache = []


def save_cache():
    logger.debug("Saving cache with {} items", len(cache))
    rotate_cache()
    serializable = []
    for item in cache:
        emb = item["embedding"]
        if torch.is_tensor(emb):
            emb_np = emb.cpu().detach().numpy()
        else:
            emb_np = emb
        serializable.append(
            {"hash": item["hash"], "embedding": emb_np, "date": item["date"]}
        )
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(serializable, f)
    logger.debug("Cache saved successfully")


def rotate_cache():
    global cache
    if len(cache) > MAX_CACHE_SIZE:
        logger.debug("Rotating cache: {} -> {}", len(cache), MAX_CACHE_SIZE)
        cache = cache[-MAX_CACHE_SIZE:]


def is_duplicate(text_embedding: Tensor) -> bool:
    if not cache:
        return False

    if text_embedding.dim() == 1:
        query = text_embedding.unsqueeze(0)
    else:
        query = text_embedding

    device = query.device
    cache_embeddings = [item["embedding"] for item in cache]
    tensors = [_to_tensor(e, device) for e in cache_embeddings]
    try:
        cache_batch = torch.stack(tensors)
    except Exception as e:
        logger.exception("Failed to stack cache embeddings: {}", e)
        return False

    sim_scores = util.cos_sim(query, cache_batch)[0]
    max_score = float(sim_scores.max().cpu().item())
    logger.debug("Max similarity against cache: {}", max_score)
    return max_score >= SIMILARITY_THRESHOLD


def find_keywords(text: str) -> list[str]:
    found = []
    for kw in KEYWORDS:
        pattern = rf"\b{re.escape(kw.lower())}\b"
        if re.search(pattern, text):
            found.append(kw)
    return found


def process_news(text: str):
    global cache
    logger.debug("Processing news: {} chars", len(text))

    lower_text = text.lower()
    embedding = model.encode(text, show_progress_bar=False, convert_to_tensor=True)

    kw_found = find_keywords(lower_text)
    if not kw_found:
        logger.debug("No keywords found in text({}), checking relevance", text)
        relevance_scores = util.cos_sim(embedding, keyword_embeddings)[0]
        if (
            relevance := float(relevance_scores.max().cpu().item())
        ) < RELEVANCE_THRESHOLD:
            e = f"Text not relevant (text: {text}, score: {relevance:.4f})"
            logger.debug(e)
            return False, e
        logger.debug(
            f"Text not relevant (text: {text}, score: {relevance:.4f})"
        )
    else:
        relevance = None
        logger.debug(
            "Keywords found in text ({}({})), skipping relevance check", text, ",".join(kw_found)
        )

    text_hash = get_text_hash(text)
    if any(item["hash"] == text_hash for item in cache):
        e = "Text hash already in cache"
        logger.debug(e)
        return False, e

    if is_duplicate(embedding):
        e = "Text is duplicate by embedding"
        logger.debug(e)
        return False, e

    logger.debug("Adding text to cache")
    cache.append(
        {
            "hash": text_hash,
            "embedding": embedding.cpu().detach(),
            "date": datetime.now(tz=timezone.utc),
        }
    )

    save_cache()
    logger.debug("News processed successfully")
    return True, ",".join(kw_found) if kw_found else relevance


load_cache()
logger.debug("Initial cache size after load: {}", len(cache))
