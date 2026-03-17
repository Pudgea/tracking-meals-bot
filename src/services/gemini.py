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
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-1.5-flash")

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
