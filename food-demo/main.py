import os
import json
import base64
from typing import Any

import requests
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Food Analyzer Demo")


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()


def build_prompt() -> str:
    return """
Analiza la imagen y responde SOLO con JSON válido.

Primero determina si la imagen principal muestra comida o bebida consumible.

Si NO es comida o bebida, responde exactamente:
{
  "is_food": false,
  "message": "Eso no es comida"
}

Si SÍ es comida o bebida, responde exactamente:
{
  "is_food": true,
  "food_name": "string",
  "estimated_portion": "string",
  "calories": 0,
  "protein_g": 0,
  "carbs_g": 0,
  "fat_g": 0,
  "fiber_g": 0,
  "sugar_g": 0,
  "confidence": 0
}

Reglas:
- No agregues texto fuera del JSON
- No uses markdown
- Los nutrientes son una estimación de la porción visible
- confidence debe ir de 0 a 100
""".strip()


def extract_json_from_content(content: Any) -> dict:
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        content = "".join(text_parts).strip()

    if not isinstance(content, str):
        raise ValueError("La respuesta del modelo no vino en texto")

    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start:end + 1])
        raise ValueError(f"El modelo no devolvió JSON válido: {content}")


def call_openrouter(image_bytes: bytes, mime_type: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError("Falta OPENROUTER_API_KEY")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://railway.app",
        "X-Title": "Food Analyzer Demo"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": build_prompt()
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=90
    )

    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return extract_json_from_content(content)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/analyze-food")
async def analyze_food(file: UploadFile = File(...)):
    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            return JSONResponse(
                status_code=400,
                content={
                    "is_food": False,
                    "message": "El archivo no es una imagen"
                }
            )

        image_bytes = await file.read()
        result = call_openrouter(image_bytes, file.content_type)

        if not isinstance(result, dict):
            return JSONResponse(
                status_code=500,
                content={
                    "is_food": False,
                    "message": "Respuesta inválida del modelo"
                }
            )

        if result.get("is_food") is False:
            return JSONResponse(
                status_code=200,
                content={
                    "is_food": False,
                    "message": "Eso no es comida"
                }
            )

        normalized = {
            "is_food": True,
            "food_name": result.get("food_name", "Desconocido"),
            "estimated_portion": result.get("estimated_portion", "Porción estimada"),
            "calories": result.get("calories", 0),
            "protein_g": result.get("protein_g", 0),
            "carbs_g": result.get("carbs_g", 0),
            "fat_g": result.get("fat_g", 0),
            "fiber_g": result.get("fiber_g", 0),
            "sugar_g": result.get("sugar_g", 0),
            "confidence": result.get("confidence", 0)
        }

        return JSONResponse(status_code=200, content=normalized)

    except requests.HTTPError as exc:
        try:
            detail = exc.response.text
        except Exception:
            detail = str(exc)

        return JSONResponse(
            status_code=500,
            content={
                "is_food": False,
                "message": f"Error con OpenRouter: {detail}"
            }
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "is_food": False,
                "message": f"Error interno: {str(exc)}"
            }
        )