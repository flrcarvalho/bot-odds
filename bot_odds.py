import logging
import os
import psycopg2
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN      = "8985257228:AAFqxNiOza219IYoK-wh4KenzNxD_8OEnGA"
SOURCE_CHAT_ID = -1003726885598
DEST_CHAT_ID   = -1003891414309

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:ZvgIRmrRwvJUGmwNMkniZovbtnpdKSUs@postgres.railway.internal:5432/railway")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS message_map (
                    source_msg_id BIGINT PRIMARY KEY,
                    dest_msg_id   BIGINT NOT NULL
                )
            """)
        conn.commit()
    logger.info("Banco inicializado.")

def save_mapping(source_id: int, dest_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO message_map (source_msg_id, dest_msg_id)
                VALUES (%s, %s)
                ON CONFLICT (source_msg_id) DO UPDATE SET dest_msg_id = EXCLUDED.dest_msg_id
            """, (source_id, dest_id))
        conn.commit()

def get_mapping(source_id: int) -> int | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT dest_msg_id FROM message_map WHERE source_msg_id = %s", (source_id,))
            row = cur.fetchone()
            return row[0] if row else None

def is_under(text: str) -> bool:
    return "UNDER" in text.upper()

def format_message(text: str) -> str:
    lines = [l for l in text.strip().split("\n") if l.strip()]

    if text.upper().startswith("ATENTOS"):
        return f"⚠️ *ATENÇÃO* ⚠️\n\n{text}"

    if "UNDER" in (lines[0].upper() if lines else "") and len(lines) >= 4:
        title   = lines[0]
        line    = lines[1] if len(lines) > 1 else ""
        stake   = lines[2] if len(lines) > 2 else ""
        odd_raw = lines[3] if len(lines) > 3 else ""

        if "❌" in odd_raw:
            resultado = "❌ *VERMELHO*"
            odd = odd_raw.replace("❌", "").strip()
        elif "✅" in odd_raw:
            resultado = "✅ *VERDE*"
            odd = odd_raw.replace("✅", "").strip()
        elif "🔄" in odd_raw:
            resultado = "🔄 *EM ABERTO*"
            odd = odd_raw.replace("🔄", "").strip()
        else:
            resultado = ""
            odd = odd_raw.strip()

        msg  = f"🎯 *{title}*\n\n"
        msg += f"📊 Linha: `{line}`\n"
        msg += f"💰 Stake: `{stake}`\n"
        msg += f"📈 Odd: `{odd}`\n"
        if resultado:
            msg += f"\nResultado: {resultado}"
        return msg

    return text

async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if update.effective_chat.id != SOURCE_CHAT_ID:
        return

    text = message.text or message.caption or ""
    if not is_under(text):
        return

    logger.info(f"UNDER detectado (nova): {text[:80]}")
    formatted = format_message(text)

    try:
        sent = await context.bot.send_message(
            chat_id=DEST_CHAT_ID,
            text=formatted,
            parse_mode=ParseMode.MARKDOWN
        )
        save_mapping(message.message_id, sent.message_id)
        logger.info(f"Enviado: origem {message.message_id} -> destino {sent.message_id}")
    except Exception as e:
        logger.error(f"Erro ao enviar: {e}")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.edited_message
    if not message or update.effective_chat.id != SOURCE_CHAT_ID:
        return

    text = message.text or message.caption or ""
    if not is_under(text):
        return

    dest_msg_id = get_mapping(message.message_id)
    if not dest_msg_id:
        logger.info(f"Edição sem mapeamento para {message.message_id} — enviando como nova.")
        update.message = message
        await handle_new_message(update, context)
        return

    logger.info(f"UNDER editado: {text[:80]}")
    formatted = format_message(text)

    try:
        await context.bot.edit_message_text(
            chat_id=DEST_CHAT_ID,
            message_id=dest_msg_id,
            text=formatted,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Editado no destino: {dest_msg_id}")
    except Exception as e:
        logger.error(f"Erro ao editar: {e}")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_new_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))
    logger.info("Bot iniciado. Aguardando mensagens...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
