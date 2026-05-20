import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ============================================================
# CONFIGURAÇÃO — coloque seu token aqui
# ============================================================
BOT_TOKEN = "8729683426:AAHjSFRHfog8bZAUBPUCNdTVlLOYNvYYj10"


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
    Extrai picks da mensagem nos formatos:
      MLB Pick- Time A vs Time B          (SharpDuel Bot)
      MLB Pick #4- Time A vs Time B       (theundergroundlab24)
      Xu: Jogador mercado odd (casa)
      Xu: Jogador mercado odd(casa)       (sem espaço antes do parêntese)
      Xu: Jogador mercadoodd (casa)       (odd colada no mercado, ex: BB-113)

    Retorna lista de dicts com os dados de cada pick.
    """
    picks = []

    # Linha de título: qualquer coisa com "Pick" seguida de separador
    title_pattern = re.compile(
        r"^([A-Z]{2,5}[^:\n]*Pick[^:\n]*[-–:]\s*.+)$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Linha de pick:
    #   unidades (ex: 1u, .5u, 0.5u)
    #   : mercado (qualquer texto)
    #   odd americana (+/-NNN) — pode estar colada ao mercado ou separada por espaço
    #   (casa) — com ou sem espaço antes do parêntese
    pick_line_pattern = re.compile(
        r"^(\d*\.?\d+u)\s*:\s*(.+?)\s*([+-]\d{2,4})\s*\((\w+)\)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Encontra todos os títulos e suas posições
    titles = [(m.start(), m.group(1).strip()) for m in title_pattern.finditer(text)]

    if not titles:
        return picks

    # Para cada título, procura a linha de pick imediatamente após
    for i, (title_pos, title_text) in enumerate(titles):
        # Delimita a busca: do fim do título até o próximo título (ou fim do texto)
        search_start = title_pos + len(title_text)
        search_end = titles[i + 1][0] if i + 1 < len(titles) else len(text)
        segment = text[search_start:search_end]

        m = pick_line_pattern.search(segment)
        if m:
            units   = m.group(1).strip()
            market  = m.group(2).strip()
            odd_am  = int(m.group(3))
            house   = m.group(4).strip()
            odd_br  = american_to_decimal(odd_am)

            picks.append({
                "title":  title_text,
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
