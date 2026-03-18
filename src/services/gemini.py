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
  "calories": <number>,
  "protein":  <number in grams>,
  "fat":      <number in grams>,
  "carbs":    <number in grams>,
  "fiber":    <number in grams>,
  "description": "<short meal description in Russian>"
}

Base all estimates on visible portion size and the provided description.
"""


@dataclass(frozen=True)
class NutritionData:
    calories: Decimal
    protein: Decimal
    fat: Decimal
    carbs: Decimal
    fiber: Decimal
    description: str


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self._normalize_model_name(model))

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        m = model.strip()
        if not m:
            return "gemini-flash-latest"
        if m.startswith("models/"):
            return m
        return m

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

        return NutritionData(
            calories=Decimal(str(data["calories"])),
            protein=Decimal(str(data["protein"])),
            fat=Decimal(str(data["fat"])),
            carbs=Decimal(str(data["carbs"])),
            fiber=Decimal(str(data["fiber"])),
            description=str(data.get("description", text or "")),
        )

    async def get_workout_advice(
        self,
        profile: dict,
        meals_today: list[dict],
        workout_description: str,
    ) -> str:
        return await asyncio.to_thread(
            self._workout_advice_sync,
            profile,
            meals_today,
            workout_description,
        )

    def _workout_advice_sync(
        self,
        profile: dict,
        meals_today: list[dict],
        workout_description: str,
    ) -> str:
        profile_text = "Не указан" if not (profile.get("height_cm") or profile.get("goal")) else (
            f"Рост: {profile.get('height_cm')} см. Цель: {profile.get('goal') or 'не указана'}"
        )
        meals_text = "Нет записей о приёмах пищи за сегодня."
        if meals_today:
            lines = []
            for m in meals_today:
                t = m.get("logged_at")
                time_str = t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)
                lines.append(
                    f"- {time_str}: {m.get('description', '—')} "
                    f"(ккал: {m.get('calories')}, Б: {m.get('protein')}, Ж: {m.get('fat')}, У: {m.get('carbs')})"
                )
            meals_text = "\n".join(lines)

        prompt = f"""Профиль пользователя: {profile_text}

Приёмы пищи за сегодня:
{meals_text}

Тренировка: {workout_description}

Дай краткий совет на русском: что можно съесть или выпить для восстановления после этой тренировки, с учётом уже съеденного за день и цели пользователя. 2–4 предложения, без лишнего."""

        response = self._model.generate_content(prompt)
        return (response.text or "").strip()

    async def get_day_analysis(
        self,
        profile: dict,
        summary: dict,
        weight_kg: float | None,
        date_str: str,
    ) -> str:
        return await asyncio.to_thread(
            self._day_analysis_sync,
            profile,
            summary,
            weight_kg,
            date_str,
        )

    def _day_analysis_sync(
        self,
        profile: dict,
        summary: dict,
        weight_kg: float | None,
        date_str: str,
    ) -> str:
        profile_text = "Не указан" if not (profile.get("height_cm") or profile.get("goal")) else (
            f"Рост: {profile.get('height_cm')} см. Цель: {profile.get('goal') or 'не указана'}"
        )
        prompt = f"""Профиль: {profile_text}
Дата: {date_str}
Вес на сегодня: {weight_kg if weight_kg is not None else 'не записан'} кг

Сводка питания за день:
- Приёмов пищи: {summary.get('meals', 0)}
- Калории: {summary.get('calories') or 0}
- Белки: {summary.get('protein') or 0} г
- Жиры: {summary.get('fat') or 0} г
- Углеводы: {summary.get('carbs') or 0} г
- Клетчатка: {summary.get('fiber') or 0} г

Дай краткий анализ дня на русском: что хорошо, что можно улучшить (питание, режим, баланс БЖУ), конкретные рекомендации. 3–5 предложений."""

        response = self._model.generate_content(prompt)
        return (response.text or "").strip()
