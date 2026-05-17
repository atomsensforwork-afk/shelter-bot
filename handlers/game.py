import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import database as db
import generator as gen
import messages as msg
from keyboards import reveal_keyboard
from config import REVEAL_TIMEOUT, VOTE_TIMEOUT

router = Router()

# Хранение задач таймеров {chat_id: asyncio.Task}
_reveal_timers: dict[int, asyncio.Task] = {}
_vote_timers: dict[int, asyncio.Task] = {}


async def start_game(message, bot: Bot, players: list):
    chat_id = message.chat.id
    player_names = [p["username"] for p in players]

    scenario = gen.generate_scenario(len(players))
    cards_map = gen.generate_cards_for_players(player_names, scenario)

    db.update_game(
        chat_id,
        state="reveal",
        scenario=scenario,
        survivors=scenario["survivors_needed"],
        round=1,
        revote=0
    )

    for p in players:
        cards = cards_map.get(p["username"], {})
        db.set_player_cards(chat_id, p["user_id"], cards)

    # Сценарий в группу
    await message.answer(
        msg.scenario_text(scenario, len(players)),
        parse_mode="HTML"
    )

    # Профессии всех
    players_with_cards = db.get_players(chat_id, active_only=True)
    await message.answer(
        msg.professions_reveal_text(players_with_cards),
        parse_mode="HTML"
    )

    # Карточки в личку
    failed = []
    for p in players_with_cards:
        cards = p["cards"]
        try:
            await bot.send_message(
                p["user_id"],
                msg.player_card_text(cards),
                parse_mode="HTML"
            )
        except Exception:
            failed.append(p["username"])

    if failed:
        await message.answer(
            f"⚠️ Не смог отправить карточки: <b>{', '.join(failed)}</b>\n"
            f"Они должны написать /start боту в личку!",
            parse_mode="HTML"
        )

    await start_reveal_round(message, bot)


async def start_reveal_round(message, bot: Bot):
    chat_id = message.chat.id
    game = db.get_game(chat_id)
    players = db.get_players(chat_id, active_only=True)

    await message.answer(
        msg.round_start_text(game["round"], players, game["survivors"]),
        parse_mode="HTML"
    )

    for p in players:
        try:
            await bot.send_message(
                p["user_id"],
                f"🔍 <b>Раунд {game['round']} — выбери карту для раскрытия:</b>",
                reply_markup=reveal_keyboard(p["cards"], p["revealed"]),
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Таймер на раскрытие
    if chat_id in _reveal_timers:
        _reveal_timers[chat_id].cancel()
    _reveal_timers[chat_id] = asyncio.create_task(
        _reveal_timeout(bot, chat_id, game["round"])
    )


async def _reveal_timeout(bot: Bot, chat_id: int, round_n: int):
    await asyncio.sleep(REVEAL_TIMEOUT)
    game = db.get_game(chat_id)
    if not game or game["state"] != "reveal" or game["round"] != round_n:
        return

    players = db.get_players(chat_id, active_only=True)
    round_key = f"round_{round_n}_revealed"

    for p in players:
        if round_key not in p["revealed"]:
            # Авто-раскрытие случайной нераскрытой карты
            unrevealed = [k for k in gen.CARD_KEYS if k not in p["revealed"] and k != "special"]
            if unrevealed:
                import random
                key = random.choice(unrevealed)
                db.reveal_card(chat_id, p["user_id"], key)
                db.reveal_card(chat_id, p["user_id"], round_key)
                value = p["cards"].get(key, "?")
                label = gen.CARD_LABELS.get(key, key)
                await bot.send_message(
                    chat_id,
                    msg.reveal_timeout_text(p["username"]) + f"\n{label}: <b>{value}</b>",
                    parse_mode="HTML"
                )

    db.update_game(chat_id, state="voting")
    from handlers.vote import start_voting
    await start_voting(bot, chat_id)


async def check_all_revealed(bot: Bot, chat_id: int):
    game = db.get_game(chat_id)
    if not game or game["state"] != "reveal":
        return

    players = db.get_players(chat_id, active_only=True)
    round_key = f"round_{game['round']}_revealed"
    if not all(round_key in p["revealed"] for p in players):
        return

    # Отменяем таймер
    if chat_id in _reveal_timers:
        _reveal_timers[chat_id].cancel()
        del _reveal_timers[chat_id]

    db.update_game(chat_id, state="voting")
    from handlers.vote import start_voting
    await start_voting(bot, chat_id)


async def check_game_over(bot: Bot, chat_id: int):
    game = db.get_game(chat_id)
    if not game:
        return
    remaining = db.get_players(chat_id, active_only=True)
    if len(remaining) <= game["survivors"]:
        await end_game(bot, chat_id, remaining)
        return True
    return False


async def end_game(bot: Bot, chat_id: int, survivors: list):
    db.update_game(chat_id, state="finished")

    await bot.send_message(
        chat_id,
        msg.game_over_text(survivors),
        parse_mode="HTML"
    )

    all_players = db.get_players(chat_id)
    await bot.send_message(
        chat_id,
        msg.all_cards_text(all_players),
        parse_mode="HTML"
    )

    db.delete_game(chat_id)


@router.callback_query(F.data.startswith("reveal:"))
async def cb_reveal(callback: CallbackQuery, bot: Bot):
    if callback.message.chat.type != "private":
        await callback.answer("Раскрывай карты в личке с ботом!", show_alert=True)
        return

    user_id = callback.from_user.id
    card_key = callback.data.split(":")[1]

    chat_id = db.get_player_game(user_id)
    if not chat_id:
        await callback.answer("Ты не участвуешь в активной игре.", show_alert=True)
        return

    game = db.get_game(chat_id)
    if not game or game["state"] not in ("reveal", "playing"):
        await callback.answer("Сейчас не фаза раскрытия.", show_alert=True)
        return

    player = db.get_player(chat_id, user_id)
    if not player:
        await callback.answer("Ты не в игре.", show_alert=True)
        return

    round_key = f"round_{game['round']}_revealed"
    already_revealed_this_round = round_key in player["revealed"]

    if card_key != "special" and already_revealed_this_round:
        await callback.answer("В этом раунде ты уже раскрыл карту!", show_alert=True)
        return

    if card_key in player["revealed"] and card_key != "special":
        await callback.answer("Эта карта уже открыта.", show_alert=True)
        return

    db.reveal_card(chat_id, user_id, card_key)
    if card_key != "special":
        db.reveal_card(chat_id, user_id, round_key)

    card_value = player["cards"].get(card_key, "?")
    label = gen.CARD_LABELS.get(card_key, card_key)

    player = db.get_player(chat_id, user_id)
    await callback.message.edit_reply_markup(
        reply_markup=reveal_keyboard(player["cards"], player["revealed"])
    )
    await callback.answer(f"✅ {label} раскрыта!")

    await bot.send_message(
        chat_id,
        msg.card_revealed_text(callback.from_user.first_name, label, card_value),
        parse_mode="HTML"
    )

    await check_all_revealed(bot, chat_id)


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
