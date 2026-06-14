import requests
import logging
import time

import config

logger = logging.getLogger(__name__)


def analyze_image(image_path: str) -> str:
    headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}
    model_id = config.HF_VISION_MODEL

    with open(image_path, "rb") as f:
        data = f.read()

    # Try configured vision model
    try:
        result = _call_model(model_id, headers, data)
        if result:
            return result
    except Exception as e:
        logger.warning(f"Vision model {model_id} failed: {e}")

    raise Exception(
        f"AI vision analysis tidak tersedia untuk model {model_id}. "
        "HF Inference API tidak mendukung image-to-text gratis. "
        "Silakan lanjutkan dengan deskripsi manual."
    )


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
