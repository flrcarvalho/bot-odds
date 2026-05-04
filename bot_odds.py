import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ============================================================
# CONFIGURAÇÃO — coloque seu token aqui
# ============================================================
BOT_TOKEN = "SEU_TOKEN_AQUI"


logging.basicConfig(level=logging.INFO)


# ============================================================
# CONVERSÃO DE ODD AMERICANA → DECIMAL (padrão BR)
# ============================================================
def american_to_decimal(american: int) -> float:
    if american < 0:
        return round((100 + abs(american)) / abs(american), 2)
    else:
        return round((american + 100) / 100, 2)


# ============================================================
# PARSER DA MENSAGEM
# ============================================================
def parse_picks(text: str) -> list[dict]:
    """
    Extrai picks da mensagem no formato:
      MLB Pick- Time A vs Time B
      Xu: Jogador mercado odd (casa)
    Retorna lista de dicts com os dados de cada pick.
    """
    picks = []

    # Padrão: linha com "Pick" seguida de linha com odd americana
    # Captura: unidades, jogador/mercado, odd americana, casa
    pick_pattern = re.compile(
        r"([A-Z]{2,5}[^:\n]*Pick[^:\n]*[:\-–]\s*.+)\n"  # linha do título ex: MLB Pick-, NBA Playoffs Pick-
        r"([0-9.]+u)\s*:\s*(.+?)\s+([+-]\d+)\s+\((\w+)\)",
        re.IGNORECASE,
    )

    for m in pick_pattern.finditer(text):
        title    = m.group(1).strip()
        units    = m.group(2).strip()
        market   = m.group(3).strip()
        odd_am   = int(m.group(4))
        house    = m.group(5).strip()
        odd_br   = american_to_decimal(odd_am)

        picks.append({
            "title":  title,
            "units":  units,
            "market": market,
            "odd_am": odd_am,
            "odd_br": odd_br,
            "house":  house,
        })

    return picks


# ============================================================
# FORMATA A RESPOSTA
# ============================================================
def format_response(picks: list[dict]) -> str:
    if not picks:
        return None

    lines = ["🎯 *Odds convertidas (padrão BR):*\n"]
    for p in picks:
        odd_str = f"+{p['odd_am']}" if p['odd_am'] > 0 else str(p['odd_am'])
        lines.append(
            f"📌 *{p['title']}*\n"
            f"   {p['units']}: {p['market']}\n"
            f"   Odd americana: `{odd_str}` → Odd decimal: *{p['odd_br']}*\n"
            f"   Casa: {p['house']}\n"
        )

    return "\n".join(lines)


# ============================================================
# HANDLER
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    picks = parse_picks(text)
    response = format_response(picks)

    if response:
        await update.message.reply_text(response, parse_mode="Markdown")


# ============================================================
# MAIN
# ============================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # Monitora TODAS as mensagens de texto (grupos e privado)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot rodando! Aguardando mensagens...")
    app.run_polling()


if __name__ == "__main__":
    main()
