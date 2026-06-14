#!/usr/bin/env python3
import logging
import sys

from telegram.ext import Application

import config
from conversation import conv_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)


def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "isi_token_bot_telegram_di_sini":
        print("❌ BOT_TOKEN belum diisi! Edit file .env")
        return

    if not config.HF_TOKEN or config.HF_TOKEN == "isi_token_huggingface_di_sini":
        print("❌ HF_TOKEN belum diisi! Edit file .env")
        return

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(conv_handler)

    print("🤖 UGC Bot started! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
