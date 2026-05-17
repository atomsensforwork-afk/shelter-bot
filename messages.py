from generator import CARD_LABELS, CARD_KEYS


def lobby_text(players: list, host_name: str) -> str:
    names = "\n".join(
        f"{'👑' if p['username'] == host_name else '👤'} {p['username']}"
        for p in players
    )
    return (
        f"🏠 <b>Убежище</b> — набор игроков\n\n"
        f"Участники ({len(players)}):\n{names}\n\n"
        f"<i>Хост начинает игру когда все собрались.</i>"
    )


def rules_text() -> str:
    return (
        f"📋 <b>Правила игры</b>\n\n"
        f"Случилась катастрофа. Мест в убежище на всех не хватает — "
        f"группа сама решает кто останется.\n\n"
        f"<b>Как играть:</b>\n"
        f"1. Каждый получает секретную карточку персонажа\n"
        f"2. Каждый раунд — раскрываешь одну свою черту\n"
        f"3. Убеди всех что ты нужен убежищу\n"
        f"4. Голосование — кто выбывает\n"
        f"5. Повтор пока не останется нужное число выживших\n\n"
        f"⭐ <b>Особое</b> можно раскрыть в любой момент\n"
        f"🗳 Голосование анонимное — в личке с ботом"
    )


def pm_reminder_text(bot_username: str) -> str:
    return (
        f"⚠️ <b>Важно перед стартом!</b>\n\n"
        f"Каждый игрок должен написать боту в личку:\n"
        f"👉 @{bot_username} → /start\n\n"
        f"<i>Без этого бот не сможет отправить карточку.</i>"
    )


def scenario_text(scenario: dict, player_count: int) -> str:
    survivors = scenario["survivors_needed"]
    return (
        f"💥 <b>Катастрофа</b>\n"
        f"{scenario['disaster']}\n\n"
        f"⚠️ <b>Угроза в убежище</b>\n"
        f"{scenario['threat']}\n\n"
        f"🏠 <b>Убежище</b>\n"
        f"{scenario['shelter']}\n\n"
        f"👥 Игроков: <b>{player_count}</b>  🎯 Выживут: <b>{survivors}</b>  💀 Выбудет: <b>{player_count - survivors}</b>"
    )


def professions_reveal_text(players: list) -> str:
    lines = "\n".join(
        f"💼 <b>{p['username']}</b>: {p['cards'].get('profession', '?')}"
        for p in players
    )
    return f"📢 <b>Профессии игроков:</b>\n\n{lines}"


def player_card_text(cards: dict) -> str:
    lines = []
    for key in CARD_KEYS:
        if key in cards:
            lines.append(f"{CARD_LABELS[key]}: <b>{cards[key]}</b>")
    return (
        f"🎭 <b>Твоя карточка</b>\n\n"
        + "\n".join(lines)
        + "\n\n<i>Особое можно раскрыть в любой момент. Остальные — по одной за раунд.</i>"
    )


def round_start_text(round_n: int, players: list, survivors_needed: int) -> str:
    remaining = len(players)
    names = ", ".join(p["username"] for p in players)
    return (
        f"🔍 <b>Раунд {round_n} — раскрытие</b>\n\n"
        f"В игре ({remaining}): {names}\n"
        f"Нужно выжить: <b>{survivors_needed}</b>\n\n"
        f"<i>Каждый раскрывает одну карту в личке боту.</i>"
    )


def card_revealed_text(username: str, label: str, value: str) -> str:
    return f"🔓 <b>{username}</b> → {label}: <b>{value}</b>"


def reveal_timeout_text(username: str) -> str:
    return f"⏰ <b>{username}</b> не успел — карта раскрыта автоматически."


def waiting_for_reveal_text(names: list) -> str:
    return f"⏳ Ждём: <b>{', '.join(names)}</b>"


def vote_start_text(round_n: int) -> str:
    return (
        f"🗳 <b>Голосование — раунд {round_n}</b>\n\n"
        f"Кто покинет убежище?\n"
        f"<i>Анонимно в личке. 90 секунд.</i>"
    )


def vote_cast_text(target_username: str) -> str:
    return f"✅ Голос за <b>{target_username}</b> засчитан. Ждём остальных..."


def vote_timeout_text(username: str) -> str:
    return f"⏰ <b>{username}</b> не проголосовал — пропуск."


def revote_text() -> str:
    return "⚖️ <b>Ничья!</b> Проводим повторное голосование между теми кто набрал поровну."


def vote_results_text(counts: dict, players_map: dict) -> str:
    lines = []
    for uid, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        name = players_map.get(uid, "?")
        lines.append(f"  {name}: {cnt} гол.")
    return "📊 <b>Результаты:</b>\n" + "\n".join(lines)


def eliminated_text(username: str, cards: dict) -> str:
    gender = cards.get("biology", "")
    his_her = "Её" if "енщин" in gender else "Его"
    lines = []
    for key in CARD_KEYS:
        if key in cards:
            lines.append(f"{CARD_LABELS[key]}: {cards[key]}")
    return (
        f"🚫 <b>{username} покидает убежище.</b>\n\n"
        f"{his_her} карточка:\n" + "\n".join(lines)
    )


def game_over_text(survivors: list) -> str:
    names = "\n".join(f"🏆 <b>{p['username']}</b>" for p in survivors)
    return f"🎉 <b>Игра окончена!</b>\n\nВ убежище выживают:\n{names}"


def all_cards_text(players: list) -> str:
    blocks = []
    for p in players:
        cards = p["cards"]
        icon = "💀" if p["eliminated"] else "🏆"
        lines = [f"{icon} <b>{p['username']}</b>"]
        for key in CARD_KEYS:
            if key in cards:
                lines.append(f"  {CARD_LABELS[key]}: {cards[key]}")
        blocks.append("\n".join(lines))
    return "📋 <b>Карточки всех игроков:</b>\n\n" + "\n\n".join(blocks)


def error_text(msg: str) -> str:
    return f"❌ {msg}"


def generating_text() -> str:
    return "⚙️ Генерирую сценарий и карточки..."
