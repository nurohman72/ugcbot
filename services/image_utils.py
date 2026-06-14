import os
from pathlib import Path
from uuid import uuid4
from PIL import Image

import config


def save_photo(photo_bytes: bytes, subdir: str = "products") -> str:
    save_dir = config.PHOTO_DIR / subdir
    save_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}.jpg"
    path = str(save_dir / filename)

    with open(path, "wb") as f:
        f.write(photo_bytes)

    img = Image.open(path)
    img = img.convert("RGB")
    img.save(path, "JPEG", quality=85)

    return path
