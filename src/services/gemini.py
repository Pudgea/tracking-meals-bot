import asyncio
import io
import json
from dataclasses import dataclass
from decimal import Decimal

import google.generativeai as genai
from PIL import Image

_ANALYSIS_PROMPT = """
Analyze the meal in the photo and/or description below.
Return ONLY a valid JSON object — no markdown, no extra text:

{
  "calories": <total kcal>,
  "protein":  <total grams>,
  "fat":      <total grams>,
  "carbs":    <total grams>,
  "fiber":    <total grams>,
  "description": "<meal name in Russian>",
  "breakdown": [
    {
      "name": "<ingredient + approximate weight, e.g. Куриная грудка 200г>",
      "calories": <kcal>,
      "protein": <grams>,
      "fat": <grams>,
      "carbs": <grams>,
      "fiber": <grams>
    }
  ]
}

List each distinct ingredient as a separate item in breakdown with its approximate weight.
Base all estimates on visible portion size and the provided description.
"""


@dataclass(frozen=True)
class NutritionItem:
    name: str
    calories: Decimal
    protein: Decimal
    fat: Decimal
    carbs: Decimal
    fiber: Decimal


@dataclass(frozen=True)
class NutritionData:
    calories: Decimal
    protein: Decimal
    fat: Decimal
    carbs: Decimal
    fiber: Decimal
    description: str
    breakdown: tuple  # tuple[NutritionItem, ...]


def _parse_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _format_profile(profile: dict) -> str:
    if not profile or not (profile.get("height_cm") or profile.get("goal")):
        return "Не указан"
    parts = []
    if profile.get("height_cm"):
        parts.append(f"Рост: {profile['height_cm']} см")
    if profile.get("goal"):
        parts.append(f"Цель: {profile['goal']}")
    return ", ".join(parts)


def _format_meals_context(meals: list[dict]) -> str:
    if not meals:
        return "Нет записей о приёмах пищи."
    lines = []
    for m in meals:
        t = m.get("logged_at")
        time_str = t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)
        lines.append(
            f"- {time_str}: {m.get('description', '—')} "
            f"(ккал: {m.get('calories')}, Б: {m.get('protein')}г, "
            f"Ж: {m.get('fat')}г, У: {m.get('carbs')}г, Кл: {m.get('fiber')}г)"
        )
    return "\n".join(lines)


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model.strip() or "gemini-flash-latest")

    async def analyze_meal(
        self,
        image_bytes: bytes | None,
        text: str | None,
    ) -> NutritionData:
        return await asyncio.to_thread(self._analyze_sync, image_bytes, text)

    def _analyze_sync(
        self,
        image_bytes: bytes | None,
        text: str | None,
    ) -> NutritionData:
        parts: list = []

        if image_bytes:
            parts.append(Image.open(io.BytesIO(image_bytes)))

        prompt = _ANALYSIS_PROMPT
        if text:
            prompt = f"Description: {text}\n\n{_ANALYSIS_PROMPT}"
        parts.append(prompt)

        response = self._model.generate_content(parts)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)

        breakdown = tuple(
            NutritionItem(
                name=str(item.get("name", "")),
                calories=_parse_decimal(item.get("calories", 0)),
                protein=_parse_decimal(item.get("protein", 0)),
                fat=_parse_decimal(item.get("fat", 0)),
                carbs=_parse_decimal(item.get("carbs", 0)),
                fiber=_parse_decimal(item.get("fiber", 0)),
            )
            for item in (data.get("breakdown") or [])
            if isinstance(item, dict)
        )

        return NutritionData(
            calories=_parse_decimal(data["calories"]),
            protein=_parse_decimal(data["protein"]),
            fat=_parse_decimal(data["fat"]),
            carbs=_parse_decimal(data["carbs"]),
            fiber=_parse_decimal(data["fiber"]),
            description=str(data.get("description", text or "")),
            breakdown=breakdown,
        )

    async def get_workout_advice(
        self,
        profile: dict,
        meals_today: list[dict],
        workout_description: str,
    ) -> str:
        return await asyncio.to_thread(
            self._workout_advice_sync, profile, meals_today, workout_description
        )

    def _workout_advice_sync(
        self,
        profile: dict,
        meals_today: list[dict],
        workout_description: str,
    ) -> str:
        prompt = f"""Профиль: {_format_profile(profile)}

Съедено за сегодня:
{_format_meals_context(meals_today)}

Тренировка: {workout_description}

Дай совет на русском: что съесть или выпить для восстановления с учётом уже съеденного и цели.
Для каждого рекомендуемого продукта укажи граммовку и КБЖУ. 3–5 предложений."""

        return (self._model.generate_content(prompt).text or "").strip()

    async def get_day_analysis(
        self,
        profile: dict,
        summary: dict,
        meals_today: list[dict],
        workouts_today: list[str],
        weight_kg: float | None,
        date_str: str,
    ) -> str:
        return await asyncio.to_thread(
            self._day_analysis_sync,
            profile, summary, meals_today, workouts_today, weight_kg, date_str,
        )

    def _day_analysis_sync(
        self,
        profile: dict,
        summary: dict,
        meals_today: list[dict],
        workouts_today: list[str],
        weight_kg: float | None,
        date_str: str,
    ) -> str:
        workouts_text = (
            "\n".join(f"- {w}" for w in workouts_today)
            if workouts_today else "Нет тренировок."
        )

        prompt = f"""Профиль: {_format_profile(profile)}
Дата: {date_str}
Вес: {weight_kg if weight_kg is not None else 'не записан'} кг

Тренировки за день:
{workouts_text}

Все приёмы пищи:
{_format_meals_context(meals_today)}

Итого за день: {summary.get('meals', 0)} приёмов, {summary.get('calories') or 0} ккал,
Б: {summary.get('protein') or 0}г, Ж: {summary.get('fat') or 0}г,
У: {summary.get('carbs') or 0}г, Кл: {summary.get('fiber') or 0}г

Дай развёрнутый анализ дня на русском: учти тренировки, баланс БЖУ относительно цели,
качество питания, режим приёмов пищи. Конкретно — что хорошо и что улучшить. 4–6 предложений."""

        return (self._model.generate_content(prompt).text or "").strip()

    async def ask_question(
        self,
        profile: dict,
        meals_today: list[dict],
        weight_kg: float | None,
        workouts_today: list[str],
        question: str,
    ) -> str:
        return await asyncio.to_thread(
            self._ask_question_sync,
            profile, meals_today, weight_kg, workouts_today, question,
        )

    def _ask_question_sync(
        self,
        profile: dict,
        meals_today: list[dict],
        weight_kg: float | None,
        workouts_today: list[str],
        question: str,
    ) -> str:
        workouts_text = (
            "\n".join(f"- {w}" for w in workouts_today)
            if workouts_today else "Нет тренировок."
        )

        prompt = f"""Контекст пользователя:
Профиль: {_format_profile(profile)}
Вес: {weight_kg if weight_kg is not None else 'не записан'} кг

Тренировки сегодня:
{workouts_text}

Съедено сегодня:
{_format_meals_context(meals_today)}

Вопрос: {question}

Ответь на русском кратко и по делу. Если речь о конкретных продуктах — обязательно укажи:
- примерную граммовку (например: банан ~120г, куриная грудка ~200г)
- КБЖУ для каждого продукта отдельно
- итоговые КБЖУ если продуктов несколько
Учитывай, что уже было съедено сегодня, и цель пользователя."""

        return (self._model.generate_content(prompt).text or "").strip()
