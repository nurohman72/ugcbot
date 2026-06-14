# UGC Bot — Foto Produk Affiliate dengan AI

Telegram bot untuk affiliate marketing. Upload foto produk, AI menganalisa, lalu generate foto model yang memegang/menggunakan produk — semuanya otomatis.

## Fitur

- **Analisa Produk Otomatis** — (opsional) AI mendeskripsikan produk dari foto. Jika gagal, user bisa isi manual
- **Generate Model AI** — FLUX.1-schnell membuat foto model sesuai gender & usia
- **Upload Model Sendiri** — atau pakai foto model Anda sendiri
- **State Machine** — percakapan 10 langkah yang terstruktur
- **Penyimpanan Riwayat** — semua sesi tersimpan di SQLite

## Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Runtime | Python 3.12+ |
| Framework Bot | python-telegram-bot 20.8 (async) |
| Vision AI | Gemini 1.5 Flash via API (gratis) atau microsoft/Florence-2-large (jika GEMINI_API_KEY tidak diisi) |
| Image Gen | black-forest-labs/FLUX.1-schnell |
| Database | SQLite3 |
| Image Proc | Pillow |
| Deploy | Hugging Face Inference API (router.huggingface.co) |

## Persiapan

1. **Clone repo**
   ```bash
   git clone https://github.com/nurohman72/ugcbot.git
   cd ugcbot
   ```

2. **Buat virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfigurasi**
   ```bash
   cp .env.example .env
   ```
   Isi `.env`:
   - `BOT_TOKEN` — dari [@BotFather](https://t.me/BotFather)
   - `HF_TOKEN` — dari [Hugging Face Settings](https://huggingface.co/settings/tokens)
   - `GEMINI_API_KEY` — (opsional) dari [Google AI Studio](https://aistudio.google.com/apikey), untuk analisa foto produk otomatis
   - `HF_API_URL` — default `https://router.huggingface.co/hf-inference/models`

5. **Jalankan**
   ```bash
   python main.py
   ```

## Cara Pakai

1. Kirim `/start` ke bot
2. Upload **foto produk** (1 atau lebih)
3. Tambahkan **deskripsi** dari Anda
4. Pilih **model AI** atau **upload model sendiri**
5. Jika model AI: pilih **gender** & **usia**
6. Setuju dengan hasil preview → bot generate **foto utama**

## Struktur Proyek

```
ugcbot/
├── main.py                 # Entry point
├── config.py               # Konfigurasi dari .env
├── conversation.py         # Semua logic dialog (10 states)
├── db.py                   # Wrapper SQLite
├── states.py               # Konstanta state
├── services/
│   ├── huggingface_vision.py  # Analisa gambar via HF API
│   ├── huggingface_gen.py     # Generate gambar via HF API
│   └── image_utils.py         # Simpan & konversi foto
├── photos/                 # Penyimpanan foto (auto-generated)
├── ugcbot.db               # Database SQLite
└── .env                    # Token & konfigurasi
```

## Lisensi

MIT
