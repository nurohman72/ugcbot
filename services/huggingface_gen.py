import time
import logging
import requests

import config

logger = logging.getLogger(__name__)


def generate_image(prompt: str, max_retries: int = 3) -> bytes:
    headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}
    url = f"{config.HF_API_URL}/{config.HF_GEN_MODEL}"
    payload = {"inputs": prompt}

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=180)

            if resp.status_code == 200:
                return resp.content

            if resp.status_code == 503:
                err = resp.json()
                wait = err.get("estimated_time", 30)
                logger.info(
                    f"Gen model loading, attempt {attempt+1}/{max_retries}, "
                    f"waiting {wait}s ..."
                )
                time.sleep(wait + 10)
                continue

            raise Exception(
                f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        except requests.Timeout:
            logger.warning(
                f"Gen timeout attempt {attempt+1}/{max_retries}, retrying ..."
            )
            time.sleep(10)
            continue

    raise Exception(
        "Gagal generate gambar setelah beberapa percobaan. "
        "Coba lagi nanti atau ganti model di .env"
    )
