import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ============================================================
# CONFIGURAÇÃO
# ============================================================
BOT_TOKEN = "8729683426:AAHjSFRHfog8bZAUBPUCNdTVlLOYNvYYj10"

logging.basicConfig(level=logging.INFO)

# ============================================================
# DICIONÁRIO DE CASAS DE APOSTAS
# ============================================================
HOUSE_NAMES = {
    "DK":       "DraftKings",
    "FD":       "FanDuel",
    "MGM":      "BetMGM",
    "CZR":      "Caesars Sportsbook",
    "Fanatics": "Fanatics Sportsbook",
    "TheScore": "theScore Bet",
    "ESB":      "ESPN Bet",
    "BRV":      "Bally's Bet",
}

# ============================================================
# DICIONÁRIO DE MERCADOS
# ============================================================
MARKET_TRANSLATIONS = {
    # MLB — Pitcher Props
    "K":    {"under": "Under {n} Strikeouts",       "over": "Over {n} Strikeouts",       "desc": "strikeouts (ponches) do pitcher"},
    "HA":   {"under": "Under {n} Hits Allowed",     "over": "Over {n} Hits Allowed",     "desc": "rebatidas (hits) permitidas pelo pitcher"},
    "ER":   {"under": "Under {n} Earned Runs",      "over": "Over {n} Earned Runs",      "desc": "corridas sofridas pelo pitcher"},
    "BB":   {"under": "Under {n} Walks",            "over": "Over {n} Walks",            "desc": "bases por bola (walks) concedidas pelo pitcher"},
    "outs": {"under": "Under {n} Outs (~{inn} inn)", "over": "Over {n} Outs (~{inn} inn)", "desc": "eliminações registradas (~{inn} innings)"},
    # NBA / WNBA — Player Props
    "PRA":      {"under": "Under {n} Pts+Reb+Ast",      "over": "Over {n} Pts+Reb+Ast",      "desc": "Pontos + Rebotes + Assistências"},
    "points":   {"under": "Under {n} Pontos",           "over": "Over {n} Pontos",           "desc": "pontos marcados pelo jogador"},
    "assists":  {"under": "Under {n} Assistências",     "over": "Over {n} Assistências",     "desc": "assistências do jogador"},
    "rebounds": {"under": "Under {n} Rebotes",          "over": "Over {n} Rebotes",          "desc": "rebotes do jogador"},
    "PR":       {"under": "Under {n} Pts+Reb",          "over": "Over {n} Pts+Reb",          "desc": "Pontos + Rebotes"},
    "PA":       {"under": "Under {n} Pts+Ast",          "over": "Over {n} Pts+Ast",          "desc": "Pontos + Assistências"},
    "RA":       {"under": "Under {n} Reb+Ast",          "over": "Over {n} Reb+Ast",          "desc": "Rebotes + Assistências"},
    "3PM":      {"under": "Under {n} Cestas de 3pts",   "over": "Over {n} Cestas de 3pts",   "desc": "cestas de 3 pontos convertidas"},
    "blocks":   {"under": "Under {n} Bloqueios",        "over": "Over {n} Bloqueios",        "desc": "bloqueios (tocos) do jogador"},
    "steals":   {"under": "Under {n} Roubos de Bola",   "over": "Over {n} Roubos de Bola",   "desc": "roubos de bola do jogador"},
    "mins":     {"under": "Under {n} Minutos",          "over": "Over {n} Minutos",          "desc": "minutos em quadra"},
}

# ============================================================
# EMOJI POR ESPORTE
# ============================================================
def get_sport_emoji(title: str) -> str:
    t = (title or "").upper()
    if "MLB"  in t: return "⚾"
    if "WNBA" in t: return "🏀"
    if "NBA"  in t: return "🏀"
    if "NFL"  in t: return "🏈"
    if "NHL"  in t: return "🏒"
    return "🎲"

# ============================================================
# CONVERSÃO DE ODD AMERICANA → DECIMAL
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
    Suporta os formatos:
      - MLB Pick- Time A vs Time B           (SharpDuel Bot)
      - MLB Pick #4- Time A vs Time B        (numerado)
      - **MLB Pick #2- ...**                 (com markdown **)
      - MLB Pick Thursday- ...              (com dia da semana)
      - Xu: Jogador mercado odd (casa)
      - Xu Jogador mercado odd (casa)        (sem dois pontos)
      - K + 114                              (espaço no sinal)
      - BB-113                              (odd colada ao mercado)
      - picks sem título (mensagem isolada)
    """
    picks = []

    # Remove marcação markdown **...**
    text_clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

    # Padrão título: ex. "MLB Pick-", "NBA Playoffs Pick #2-", "MLB Pick Thursday-"
    title_pattern = re.compile(
        r'^(\*{0,2}[A-Z]{2,5}[^:\n]*Pick[^:\n]*[-–:]\s*.+?)\*{0,2}$',
        re.IGNORECASE | re.MULTILINE,
    )

    # Linha de pick
    pick_line_pattern = re.compile(
        r'^(\d*\.?\d+u)\s*:?\s*(.+?)\s*([+-]\s*\d{2,4})\s*\((\w+)\)\s*$',
        re.IGNORECASE | re.MULTILINE,
    )

    titles = [(m.start(), m.group(1).strip()) for m in title_pattern.finditer(text_clean)]

    if titles:
        for i, (title_pos, title_text) in enumerate(titles):
            search_start = title_pos + len(title_text)
            search_end = titles[i + 1][0] if i + 1 < len(titles) else len(text_clean)
            segment = text_clean[search_start:search_end]
            m = pick_line_pattern.search(segment)
            if m:
                odd_am = int(m.group(3).replace(" ", ""))
                picks.append({
                    "title":   title_text,
                    "units":   m.group(1).strip(),
                    "market":  m.group(2).strip(),
                    "odd_am":  odd_am,
                    "odd_br":  american_to_decimal(odd_am),
                    "house":   m.group(4).strip(),
                })
    else:
        # Sem título: tenta capturar pick isolado
        m = pick_line_pattern.search(text_clean)
        if m:
            odd_am = int(m.group(3).replace(" ", ""))
            picks.append({
                "title":   None,
                "units":   m.group(1).strip(),
                "market":  m.group(2).strip(),
                "odd_am":  odd_am,
                "odd_br":  american_to_decimal(odd_am),
                "house":   m.group(4).strip(),
            })

    return picks

# ============================================================
# INTERPRETA O MERCADO
# ============================================================
def interpret_market(market_raw: str) -> dict:
    """
    Recebe 'u4.5 K', 'Jogador u4.5 K', 'o2.5 ER', etc.
    Extrai a parte de mercado (direção + linha + código) mesmo que venha precedida do nome do jogador.
    """
    # Tenta encontrar padrão [u/o][número] [código] em qualquer posição da string
    m = re.search(r'([uo])([\d.]+)\s+([A-Za-z]+)(?:\s|$)', market_raw.strip(), re.IGNORECASE)
    if not m:
        m = re.match(r'^([uo])([\d.]+)\s*(.+)$', market_raw.strip(), re.IGNORECASE)
    if not m:
        return {"direction": None, "line": None, "code": market_raw, "label": market_raw, "desc": None}

    direction = m.group(1).lower()
    line      = m.group(2)
    code      = m.group(3).strip()

    direction_word = "under" if direction == "u" else "over"
    direction_sym  = "🔵 UNDER" if direction == "u" else "🔴 OVER"

    mkt = MARKET_TRANSLATIONS.get(code, {})
    label_tmpl = mkt.get(direction_word, f"{direction.upper()}{line} {code}")
    desc_tmpl  = mkt.get("desc", None)

    # Substitui {n} e {inn}
    innings = str(round(float(line) / 3, 1)) if code == "outs" else ""
    label = label_tmpl.replace("{n}", line).replace("{inn}", innings)
    desc  = desc_tmpl.replace("{n}", line).replace("{inn}", innings) if desc_tmpl else None

    return {
        "direction": direction,
        "direction_sym": direction_sym,
        "line": line,
        "code": code,
        "label": label,
        "desc": desc,
    }

# ============================================================
# FORMATA A RESPOSTA
# ============================================================
def format_response(picks: list[dict]) -> str:
    if not picks:
        return None

    lines = ["🎯 *Odds convertidas (padrão BR):*\n"]

    for p in picks:
        odd_am  = p["odd_am"]
        odd_br  = p["odd_br"]
        house   = HOUSE_NAMES.get(p["house"], p["house"])
        odd_str = f"+{odd_am}" if odd_am > 0 else str(odd_am)
        units   = p["units"]
        mkt     = interpret_market(p["market"])

        # Título com emoji de esporte
        sport_emoji = get_sport_emoji(p["title"])
        title_line = f"{sport_emoji} *{p['title']}*" if p["title"] else "🎲 *Pick detectado*"

        # Mercado traduzido
        market_line = f"{mkt['direction_sym']} {mkt['line']} {mkt['code']} → {mkt['label']}" if mkt["direction"] else p["market"]

        # Glossário dinâmico
        glossary = []
        if mkt["desc"]:
            glossary.append(f"• `{mkt['direction'].upper() if mkt['direction'] else ''}{mkt['line']} {mkt['code']}` → {mkt['desc']}")

        unit_map = {".5u": "meia unidade — aposta pequena/especulativa", "1u": "1 unidade — pick padrão", "2u": "2 unidades — alta convicção"}
        glossary.append(f"• `{units}` → {unit_map.get(units, 'unidades de aposta')}")

        if odd_am > 0:
            glossary.append(f"• `{odd_str}` → azarão — lucro de R${odd_am} para cada R$100 apostados")
        else:
            glossary.append(f"• `{odd_str}` → favorito — aposte R${abs(odd_am)} para lucrar R$100")

        glossary_text = "\n".join(glossary)

        # Busca equivalente
        # Termo de busca: pega a parte descritiva do label (ex: "Hits Allowed", "Strikeouts")
        label_words = mkt['label'].split()
        search_term = " ".join(label_words[2:]) if len(label_words) > 2 else mkt['code']

        lines.append(
            f"{title_line}\n"
            f"💰 *{units}*\n"
            f"🎟️ {p['market']} → {mkt['label']}\n"
            f"📈 Odd americana: `{odd_str}` → Odd decimal: *{odd_br}*\n"
            f"🏡 Casa: {house} 🇺🇸\n\n"
            f"📖 *O que significa:*\n"
            f"{glossary_text}\n\n"
            f"⚠️ _{house} é uma casa americana. Busque \"{search_term}\" na Bet365 ou Betano._\n"
        )

    return "\n".join(lines)

# ============================================================
# HANDLER
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    # Ignora respostas do próprio bot
    if "Odd americana:" in text or "Odds convertidas" in text:
        return

    chat_id  = update.message.chat_id
    chat_type = update.message.chat.type
    print(f"[MSG] chat_id={chat_id} tipo={chat_type}")
    print(f"[TEXTO] {repr(text[:200])}")

    picks = parse_picks(text)
    print(f"[PICKS] {picks}")

    response = format_response(picks)

    if response:
        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        print("[SEM RESPOSTA] nenhum pick encontrado")

# ============================================================
# MAIN
# ============================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot rodando! Aguardando mensagens...")
    app.run_polling()

if __name__ == "__main__":
    main()
