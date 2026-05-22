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
    # ── MLB — Lançador (nomes Bet365 BR) ──────────────────────────────
    "K":        {"under": "Menos de {n} Strikeouts",               "over": "Mais de {n} Strikeouts",               "desc": "Lançador - Strikeouts (Mais de/Menos de)"},
    "HA":       {"under": "Menos de {n} Hits Permitidos",          "over": "Mais de {n} Hits Permitidos",          "desc": "Lançador - Hits Permitidos (Mais de/Menos de)"},
    "ER":       {"under": "Menos de {n} Earned Runs",              "over": "Mais de {n} Earned Runs",              "desc": "Pitcher Earned Runs O/U"},
    "BB":       {"under": "Menos de {n} Walks Atribuídos",         "over": "Mais de {n} Walks Atribuídos",         "desc": "Lançador - Walks Atribuídos (Mais de/Menos de)"},
    "outs":     {"under": "Menos de {n} Outs (~{inn} inn)",        "over": "Mais de {n} Outs (~{inn} inn)",        "desc": "Lançador - Outs (Mais de/Menos de)"},
    # ── MLB — Rebatedor (nomes Bet365 BR) ─────────────────────────────
    "hits":     {"under": "Menos de {n} Hits",                     "over": "Mais de {n} Hits",                     "desc": "Hits (Mais de/Menos de)"},
    "HR":       {"under": "Menos de {n} Home Runs",                "over": "Mais de {n} Home Runs",                "desc": "Home Runs (Mais de/Menos de)"},
    "RBI":      {"under": "Menos de {n} Runs Batted In",           "over": "Mais de {n} Runs Batted In",           "desc": "Runs Batted In (Mais de/Menos de)"},
    "runs":     {"under": "Menos de {n} Runs",                     "over": "Mais de {n} Runs",                     "desc": "Runs (Mais de/Menos de)"},
    "TB":       {"under": "Menos de {n} Total de Bases",           "over": "Mais de {n} Total de Bases",           "desc": "Total de Bases (Mais de/Menos de)"},
    "HRR":      {"under": "Menos de {n} Total Hits+Runs+RBIs",     "over": "Mais de {n} Total Hits+Runs+RBIs",     "desc": "Total de Hits, Runs e RBIs"},
    "SB":       {"under": "Menos de {n} Bases Roubadas",           "over": "Mais de {n} Bases Roubadas",           "desc": "Bases Roubadas (Mais de/Menos de)"},
    # ── NBA / WNBA — Player Props ──────────────────────────────────────
    "PRA":      {"under": "Menos de {n} Pts+Reb+Ast",              "over": "Mais de {n} Pts+Reb+Ast",              "desc": "Pontos + Rebotes + Assistências do jogador"},
    "points":   {"under": "Menos de {n} Pontos",                   "over": "Mais de {n} Pontos",                   "desc": "Pontos marcados pelo jogador"},
    "assists":  {"under": "Menos de {n} Assistências",             "over": "Mais de {n} Assistências",             "desc": "Assistências do jogador"},
    "rebounds": {"under": "Menos de {n} Rebotes",                  "over": "Mais de {n} Rebotes",                  "desc": "Rebotes do jogador"},
    "PR":       {"under": "Menos de {n} Pts+Reb",                  "over": "Mais de {n} Pts+Reb",                  "desc": "Pontos + Rebotes do jogador"},
    "PA":       {"under": "Menos de {n} Pts+Ast",                  "over": "Mais de {n} Pts+Ast",                  "desc": "Pontos + Assistências do jogador"},
    "RA":       {"under": "Menos de {n} Reb+Ast",                  "over": "Mais de {n} Reb+Ast",                  "desc": "Rebotes + Assistências do jogador"},
    "3PM":      {"under": "Menos de {n} Cestas de 3 Pontos",       "over": "Mais de {n} Cestas de 3 Pontos",       "desc": "Cestas de 3 pontos convertidas"},
    "blocks":   {"under": "Menos de {n} Bloqueios",                "over": "Mais de {n} Bloqueios",                "desc": "Bloqueios (tocos) do jogador"},
    "steals":   {"under": "Menos de {n} Roubos de Bola",           "over": "Mais de {n} Roubos de Bola",           "desc": "Roubos de bola do jogador"},
    "mins":     {"under": "Menos de {n} Minutos",                  "over": "Mais de {n} Minutos",                  "desc": "Minutos em quadra"},
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
def excel_round(value: float, decimals: int) -> float:
    """Arredondamento igual ao Excel (half up)."""
    import math
    factor = 10 ** decimals
    return math.floor(value * factor + 0.5) / factor

def american_to_decimal(american: int) -> float:
    if american < 0:
        return excel_round((100 + abs(american)) / abs(american), 2)
    else:
        return excel_round((american + 100) / 100, 2)

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
        odd_min = excel_round(odd_br * 0.96, 2)
        house   = HOUSE_NAMES.get(p["house"], p["house"])
        odd_str = f"+{odd_am}" if odd_am > 0 else str(odd_am)

        # Formata odd decimal com vírgula (padrão BR) e 2 casas sempre
        odd_br_str  = f"{odd_br:.2f}".replace(".", ",")
        odd_min_str = f"{odd_min:.2f}".replace(".", ",")

        # Normaliza unidades: .5u → 0.5u
        units_raw = p["units"]
        units = re.sub(r'^\.(\d)', r'0.\1', units_raw)

        mkt = interpret_market(p["market"])

        # Título com emoji de esporte
        sport_emoji = get_sport_emoji(p["title"])
        title_line = f"{sport_emoji} *{p['title']}*" if p["title"] else "🎲 *Pick detectado*"

        # Glossário dinâmico — só o mercado
        glossary = []
        if mkt["desc"]:
            glossary.append(f"• `{(mkt['direction'] or '').upper()}{mkt['line']} {mkt['code']}` → {mkt['desc']}")

        glossary_text = "\n".join(glossary) if glossary else ""
        glossary_block = f"\n📖 *O que significa:*\n{glossary_text}" if glossary_text else ""

        # Termo de busca: parte descritiva do label
        label_words = mkt['label'].split()
        search_term = " ".join(label_words[2:]) if len(label_words) > 2 else mkt['code']

        lines.append(
            f"{title_line}\n"
            f"💰 *{units}*\n"
            f"🎟️ {p['market']} → {mkt['label']}\n"
            f"📉 Odd americana: `{odd_str}`\n"
            f"📈 Odd decimal: *{odd_br_str}*\n"
            f"🚫 Odd mínima: *{odd_min_str}*\n"
            f"🏡 Casa: {house} 🇺🇸"
            f"{glossary_block}\n\n"
            f"⚠️ Busque \"{search_term}\" em casas brasileiras.\n"
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
