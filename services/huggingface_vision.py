import base64
import logging
import time

import requests

import config

logger = logging.getLogger(__name__)


def analyze_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Try Gemini API first if key is configured
    if config.GEMINI_API_KEY:
        try:
            result = _analyze_with_gemini(image_bytes)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Gemini analysis failed: {e}")
    else:
        logger.info("GEMINI_API_KEY not set, skipping Gemini")

    # Try HF Inference API (likely to fail for image-to-text)
    try:
        headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}
        result = _call_model(config.HF_VISION_MODEL, headers, image_bytes)
        if result:
            return result
    except Exception as e:
        logger.warning(f"HF vision model failed: {e}")

    raise Exception(
        "Gagal menganalisa gambar. Silakan isi deskripsi manual."
    )


_GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]


def _analyze_with_gemini(image_bytes: bytes) -> str | None:
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    errors = []
    for model in _GEMINI_MODELS:
        try:
            result = _call_gemini(model, encoded)
            if result:
                return result
        except Exception as e:
            msg = str(e)
            errors.append(f"{model}: {msg}")
            if "429" in msg or "quota" in msg.lower():
                logger.warning(f"Gemini {model} quota exceeded, trying next model ...")
            else:
                logger.warning(f"Gemini {model} failed: {msg}")

    raise Exception("; ".join(errors))


def _call_gemini(model: str, encoded: str) -> str | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [
                {"text": "Describe this product photo in detail in English for an e-commerce listing. Include: what the product is, its color, material, shape, visible features, and any text or branding visible. Be specific and concise (max 100 words)."},
                {"inline_data": {"mime_type": "image/jpeg", "data": encoded}},
            ]
        }]
    }

    resp = requests.post(url, json=payload, timeout=60)

    # Retry 429 once per model
    if resp.status_code == 429:
        logger.warning(f"Gemini {model} 429, retrying in 10s ...")
        time.sleep(10)
        resp = requests.post(url, json=payload, timeout=60)

    if resp.status_code == 429:
        raise Exception(f"429 quota exceeded")

    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise Exception("Gemini returned no candidates")

    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    if not text:
        raise Exception("Gemini returned empty text")

    return text[:500]


def _call_model(model_id: str, headers: dict, data: bytes) -> str | None:
    url = f"{config.HF_API_URL}/{model_id}"
    resp = requests.post(url, headers=headers, data=data, timeout=120)

    if resp.status_code == 200:
        return _parse_response(resp)

    if resp.status_code == 503:
        err = resp.json()
        wait = err.get("estimated_time", 30)
        logger.info(f"Model {model_id} loading, waiting {wait}s ...")
        time.sleep(wait + 5)
        resp = requests.post(url, headers=headers, data=data, timeout=120)
        if resp.status_code == 200:
            return _parse_response(resp)
        raise Exception(f"Model still unavailable after retry: HTTP {resp.status_code}")

    raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")


def _parse_response(resp: requests.Response) -> str:
    result = resp.json()
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], dict):
            return result[0].get("generated_text", str(result[0]))[:500]
        return str(result[0])[:500]
    if isinstance(result, dict):
        return result.get("generated_text", str(result))[:500]
    return str(result)[:500]
