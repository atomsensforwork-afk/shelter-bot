# ═══════════════════════════════════════════
#   УБЕЖИЩЕ — система сообщений и эстетика
# ═══════════════════════════════════════════

from generator import CARD_LABELS, CARD_KEYS


def divider(char="═", length=28):
    return char * length


def box(text: str, char="═") -> str:
    lines = text.split("\n")
    width = max(len(l) for l in lines) + 4
    top = "╔" + char * (width - 2) + "╗"
    bottom = "╚" + char * (width - 2) + "╝"
    mid = "\n".join("║ " + l.ljust(width - 4) + " ║" for l in lines)
    return f"{top}\n{mid}\n{bottom}"


# ── Лобби ─────────────────────────────────

def lobby_text(players: list[dict], host_name: str) -> str:
    count = len(players)
    names = "\n".join(f"  {'👑' if p['username'] == host_name else '👤'} {p['username']}" for p in players)
    return (
        f"🏠 <b>УБЕЖИЩЕ</b> — набор игроков\n"
        f"<code>{divider()}</code>\n"
        f"Хост: <b>{host_name}</b>\n\n"
        f"Участники ({count}):\n{names}\n\n"
        f"<code>{divider('─')}</code>\n"
        f"<i>Нажми «Присоединиться» чтобы войти.\n"
        f"Хост начинает игру когда все собрались.</i>"
    )


def rules_text() -> str:
    return (
        f"📋 <b>ПРАВИЛА УБЕЖИЩА</b>\n"
        f"<code>{divider()}</code>\n\n"
        f"Случилась катастрофа. Выжившие прячутся\n"
        f"в убежище, но мест на всех не хватает.\n\n"
        f"<b>Как играть:</b>\n"
        f"1️⃣ Каждый получает карточку персонажа\n"
        f"2️⃣ Каждый раунд — раскрой одну черту\n"
        f"3️⃣ Убеди всех что ты нужен убежищу\n"
        f"4️⃣ Голосование — кто выбывает\n"
        f"5️⃣ Повтор до нужного числа выживших\n\n"
        f"<code>{divider('─')}</code>\n"
        f"⭐ <b>Особое</b> можно раскрыть в любой момент\n"
        f"🗳 Голосование — анонимно в личке с ботом\n\n"
        f"⚠️ <b>ВАЖНО:</b> Все игроки должны написать\n"
        f"/start боту в личку, иначе не получат карточки!"
    )


def pm_reminder_text(bot_username: str) -> str:
    return (
        f"📩 <b>Перед стартом — важно!</b>\n"
        f"<code>{divider()}</code>\n\n"
        f"Каждый игрок должен написать боту в личку:\n\n"
        f"👉 @{bot_username} → /start\n\n"
        f"<i>Иначе бот не сможет отправить карточку.\n"
        f"Хост нажимает «Начать» когда все готовы.</i>"
    )


# ── Сценарий ──────────────────────────────

def scenario_text(scenario: dict, player_count: int) -> str:
    survivors = scenario["survivors_needed"]
    return (
        f"💥 <b>КАТАСТРОФА</b>\n"
        f"<code>{divider()}</code>\n"
        f"{scenario['disaster']}\n\n"
        f"⚠️ <b>УГРОЗА В УБЕЖИЩЕ</b>\n"
        f"<code>{divider('─')}</code>\n"
        f"{scenario['threat']}\n\n"
        f"🏠 <b>УБЕЖИЩЕ</b>\n"
        f"<code>{divider('─')}</code>\n"
        f"{scenario['shelter']}\n\n"
        f"<code>{divider()}</code>\n"
        f"👥 Игроков: <b>{player_count}</b>\n"
        f"🎯 Выживут: <b>{survivors}</b>\n"
        f"💀 Выбудет: <b>{player_count - survivors}</b>"
    )


def professions_reveal_text(players: list[dict]) -> str:
    lines = "\n".join(
        f"  💼 <b>{p['username']}</b>: {p['cards'].get('profession', '?')}"
        for p in players
    )
    return (
        f"📢 <b>ПРОФЕССИИ ИГРОКОВ</b>\n"
        f"<code>{divider()}</code>\n"
        f"{lines}"
    )


# ── Карточка игрока ────────────────────────

def player_card_text(cards: dict) -> str:
    lines = []
    for key in CARD_KEYS:
        if key in cards:
            lines.append(f"{CARD_LABELS[key]}: <b>{cards[key]}</b>")
    body = "\n".join(lines)
    return (
        f"🎭 <b>ТВОЯ КАРТОЧКА</b>\n"
        f"<code>{divider()}</code>\n"
        f"{body}\n"
        f"<code>{divider('─')}</code>\n"
        f"<i>Особое можно раскрыть в любой момент.\n"
        f"Остальные — по одной за раунд.</i>"
    )


# ── Раунд ─────────────────────────────────

def round_start_text(round_n: int, players: list[dict], survivors_needed: int) -> str:
    remaining = len(players)
    names = "  " + ", ".join(p["username"] for p in players)
    return (
        f"🔍 <b>РАУНД {round_n} — РАСКРЫТИЕ</b>\n"
        f"<code>{divider()}</code>\n"
        f"Выживших нужно: <b>{survivors_needed}</b>\n"
        f"Осталось игроков: <b>{remaining}</b>\n\n"
        f"В игре:\n{names}\n\n"
        f"<code>{divider('─')}</code>\n"
        f"<i>Каждый раскрывает одну карту в личке.\n"
        f"Особое — доступно всегда.</i>"
    )


def card_revealed_text(username: str, label: str, value: str) -> str:
    return (
        f"🔓 <b>{username}</b> раскрывает:\n"
        f"<code>{divider('─')}</code>\n"
        f"{label}: <b>{value}</b>"
    )


def reveal_timeout_text(username: str) -> str:
    return f"⏰ <b>{username}</b> не успел раскрыть карту — пропускает раунд."


def waiting_for_reveal_text(names: list[str]) -> str:
    joined = ", ".join(names)
    return f"⏳ Ждём раскрытия от: <b>{joined}</b>"


# ── Голосование ───────────────────────────

def vote_start_text(round_n: int) -> str:
    return (
        f"🗳 <b>ГОЛОСОВАНИЕ — РАУНД {round_n}</b>\n"
        f"<code>{divider()}</code>\n"
        f"Кто покинет убежище?\n\n"
        f"<i>Голосование анонимное — в личке с ботом.\n"
        f"У вас {90} секунд.</i>"
    )


def vote_cast_text(target_username: str) -> str:
    return (
        f"🗳 Ты проголосовал за <b>{target_username}</b>\n"
        f"<i>Ждём остальных...</i>"
    )


def vote_timeout_text(username: str) -> str:
    return f"⏰ <b>{username}</b> не проголосовал — голос не засчитан."


def revote_text() -> str:
    return (
        f"⚖️ <b>НИЧЬЯ!</b>\n"
        f"<code>{divider()}</code>\n"
        f"Голоса разделились поровну.\n"
        f"Проводим повторное голосование!"
    )


def vote_results_text(counts: dict, players_map: dict) -> str:
    lines = []
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    for uid, cnt in sorted_counts:
        name = players_map.get(uid, "?")
        bar = "▓" * cnt + "░" * (max(counts.values()) - cnt)
        lines.append(f"  {name}: {bar} {cnt}")
    return (
        f"📊 <b>РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ</b>\n"
        f"<code>{divider()}</code>\n"
        + "\n".join(lines)
    )


def eliminated_text(username: str, cards: dict) -> str:
    gender = cards.get("biology", "")
    his_her = "Её" if "енщин" in gender else "Его"
    lines = []
    for key in CARD_KEYS:
        if key in cards:
            lines.append(f"  {CARD_LABELS[key]}: {cards[key]}")
    body = "\n".join(lines)
    return (
        f"🚫 <b>{username} покидает убежище!</b>\n"
        f"<code>{divider()}</code>\n"
        f"{his_her} карточка:\n{body}"
    )


# ── Финал ─────────────────────────────────

def game_over_text(survivors: list[dict]) -> str:
    names = "\n".join(f"  🏆 <b>{p['username']}</b>" for p in survivors)
    return (
        f"🎉 <b>ИГРА ОКОНЧЕНА!</b>\n"
        f"<code>{divider()}</code>\n\n"
        f"В убежище выживают:\n{names}\n\n"
        f"<code>{divider('─')}</code>\n"
        f"<i>Поздравляем выживших!</i>"
    )


def all_cards_text(players: list[dict]) -> str:
    blocks = []
    for p in players:
        cards = p["cards"]
        gender = cards.get("biology", "")
        eliminated = "💀" if p["eliminated"] else "🏆"
        lines = [f"{eliminated} <b>{p['username']}</b>"]
        for key in CARD_KEYS:
            if key in cards:
                lines.append(f"  {CARD_LABELS[key]}: {cards[key]}")
        blocks.append("\n".join(lines))
    return (
        f"📋 <b>КАРТОЧКИ ВСЕХ ИГРОКОВ</b>\n"
        f"<code>{divider()}</code>\n\n"
        + f"\n{divider('─')}\n".join(blocks)
    )


# ── Системные ─────────────────────────────

def error_text(msg: str) -> str:
    return f"❌ <b>Ошибка:</b> {msg}"


def generating_text() -> str:
    return (
        f"⚙️ <b>Генерирую сценарий...</b>\n"
        f"<code>{divider('─')}</code>\n"
        f"<i>Это займёт пару секунд.</i>"
    )
