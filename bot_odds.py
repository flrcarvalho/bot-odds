import re
import math
import logging
from html import escape
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
    # ── MLB — Lançador ─────────────────────────────────────────────────
    "K":        {"under": "Menos de {n} Strikeouts",           "over": "Mais de {n} Strikeouts",           "desc": "Strikeouts do lançador (K = Strikeout no beisebol)"},
    "Ks":       {"under": "Menos de {n} Strikeouts",           "over": "Mais de {n} Strikeouts",           "desc": "Strikeouts do lançador"},
    "HA":       {"under": "Menos de {n} Hits Permitidos",      "over": "Mais de {n} Hits Permitidos",      "desc": "Hits Permitidos pelo lançador"},
    "H":        {"under": "Menos de {n} Hits Permitidos",      "over": "Mais de {n} Hits Permitidos",      "desc": "Hits Permitidos pelo lançador (H = Hits)"},
    "ER":       {"under": "Menos de {n} Earned Runs",          "over": "Mais de {n} Earned Runs",          "desc": "Runs sofridos pelo lançador (excluindo erros)"},
    "BB":       {"under": "Menos de {n} Walks Atribuídos",     "over": "Mais de {n} Walks Atribuídos",     "desc": "Walks (bases por bolas) concedidos pelo lançador"},
    "outs":     {"under": "Menos de {n} Outs (~{inn} inn)",    "over": "Mais de {n} Outs (~{inn} inn)",    "desc": "Outs registrados pelo lançador (3 outs = 1 inning)"},
    "IP":       {"under": "Menos de {n} Innings",              "over": "Mais de {n} Innings",              "desc": "Innings lançados (IP = Innings Pitched)"},
    # ── MLB — Rebatedor ────────────────────────────────────────────────
    "hits":     {"under": "Menos de {n} Hits",                 "over": "Mais de {n} Hits",                 "desc": "Hits do rebatedor"},
    "HR":       {"under": "Menos de {n} Home Runs",            "over": "Mais de {n} Home Runs",            "desc": "Home Runs do rebatedor"},
    "RBI":      {"under": "Menos de {n} Runs Batted In",       "over": "Mais de {n} Runs Batted In",       "desc": "Runs impulsionados pelo rebatedor (RBI)"},
    "runs":     {"under": "Menos de {n} Runs",                 "over": "Mais de {n} Runs",                 "desc": "Runs marcados pelo rebatedor"},
    "TB":       {"under": "Menos de {n} Total de Bases",       "over": "Mais de {n} Total de Bases",       "desc": "Total de Bases (1B=1, 2B=2, 3B=3, HR=4)"},
    "HRR":      {"under": "Menos de {n} Hits+Runs+RBIs",       "over": "Mais de {n} Hits+Runs+RBIs",       "desc": "Combinado: Hits + Runs + RBIs do rebatedor"},
    "SB":       {"under": "Menos de {n} Bases Roubadas",       "over": "Mais de {n} Bases Roubadas",       "desc": "Bases roubadas pelo rebatedor"},
    # ── NBA / WNBA — Player Props ──────────────────────────────────────
    "PRA":      {"under": "Menos de {n} Pts+Reb+Ast",          "over": "Mais de {n} Pts+Reb+Ast",          "desc": "Combinado: Pontos + Rebotes + Assistências"},
    "points":   {"under": "Menos de {n} Pontos",               "over": "Mais de {n} Pontos",               "desc": "Pontos marcados pelo jogador"},
    "pts":      {"under": "Menos de {n} Pontos",               "over": "Mais de {n} Pontos",               "desc": "Pontos marcados pelo jogador"},
    "assists":  {"under": "Menos de {n} Assistências",         "over": "Mais de {n} Assistências",         "desc": "Assistências do jogador"},
    "ast":      {"under": "Menos de {n} Assistências",         "over": "Mais de {n} Assistências",         "desc": "Assistências do jogador"},
    "rebounds": {"under": "Menos de {n} Rebotes",              "over": "Mais de {n} Rebotes",              "desc": "Rebotes do jogador"},
    "reb":      {"under": "Menos de {n} Rebotes",              "over": "Mais de {n} Rebotes",              "desc": "Rebotes do jogador"},
    "PR":       {"under": "Menos de {n} Pts+Reb",              "over": "Mais de {n} Pts+Reb",              "desc": "Combinado: Pontos + Rebotes"},
    "PA":       {"under": "Menos de {n} Pts+Ast",              "over": "Mais de {n} Pts+Ast",              "desc": "Combinado: Pontos + Assistências"},
    "RA":       {"under": "Menos de {n} Reb+Ast",              "over": "Mais de {n} Reb+Ast",              "desc": "Combinado: Rebotes + Assistências"},
    "3PM":      {"under": "Menos de {n} Cestas de 3 Pontos",   "over": "Mais de {n} Cestas de 3 Pontos",   "desc": "Cestas de 3 pontos convertidas"},
    "3s":       {"under": "Menos de {n} Cestas de 3 Pontos",   "over": "Mais de {n} Cestas de 3 Pontos",   "desc": "Cestas de 3 pontos convertidas"},
    "blocks":   {"under": "Menos de {n} Bloqueios",            "over": "Mais de {n} Bloqueios",            "desc": "Bloqueios (tocos) do jogador"},
    "blk":      {"under": "Menos de {n} Bloqueios",            "over": "Mais de {n} Bloqueios",            "desc": "Bloqueios (tocos) do jogador"},
    "steals":   {"under": "Menos de {n} Roubos de Bola",       "over": "Mais de {n} Roubos de Bola",       "desc": "Roubos de bola do jogador"},
    "stl":      {"under": "Menos de {n} Roubos de Bola",       "over": "Mais de {n} Roubos de Bola",       "desc": "Roubos de bola do jogador"},
    "mins":     {"under": "Menos de {n} Minutos",              "over": "Mais de {n} Minutos",              "desc": "Minutos em quadra"},
    "min":      {"under": "Menos de {n} Minutos",              "over": "Mais de {n} Minutos",              "desc": "Minutos em quadra"},
    "TO":       {"under": "Menos de {n} Turnovers",            "over": "Mais de {n} Turnovers",            "desc": "Turnovers (perdas de bola) do jogador"},
    # ── NFL ────────────────────────────────────────────────────────────
    "pass_yds": {"under": "Menos de {n} Jardas (Passe)",       "over": "Mais de {n} Jardas (Passe)",       "desc": "Jardas de passe do quarterback"},
    "rush_yds": {"under": "Menos de {n} Jardas (Corrida)",     "over": "Mais de {n} Jardas (Corrida)",     "desc": "Jardas de corrida do jogador"},
    "rec_yds":  {"under": "Menos de {n} Jardas (Recepção)",    "over": "Mais de {n} Jardas (Recepção)",    "desc": "Jardas de recepção do jogador"},
    "TD":       {"under": "Menos de {n} Touchdowns",           "over": "Mais de {n} Touchdowns",           "desc": "Touchdowns marcados/lançados"},
    "rec":      {"under": "Menos de {n} Recepções",            "over": "Mais de {n} Recepções",            "desc": "Recepções do wide receiver/tight end"},
    # ── NHL ────────────────────────────────────────────────────────────
    "shots":    {"under": "Menos de {n} Chutes a Gol",         "over": "Mais de {n} Chutes a Gol",         "desc": "Chutes a gol (shots on goal)"},
    "goals":    {"under": "Menos de {n} Gols",                 "over": "Mais de {n} Gols",                 "desc": "Gols marcados pelo jogador"},
    "saves":    {"under": "Menos de {n} Defesas",              "over": "Mais de {n} Defesas",              "desc": "Defesas do goleiro (saves)"},
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
    picks = []
    text_clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

    title_pattern = re.compile(
        r'^(\*{0,2}[A-Z]{2,5}[^:\n]*Pick[^:\n]*[-–:]\s*.+?)\*{0,2}$',
        re.IGNORECASE | re.MULTILINE,
    )
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
                    "title":  title_text,
                    "units":  m.group(1).strip(),
                    "market": m.group(2).strip(),
                    "odd_am": odd_am,
                    "odd_br": american_to_decimal(odd_am),
                    "house":  m.group(4).strip(),
                })
    else:
        m = pick_line_pattern.search(text_clean)
        if m:
            odd_am = int(m.group(3).replace(" ", ""))
            picks.append({
                "title":  None,
                "units":  m.group(1).strip(),
                "market": m.group(2).strip(),
                "odd_am": odd_am,
                "odd_br": american_to_decimal(odd_am),
                "house":  m.group(4).strip(),
            })

    return picks

# ============================================================
# INTERPRETA O MERCADO
# ============================================================
def interpret_market(market_raw: str) -> dict:
    """
    Extrai direção, linha e código do mercado.
    Suporta:
      - 'u4.5 K'                    → under 4.5 K
      - 'o5.5 HA'                   → over 5.5 HA
      - 'Brandon Sproat u4.5 K'     → under 4.5 K (jogador antes)
      - 'Brandon Sproat 4.5 K'      → sem direção explícita, extrai linha+código
      - 'LeBron James o25.5 points' → over 25.5 points
    """
    raw = market_raw.strip()

    # 1. Tenta encontrar [u/o][número] [código] em qualquer posição
    m = re.search(r'\b([uo])([\d.]+)\s+([A-Za-z_]+)\b', raw, re.IGNORECASE)
    if m:
        direction = m.group(1).lower()
        line      = m.group(2)
        code      = m.group(3)
    else:
        # 2. Fallback: número + código no final da string (sem direção)
        m = re.search(r'([\d.]+)\s+([A-Za-z_]+)\s*$', raw)
        if m:
            direction = None
            line      = m.group(1)
            code      = m.group(2)
        else:
            return {"direction": None, "line": None, "code": raw, "label": raw, "desc": None, "player": None}

    # Extrai nome do jogador (tudo antes do padrão encontrado)
    player_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+', raw)
    player = player_match.group(1) if player_match else None

    direction_word = "under" if direction == "u" else ("over" if direction == "o" else None)

    mkt = MARKET_TRANSLATIONS.get(code, {})

    if direction_word:
        label_tmpl = mkt.get(direction_word, f"{direction.upper()}{line} {code}")
    else:
        # Sem direção: mostra ambos os lados possíveis
        label_tmpl = mkt.get("over", f"{line} {code}").replace("Mais de", "±")

    desc_tmpl = mkt.get("desc", None)

    innings = str(round(float(line) / 3, 1)) if code == "outs" else ""
    label = label_tmpl.replace("{n}", line).replace("{inn}", innings)
    desc  = desc_tmpl if desc_tmpl else None

    return {
        "direction": direction,
        "line":      line,
        "code":      code,
        "label":     label,
        "desc":      desc,
        "player":    player,
    }

# ============================================================
# FORMATA A RESPOSTA (HTML)
# ============================================================
def format_response(picks: list[dict], original_text: str) -> str:
    if not picks:
        return None

    blocks = []

    for p in picks:
        odd_am  = p["odd_am"]
        odd_br  = p["odd_br"]
        odd_min = excel_round(odd_br * 0.96, 2)
        house   = HOUSE_NAMES.get(p["house"], p["house"])
        odd_str = f"+{odd_am}" if odd_am > 0 else str(odd_am)

        odd_br_str  = f"{odd_br:.2f}".replace(".", ",")
        odd_min_str = f"{odd_min:.2f}".replace(".", ",")
        units = re.sub(r'^\.(\d)', r'0.\1', p["units"])
        mkt = interpret_market(p["market"])

        sport_emoji = get_sport_emoji(p["title"])
        title_str  = escape(p["title"]) if p["title"] else "Pick detectado"
        title_line = f"{sport_emoji} <b>{title_str}</b>"

        # Linha de mercado: mostra jogador separado se detectado
        if mkt["player"]:
            player_line = f"👤 {escape(mkt['player'])}\n"
        else:
            player_line = ""

        dir_sym = ""
        if mkt["direction"] == "u":
            dir_sym = "🔵 UNDER"
        elif mkt["direction"] == "o":
            dir_sym = "🔴 OVER"

        market_line = f"{dir_sym} {escape(mkt['line'])} → {escape(mkt['label'])}" if mkt["direction"] else escape(mkt["label"])

        glossary_block = ""
        if mkt["desc"]:
            code_str = f"{(mkt['direction'] or '').upper()}{mkt['line']} {mkt['code']}"
            glossary_block = (
                f"\n📖 <b>O que significa:</b>\n"
                f"• <code>{escape(code_str)}</code> → {escape(mkt['desc'])}"
            )

        # Termo de busca: palavras-chave do label
        label_words = mkt["label"].split()
        search_term = escape(" ".join(label_words[2:]) if len(label_words) > 2 else mkt["code"])

        blocks.append(
            f"{title_line}\n"
            f"💰 <b>{escape(units)}</b>\n"
            f"{player_line}"
            f"🎟️ {market_line}\n"
            f"📉 Odd americana: <code>{odd_str}</code>\n"
            f"📈 Odd decimal: <b>{odd_br_str}</b>\n"
            f"🚫 Odd mínima: <b>{odd_min_str}</b>\n"
            f"🏡 Casa: {escape(house)} 🇺🇸"
            f"{glossary_block}\n\n"
            f"⚠️ Busque \"{search_term}\" em casas brasileiras."
        )

    original_block = f"\n\n<blockquote>{escape(original_text.strip())}</blockquote>"
    return "\n\n".join(blocks) + original_block

# ============================================================
# HANDLER
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text

        if "Odd americana:" in text or "Odds convertidas" in text:
            return

        chat_id = update.message.chat_id
        print(f"[MSG] chat_id={chat_id} tipo={update.message.chat.type}")
        print(f"[TEXTO] {repr(text[:200])}")

        picks = parse_picks(text)
        print(f"[PICKS] {picks}")

        response = format_response(picks, text)

        if response:
            await context.bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode="HTML",
            )
            await update.message.delete()
        else:
            print("[SEM RESPOSTA] nenhum pick encontrado")

    except Exception as e:
        print(f"[ERRO] {e}")

# ============================================================
# MAIN
# ============================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot rodando! Aguardando mensagens...")
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
