# UGC Bot — Panduan untuk AI Agent

## Deskripsi

Telegram bot untuk affiliate marketing. Pengguna upload foto produk, AI menganalisa (Florence-2-large / BLIP2 fallback), lalu generate foto model memegang/menggunakan produk (FLUX.1-schnell).

## Tech Stack

- Python 3.12+, `python-telegram-bot` 20.8 (async), SQLite3, Pillow, requests
- Hugging Face Inference API (serverless) untuk vision & image generation

## Struktur Proyek

```
ugcbot/
├── main.py              # Entry point, build Application + run_polling()
├── config.py            # Load .env, export konstanta path & token
├── conversation.py      # ConversationHandler (10 states), semua logic dialog
├── db.py                # Database wrapper (sessions & generation_log)
├── states.py            # Tuple of 10 state constants (range(10))
├── services/
│   ├── huggingface_vision.py  # analyze_image() -> deskripsi teks
│   ├── huggingface_gen.py     # generate_image(prompt) -> bytes
│   └── image_utils.py         # save_photo(bytes, subdir) -> path
├── photos/              # {products, generated, models, final}/
├── ugcbot.db            # SQLite file (auto-create)
├── .env                 # BOT_TOKEN, HF_TOKEN, model config
└── requirements.txt
```

## Conversation Flow (10 States)

| State | Handler | Input |
|-------|---------|-------|
| `WAITING_PRODUCT_PHOTO` (0) | `handle_product_photo` | Foto produk pertama |
| `WAITING_DESCRIPTION` (1) | `handle_description` | Teks deskripsi user |
| `ASKING_ADD_PHOTO` (2) | `handle_add_photo_choice` | Callback yes/no |
| `WAITING_ADDITIONAL_PHOTO` (3) | `handle_additional_photo` | Foto tambahan |
| `WAITING_PHOTO_DESC` (4) | `handle_photo_desc` | Deskripsi foto tambahan |
| `CHOOSING_MODEL_TYPE` (5) | `handle_model_type_choice` | Callback ai/upload |
| `WAITING_GENDER` (6) | `handle_gender_choice` | Callback gender |
| `WAITING_AGE_GROUP` (7) | `handle_age_group_choice` | Callback age |
| `WAITING_AI_CONFIRM` (8) | `handle_ai_confirm` | Callback ok/retry/cancel |
| `WAITING_MODEL_UPLOAD` (9) | `handle_model_upload` | Foto model upload |

## Aturan Penting

### Bahasa
- **Semua teks ke user**: Bahasa Indonesia
- **Semua prompt AI**: Bahasa Inggris (sudah di `_build_product_prompt` dan `_build_final_prompt`)
- **Semua kode, komentar, logging, variable**: Bahasa Inggris
- **AGENTS.md**: Boleh bilingual

### Konvensi Kode
- **Async**: Semua handler function harus `async def`. Panggil service sync dengan `await` tidak perlu (non-async service layer).
- **Session state**: Disimpan di SQLite via `db.get_session(chat_id)` / `db.update_session(chat_id, **kwargs)`. Field session: `product_photos`, `ai_analyses`, `user_descriptions` adalah JSON string — gunakan `eval()` untuk parse (existing pattern).
- **Error handling**: Setiap handler harus try/except dan mengirim pesan error ke user + log.
- **Photo paths**: Disimpan sebagai string path absolut. Save via `save_photo(bytes, subdir)` dari `image_utils.py`.
- **Inline keyboard**: Gunakan `InlineKeyboardButton` + `InlineKeyboardMarkup`. pattern callback untuk `CallbackQueryHandler` harus regex.

### Konfigurasi (.env)
- `BOT_TOKEN` — Telegram bot token
- `HF_TOKEN` — Hugging Face API token
- `HF_VISION_MODEL` — default `microsoft/Florence-2-large`
- `HF_GEN_MODEL` — default `black-forest-labs/FLUX.1-schnell`
- `DATABASE_PATH` — default `ugcbot.db`
- `PHOTO_DIR` — default `photos`

### Service Layer
- `huggingface_vision.py`: `analyze_image(path) -> str` — POST ke HF Inference API, retry 503 otomatis, fallback BLIP2 on timeout
- `huggingface_gen.py`: `generate_image(prompt, max_retries=3) -> bytes` — POST dengan payload `{"inputs": prompt}`, retry 503 & timeout
- `image_utils.py`: `save_photo(bytes, subdir) -> str` — simpan sebagai JPEG kualitas 85, return path absolut

### Database
- `sessions` table: `chat_id` (PK), `step`, `product_photos` (JSON array string), `ai_analyses` (JSON array string), `user_descriptions` (JSON array string), `model_type`, `ai_gender`, `ai_age_group`, `model_photo_path`, `created_at`, `updated_at`
- `generation_log` table: `id` (PK autoincrement), `chat_id`, `prompt`, `photo_path`, `status`, `created_at`

## Cara Menjalankan

```bash
python main.py
```

Hanya itu — tidak ada build/test/lint script formal. Bot jalan dengan polling.
