import logging
import random
import warnings

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning, message=".*per_message=False.*")
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ConversationHandler,
)

import config
from db import Database
from services.huggingface_vision import analyze_image
from services.huggingface_gen import generate_image
from services.image_utils import save_photo
from states import *

logger = logging.getLogger(__name__)
db = Database(config.DATABASE_PATH)


# ── Helpers ──────────────────────────────────────────────────────────────

def _build_product_prompt(session: dict, retry_count: int = 0) -> str:
    analyses = eval(session.get("ai_analyses", "[]"))
    descriptions = eval(session.get("user_descriptions", "[]"))
    product_desc = ". ".join(filter(None, analyses + descriptions))

    gender = session.get("ai_gender", "female")
    if gender and gender.lower() in ("laki-laki", "male"):
        gender_en = "male"
    else:
        gender_en = "female"

    age = session.get("ai_age_group", "adult")
    age_map = {"anak-anak": "child", "remaja": "teenager", "dewasa": "adult"}
    age_en = age_map.get(age.lower(), "adult")

    variation = ""
    if retry_count > 0:
        variants = [
            "different pose, slightly different angle",
            "natural candid pose",
            "smiling confidently, looking at camera",
            "looking slightly away, natural lighting",
        ]
        variation = random.choice(variants)

    return (
        f"A professional product photo of a {age_en} {gender_en} model "
        f"wearing/using: {product_desc}. "
        f"The product is clearly visible and highlighted. "
        f"Studio lighting, plain white background, full body shot, "
        f"high quality, photorealistic, 4K, commercial product photography. "
        f"{variation}"
    ).strip()


def _build_final_prompt(session: dict) -> str:
    analyses = eval(session.get("ai_analyses", "[]"))
    descriptions = eval(session.get("user_descriptions", "[]"))
    product_desc = ". ".join(filter(None, analyses + descriptions))

    if session.get("model_type") == "ai":
        gender = session.get("ai_gender", "female")
        gender_en = "male" if gender and gender.lower() in ("laki-laki", "male") else "female"
        age = session.get("ai_age_group", "adult")
        age_map = {"anak-anak": "child", "remaja": "teenager", "dewasa": "adult"}
        age_en = age_map.get(age.lower(), "adult")

        return (
            f"A {age_en} {gender_en} model confidently holding/wearing "
            f"the product: {product_desc}. The product is the main focus, "
            f"clearly visible. Professional studio photography, soft diffused "
            f"lighting, plain pastel background, high quality, photorealistic, "
            f"commercial product photography, 4K, highly detailed."
        )
    else:
        return (
            f"A model wearing/using the product: {product_desc}. "
            f"The product is the main focus, clearly visible. "
            f"Professional studio photography, soft lighting, plain background, "
            f"high quality, photorealistic, commercial product photography, 4K."
        )


async def _generate_and_show_preview(update: Update, context, retry_count: int = 0):
    chat_id = update.effective_chat.id
    session = db.get_session(chat_id)

    prompt = _build_product_prompt(session, retry_count)

    try:
        image_bytes = generate_image(prompt)
        photo_path = save_photo(image_bytes, "generated")

        db.log_generation(chat_id, prompt, photo_path, "preview")

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=open(photo_path, "rb"),
            caption="🤖 *Hasil Generate Model AI*\n\nApakah model ini sudah sesuai?",
            parse_mode="Markdown",
        )

        keyboard = [
            [InlineKeyboardButton("✅ Ya, lanjutkan", callback_data="ai_ok")],
            [InlineKeyboardButton("🔄 Tidak, generate ulang", callback_data="ai_retry")],
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text="Pilih:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return WAITING_AI_CONFIRM

    except Exception as e:
        logger.error(f"Generation error: {e}")
        keyboard = [
            [InlineKeyboardButton("🔄 Coba lagi", callback_data="ai_retry")],
            [InlineKeyboardButton("❌ Batalkan", callback_data="cancel_conv")],
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Gagal generate: {str(e)[:150]}\n\nCoba lagi?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return WAITING_AI_CONFIRM


async def _generate_final_and_send(update: Update, context):
    chat_id = update.effective_chat.id
    session = db.get_session(chat_id)

    prompt = _build_final_prompt(session)

    try:
        image_bytes = generate_image(prompt)
        photo_path = save_photo(image_bytes, "final")

        db.log_generation(chat_id, prompt, photo_path, "final")
        db.update_session(chat_id, step="completed")

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=open(photo_path, "rb"),
            caption=(
                "🎉 *Foto Utama Berhasil Dibuat!*\n\n"
                "Terima kasih telah menggunakan UGC Bot! 😊\n\n"
                "Kirim /start untuk membuat baru."
            ),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Final generation error: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"⚠️ Gagal generate foto utama: {str(e)[:200]}\n\n"
                "Kirim /start untuk mencoba lagi."
            ),
        )
        return ConversationHandler.END


# ── Entry ────────────────────────────────────────────────────────────────

async def start(update: Update, context):
    chat_id = update.effective_chat.id
    db.create_session(chat_id)

    await update.message.reply_text(
        "🤖 *Selamat datang di UGC Bot!*\n\n"
        "Bot ini akan membantu Anda membuat foto produk affiliate "
        "dengan model AI.\n\n"
        "Silakan kirim **foto produk** yang ingin digunakan.\n"
        "(Kirim 1 foto dulu ya 😊)",
        parse_mode="Markdown",
    )
    return WAITING_PRODUCT_PHOTO


# ── State 0: WAITING_PRODUCT_PHOTO ──────────────────────────────────────

async def handle_product_photo(update: Update, context):
    chat_id = update.effective_chat.id

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    photo_path = save_photo(bytes(photo_bytes), "products")

    session = db.get_session(chat_id)
    photos = eval(session.get("product_photos", "[]")) if session else []
    photos.append(photo_path)
    db.update_session(chat_id, product_photos=str(photos))

    await update.message.reply_text(
        "📸 Foto diterima! Sekarang AI akan menganalisa detail produk...\n"
        "Mohon tunggu sebentar ⏳"
    )

    try:
        analysis = analyze_image(photo_path)
        analyses = eval(session.get("ai_analyses", "[]")) if session else []
        analyses.append(analysis)
        db.update_session(chat_id, ai_analyses=str(analyses))

        await update.message.reply_text(
            f"✅ *Hasil Analisa AI:*\n{analysis}\n\n"
            "Silakan tambahkan **keterangan dari Anda** tentang produk ini:\n"
            "(contoh: merek, bahan, ukuran, harga, keunggulan, dll)",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Vision error: {e}")
        await update.message.reply_text(
            "⚠️ Gagal menganalisa gambar. Silakan langsung masukkan "
            "keterangan produk Anda:\n"
            "(contoh: merek, bahan, ukuran, harga, keunggulan, dll)"
        )

    return WAITING_DESCRIPTION


# ── State 1: WAITING_DESCRIPTION ────────────────────────────────────────

async def handle_description(update: Update, context):
    chat_id = update.effective_chat.id
    description = update.message.text

    session = db.get_session(chat_id)
    descriptions = eval(session.get("user_descriptions", "[]")) if session else []
    descriptions.append(description)
    db.update_session(chat_id, user_descriptions=str(descriptions))

    keyboard = [
        [InlineKeyboardButton("✅ Ya, tambah foto", callback_data="add_photo_yes")],
        [InlineKeyboardButton("❌ Tidak, lanjutkan", callback_data="add_photo_no")],
    ]
    await update.message.reply_text(
        "📝 Keterangan disimpan!\n\n"
        "Apakah Anda ingin menambahkan **foto tambahan** produk ini?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return ASKING_ADD_PHOTO


# ── State 2: ASKING_ADD_PHOTO ──────────────────────────────────────────

async def handle_add_photo_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if query.data == "add_photo_yes":
        await query.edit_message_text("📸 Silakan kirim **foto tambahan** produk.", parse_mode="Markdown")
        return WAITING_ADDITIONAL_PHOTO

    await query.edit_message_text("✅ Baik, lanjut ke pemilihan model...")
    return await _ask_model_type(update, context)


# ── State 3: WAITING_ADDITIONAL_PHOTO ──────────────────────────────────

async def handle_additional_photo(update: Update, context):
    chat_id = update.effective_chat.id

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    photo_path = save_photo(bytes(photo_bytes), "products")

    session = db.get_session(chat_id)
    photos = eval(session.get("product_photos", "[]"))
    photos.append(photo_path)
    db.update_session(chat_id, product_photos=str(photos))

    await update.message.reply_text("📸 Foto diterima! Menganalisa... ⏳")

    try:
        analysis = analyze_image(photo_path)
        analyses = eval(session.get("ai_analyses", "[]"))
        analyses.append(analysis)
        db.update_session(chat_id, ai_analyses=str(analyses))

        await update.message.reply_text(
            f"✅ *Hasil Analisa:*\n{analysis}\n\n"
            "Silakan masukkan **keterangan untuk foto ini**:",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Vision error on additional: {e}")
        await update.message.reply_text(
            "⚠️ Gagal menganalisa. Silakan masukkan **keterangan untuk foto ini**:"
        )

    return WAITING_PHOTO_DESC


# ── State 4: WAITING_PHOTO_DESC ────────────────────────────────────────

async def handle_photo_desc(update: Update, context):
    chat_id = update.effective_chat.id
    description = update.message.text

    session = db.get_session(chat_id)
    descriptions = eval(session.get("user_descriptions", "[]"))
    descriptions.append(description)
    db.update_session(chat_id, user_descriptions=str(descriptions))

    keyboard = [
        [InlineKeyboardButton("✅ Ya, tambah lagi", callback_data="add_photo_yes")],
        [InlineKeyboardButton("❌ Tidak, selesai", callback_data="add_photo_no")],
    ]
    await update.message.reply_text(
        "✅ Disimpan! Tambah foto lagi?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASKING_ADD_PHOTO


# ── State 5: CHOOSING_MODEL_TYPE ───────────────────────────────────────

async def _ask_model_type(update: Update, context):
    query = update.callback_query
    if query:
        await query.answer()

    keyboard = [
        [InlineKeyboardButton("🤖 Buat dengan AI", callback_data="model_ai")],
        [InlineKeyboardButton("📸 Upload foto model", callback_data="model_upload")],
    ]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "Sekarang, pilih jenis model:\n\n"
            "🤖 *Buat dengan AI* — AI akan generate model sesuai keinginan\n"
            "📸 *Upload Foto Model* — Kirim foto model sendiri"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return CHOOSING_MODEL_TYPE


async def handle_model_type_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if query.data == "model_ai":
        db.update_session(chat_id, model_type="ai")

        keyboard = [
            [InlineKeyboardButton("👨 Laki-laki", callback_data="gender_male")],
            [InlineKeyboardButton("👩 Perempuan", callback_data="gender_female")],
        ]
        await query.edit_message_text(
            "Pilih **jenis kelamin** model:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return WAITING_GENDER

    db.update_session(chat_id, model_type="upload")
    await query.edit_message_text(
        "📸 Silakan kirim **foto model** yang akan digunakan.\n"
        "(Pastikan wajah dan tubuh terlihat jelas, latar sederhana)",
        parse_mode="Markdown",
    )
    return WAITING_MODEL_UPLOAD


# ── State 6: WAITING_GENDER ────────────────────────────────────────────

async def handle_gender_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    gender_map = {"gender_male": "Laki-laki", "gender_female": "Perempuan"}
    db.update_session(chat_id, ai_gender=gender_map[query.data])

    keyboard = [
        [InlineKeyboardButton("🧒 Anak-anak", callback_data="age_child")],
        [InlineKeyboardButton("🧑 Remaja", callback_data="age_teen")],
        [InlineKeyboardButton("👨 Dewasa", callback_data="age_adult")],
    ]
    await query.edit_message_text(
        "Pilih **kelompok usia** model:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return WAITING_AGE_GROUP


# ── State 7: WAITING_AGE_GROUP ─────────────────────────────────────────

async def handle_age_group_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    age_map = {"age_child": "Anak-anak", "age_teen": "Remaja", "age_adult": "Dewasa"}
    db.update_session(chat_id, ai_age_group=age_map[query.data])

    await query.edit_message_text(
        "🎨 AI sedang menghasilkan model...\nMohon tunggu 30-60 detik ⏳"
    )

    return await _generate_and_show_preview(update, context, retry_count=0)


# ── State 8: WAITING_AI_CONFIRM ────────────────────────────────────────

async def handle_ai_confirm(update: Update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if query.data == "ai_ok":
        await query.edit_message_text(
            "✅ Model disetujui! Sekarang AI akan membuat **foto utama**...\nMohon tunggu ⏳",
            parse_mode="Markdown",
        )
        return await _generate_final_and_send(update, context)

    if query.data == "ai_retry":
        await query.edit_message_text(
            "🔄 AI akan generate ulang dengan variasi berbeda...\nMohon tunggu ⏳"
        )
        retry_count = context.user_data.get("retry_count", 0) + 1
        context.user_data["retry_count"] = retry_count
        return await _generate_and_show_preview(update, context, retry_count)

    if query.data == "cancel_conv":
        await query.edit_message_text("❌ Dibatalkan. Kirim /start untuk memulai lagi.")
        return ConversationHandler.END

    return WAITING_AI_CONFIRM


# ── State 9: WAITING_MODEL_UPLOAD ──────────────────────────────────────

async def handle_model_upload(update: Update, context):
    chat_id = update.effective_chat.id

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    photo_path = save_photo(bytes(photo_bytes), "models")

    db.update_session(chat_id, model_photo_path=photo_path)

    msg = await update.message.reply_text(
        "📸 Foto model diterima! AI akan membuat **foto utama**...\nMohon tunggu ⏳",
        parse_mode="Markdown",
    )

    return await _generate_final_and_send(update, context)


# ── Cancel ─────────────────────────────────────────────────────────────

async def cancel(update: Update, context):
    await update.message.reply_text("❌ Dibatalkan. Kirim /start untuk memulai lagi.")
    return ConversationHandler.END


# ── ConversationHandler ─────────────────────────────────────────────────

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        WAITING_PRODUCT_PHOTO: [
            MessageHandler(filters.PHOTO, handle_product_photo)
        ],
        WAITING_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)
        ],
        ASKING_ADD_PHOTO: [
            CallbackQueryHandler(handle_add_photo_choice, pattern="^add_photo_")
        ],
        WAITING_ADDITIONAL_PHOTO: [
            MessageHandler(filters.PHOTO, handle_additional_photo)
        ],
        WAITING_PHOTO_DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_photo_desc)
        ],
        CHOOSING_MODEL_TYPE: [
            CallbackQueryHandler(handle_model_type_choice, pattern="^model_")
        ],
        WAITING_GENDER: [
            CallbackQueryHandler(handle_gender_choice, pattern="^gender_")
        ],
        WAITING_AGE_GROUP: [
            CallbackQueryHandler(handle_age_group_choice, pattern="^age_")
        ],
        WAITING_AI_CONFIRM: [
            CallbackQueryHandler(handle_ai_confirm, pattern="^(ai_ok|ai_retry|cancel_conv)$")
        ],
        WAITING_MODEL_UPLOAD: [
            MessageHandler(filters.PHOTO, handle_model_upload)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=False,
)
