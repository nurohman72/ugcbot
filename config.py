import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

HF_VISION_MODEL = os.getenv("HF_VISION_MODEL", "microsoft/Florence-2-large")
HF_GEN_MODEL = os.getenv("HF_GEN_MODEL", "black-forest-labs/FLUX.1-schnell")
HF_API_URL = os.getenv("HF_API_URL", "https://router.huggingface.co/hf-inference/models")

DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "ugcbot.db")
PHOTO_DIR = BASE_DIR / os.getenv("PHOTO_DIR", "photos")
