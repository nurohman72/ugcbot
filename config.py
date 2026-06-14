import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

HF_VISION_MODEL = os.getenv("HF_VISION_MODEL", "microsoft/Florence-2-large")
HF_GEN_MODEL = os.getenv("HF_GEN_MODEL", "black-forest-labs/FLUX.1-schnell")
HF_API_URL = "https://api-inference.huggingface.co/models"

DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "ugcbot.db")
PHOTO_DIR = BASE_DIR / os.getenv("PHOTO_DIR", "photos")
