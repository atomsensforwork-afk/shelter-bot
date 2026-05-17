from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from generator import CARD_KEYS, CARD_LABELS


def lobby_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚪 Присоединиться", callback_data="join")
    builder.button(text="🚀 Начать игру", callback_data="begin")
    builder.adjust(1)
    return builder.as_markup()


def reveal_keyboard(cards: dict, revealed: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key in CARD_KEYS:
        if key not in cards:
            continue
        label = CARD_LABELS[key]
        if key == "special":
            builder.button(text="⭐ Особое (всегда доступно)", callback_data="reveal:special")
        elif key in revealed:
            builder.button(text=f"✅ {label}", callback_data="noop")
        else:
            builder.button(text=label, callback_data=f"reveal:{key}")
    builder.adjust(2)
    return builder.as_markup()


def vote_keyboard(players: list, current_user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in players:
        if p["user_id"] == current_user_id:
            continue
        builder.button(
            text=f"☠️ {p['username']}",
            callback_data=f"vote:{p['user_id']}"
        )
    builder.adjust(1)
    return builder.as_markup()
