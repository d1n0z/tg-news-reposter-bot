"""
Тест для filter-процесса (process_news).
Поместите этот файл в ту же папку, где лежит ваш скрипт (по умолчанию предполагается, что он называется `news_filter.py`).
Если ваш файл называется иначе — поправьте импорт ниже (`import news_filter as nf`).

Что делает тест:
- генерирует 200 заголовков "по теме" (используя KEYWORDS из вашего скрипта) и 200 заголовков "не по теме";
- вызывает nf.process_news(title) для каждого заголовка;
- собирает метрики: TP/FP/TN/FN, accuracy, precision, recall;
- сохраняет примеры ошибочной классификации в CSV `misclassified.csv`.

Тест временно отключает запись в реальный CACHE_FILE и проверку дубликатов, чтобы результаты не зависели
от локального кэша и не перезаписывали его. Это означает, что тест фокусируется на логике поиска ключевых слов
и проверке релевантности, а не на дедупликации.
"""

from __future__ import annotations

import csv
import datetime
import os
import random
import tempfile
from typing import List, Tuple

import src.newsreposter.core.process_news as nf
from src.newsreposter.core.logging import setup_logger

setup_logger(level="INFO")

RANDOM_SEED = 42
MISCLASSIFIED_CSV = "misclassified.csv"

random.seed(RANDOM_SEED)

nf.CACHE_FILE = os.path.join(tempfile.gettempdir(), "test_cache.pkl")
nf.cache = []
if hasattr(nf, "save_cache"):
    nf.save_cache = lambda: None
if hasattr(nf, "is_duplicate"):
    nf.is_duplicate = lambda emb: False

KEYWORDS: List[str] = getattr(nf, "KEYWORDS", [])

if not KEYWORDS:
    raise RuntimeError(
        "В модуле не найден KEYWORDS — положите words.json и убедитесь, что KEYWORDS импортируется"
    )

IN_TOPIC_TEMPLATES = [
    "{kw} обнаружены в регионе — органы проводят проверку",
    "Оперативники задержали подозреваемых в связи с {kw}",
    "Минобороны: информация о {kw} проверяется",
    "Появились данные о возможной {kw} — следствие ведется",
    "Эксперты комментируют случаи, связанные с {kw}",
    "Власти предупредили о риске {kw} в регионе",
    "Расследование фактов {kw} продолжается — подробности",
    "Службы сообщили о предотвращении {kw}",
    "Усилены меры после сообщений о {kw}",
    "Полиция проверяет сообщение о {kw} в районе",
    "Жители сообщили о подозрительных действиях, связанных с {kw}",
    "Сведения о {kw} поступили от нескольких источников",
    "Источник: возможная {kw} вблизи населённого пункта",
    "Власти отреагировали на угрозу {kw}",
    "Следственные действия связаны с предполагаемой {kw}",
    "Официальный комментарий по делу о {kw} ожидается",
    "Региональные службы подтвердили информацию о {kw}",
    "Проверка фактов: было ли {kw} на самом деле?",
    "Экстренное заявление по поводу {kw} выпущено сегодня",
    "Частичная эвакуация после сообщений о {kw}",
    "Местные СМИ публикуют хронику инцидента с {kw}",
    "Спецоперация начата по причине предполагаемой {kw}",
    "Появилось видео, связанное с {kw} — эксперты анализируют",
    "Граждан призывают сообщать любую информацию о {kw}",
    "Повышенная бдительность из-за угрозы {kw}",
]

OUT_TOPIC_TEMPLATES = [
    "В Херсонской области полицейские провели мероприятия по выявлению нарушений миграционного законодательства РФ"
    "В Самарской области полицейские продолжают проводить познавательные встречи с жителями областного центра, направленные на повышение правовой грамотности",
    'ВСУ за сутки потеряли более 205 боевиков в зоне действий "Севера"'
    "Футбольная команда проиграла матч в серии пенальти",
    "Новый рецепт борща: как приготовить дома",
    "Кинообзор: что смотреть в выходные",
    "Технологический обзор: лучшие смартфоны года",
    "Погодные сводки на неделю: снег и ветер ожидаются",
    "Интервью с шеф-поваром о сезонной кухне",
    "Туристический гид: куда поехать на длинные выходные",
    "Рецензия на книгу: главные мысли и идеи",
    "Как выращивать комнатные растения: советы для начинающих",
    "Обзор акций: рынок закрылся с умеренным ростом",
    "Рецепт: быстрые завтраки для занятых людей",
    "Культурная афиша: выставки и спектакли на этой неделе",
    "Автоновости: тест-драйв нового хэтчбека",
    "Музыкальная премьера: альбом получил противоречивые отзывы",
    "Здоровье: простые упражнения для офиса",
    "DIY: как обновить старую мебель своими руками",
    "Финансы: советы по ведению личного бюджета",
    "Руководство по выбору наушников: что важно учитывать",
    "Кулинарные лайфхаки: хранение остатков еды",
    "Местные события: ярмарка ремёсел в выходные",
    "Гид по сериалам: что посмотреть вечером",
    "Обзор кафе: новое место с интересным меню",
    "Советы для автомобилистов в зимний период",
    "История: ретроспектива известного режиссёра",
]

in_topic: List[str] = []
for template in IN_TOPIC_TEMPLATES:
    kw = random.choice(KEYWORDS)
    title = template.format(kw=kw)
    if random.random() < 0.3:
        title = f"{datetime.datetime.now(datetime.UTC)} — {title}"
    in_topic.append(title)

out_topic: List[str] = []
for template in OUT_TOPIC_TEMPLATES:
    template = random.choice(OUT_TOPIC_TEMPLATES)
    if random.random() < 0.4:
        title = f"{template} — Москва"
    else:
        title = template
    out_topic.append(title)

tests: List[Tuple[str, bool]] = []
tests += [(t, True) for t in in_topic]
tests += [(t, False) for t in out_topic]

random.shuffle(tests)

results = []  # tuples (title, expected, predicted, extra)

print(
    f"Запуск теста: {len(tests)} заголовков ({len(IN_TOPIC_TEMPLATES)} in-topic, {len(OUT_TOPIC_TEMPLATES)} out-topic)\n"
)

for title, expected in tests:
    try:
        res = nf.process_news(title)
        predicted = res[0]
        extra = res[1]
    except Exception as e:
        predicted = False
        extra = f"EXCEPTION: {e!r}"

    results.append((title, expected, predicted, extra))

tp = sum(1 for _, exp, pred, _ in results if exp and pred)
fn = sum(1 for _, exp, pred, _ in results if exp and not pred)
tn = sum(1 for _, exp, pred, _ in results if (not exp) and (not pred))
fp = sum(1 for _, exp, pred, _ in results if (not exp) and pred)
errors = [r for r in results if r[1] != r[2]]

total = len(results)
accuracy = (tp + tn) / total if total else 0.0
precision = tp / (tp + fp) if (tp + fp) else 0.0
recall = tp / (tp + fn) if (tp + fn) else 0.0

print("Результаты:")
print(f"  TP: {tp}")
print(f"  FN: {fn}")
print(f"  TN: {tn}")
print(f"  FP: {fp}")
print(f"  Ошибки/исключения: {len(errors)}")
print(f"  Accuracy: {accuracy:.3f}")
print(f"  Precision: {precision:.3f}")
print(f"  Recall: {recall:.3f}\n")

misclassified = [r for r in results if r[1] != r[2]]
if misclassified:
    with open(MISCLASSIFIED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "expected", "predicted", "extra"])
        for title, expected, predicted, extra in misclassified:
            writer.writerow([title, expected, predicted, extra])
    print(f"Сохранено {len(misclassified)} ошибочных примеров в {MISCLASSIFIED_CSV}")
else:
    print("Ошибочных примеров не найдено")

if misclassified:
    print("\nПервые 10 ошибочных примеров:")
    for title, expected, predicted, extra in misclassified[:10]:
        print(f"- Expected={expected} Predicted={predicted} Extra={extra} | {title}")

print("\nТест завершён.")
