import requests
import logging

import config

logger = logging.getLogger(__name__)


def analyze_image(image_path: str) -> str:
    headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}

    with open(image_path, "rb") as f:
        data = f.read()

    url = f"{config.HF_API_URL}/{config.HF_VISION_MODEL}"

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=120)

        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get("generated_text", str(result[0]))
                return text[:500]
            return str(result)[:500]

        if resp.status_code == 503:
            err = resp.json()
            wait = err.get("estimated_time", 30)
            logger.info(f"Model loading, waiting {wait}s ...")
            import time
            time.sleep(wait + 5)
            resp = requests.post(url, headers=headers, data=data, timeout=120)
            if resp.status_code == 200:
                result = resp.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", str(result[0]))[:500]
                return str(result)[:500]

        raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")

    except requests.Timeout:
        logger.warning("Vision API timeout, falling back to BLIP ...")
        return _fallback_analyze(image_path)


def _fallback_analyze(image_path: str) -> str:
    headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}
    url = f"{config.HF_API_URL}/Salesforce/blip2-flan-t5-xl"

    with open(image_path, "rb") as f:
        data = f.read()

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", str(result[0]))[:500]
            return str(result)[:500]
        return f"Gagal menganalisa (fallback): {resp.text[:100]}"
    except Exception as e:
        return f"Gagal menganalisa gambar: {str(e)[:100]}"
