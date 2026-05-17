from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import database as db
import messages as msg
from keyboards import lobby_keyboard
from config import MIN_PLAYERS, MAX_PLAYERS

router = Router()


@router.message(Command("new", "start"))
async def cmd_new(message: Message, bot: Bot):
    if message.chat.type == "private":
        await message.answer(
            "👋 Привет! Добавь меня в групповой чат и напиши /new чтобы начать игру."
        )
        return

    game = db.get_game(message.chat.id)
    if game:
        await message.answer("⚠️ Игра уже создана. /stop чтобы завершить.")
        return

    db.create_game(message.chat.id, message.from_user.id)
    db.add_player(message.chat.id, message.from_user.id, message.from_user.first_name)

    me = await bot.get_me()
    players = db.get_players(message.chat.id)

    # Правила
    await message.answer(msg.rules_text(), parse_mode="HTML")

    # Напоминание написать в личку
    await message.answer(msg.pm_reminder_text(me.username), parse_mode="HTML")

    # Лобби
    await message.answer(
        msg.lobby_text(players, message.from_user.first_name),
        reply_markup=lobby_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    if message.chat.type == "private":
        return
    game = db.get_game(message.chat.id)
    if not game:
        await message.answer("Нет активной игры.")
        return
    if game["host_id"] != message.from_user.id:
        await message.answer("⛔ Только хост может остановить игру.")
        return
    db.delete_game(message.chat.id)
    await message.answer("🛑 Игра завершена. /new чтобы начать новую.")


@router.message(Command("status"))
async def cmd_status(message: Message):
    if message.chat.type == "private":
        return
    game = db.get_game(message.chat.id)
    if not game:
        await message.answer("Нет активной игры.")
        return
    players = db.get_players(message.chat.id, active_only=True)
    round_key = f"round_{game['round']}_revealed"
    waiting = [p["username"] for p in players if round_key not in p["revealed"]]
    if waiting:
        await message.answer(msg.waiting_for_reveal_text(waiting), parse_mode="HTML")
    else:
        await message.answer("✅ Все раскрыли карты в этом раунде.")


@router.message(Command("kick"))
async def cmd_kick(message: Message, bot: Bot):
    """Хост может кикнуть зависшего игрока: /kick @username"""
    if message.chat.type == "private":
        return
    game = db.get_game(message.chat.id)
    if not game:
        return
    if game["host_id"] != message.from_user.id:
        await message.answer("⛔ Только хост может кикать игроков.")
        return
    if not message.entities:
        await message.answer("Использование: /kick @username")
        return

    # Ищем mention в тексте
    mention = None
    for ent in message.entities:
        if ent.type == "mention":
            mention = message.text[ent.offset + 1: ent.offset + ent.length]
    if not mention:
        await message.answer("Укажи @username игрока.")
        return

    players = db.get_players(message.chat.id, active_only=True)
    target = next((p for p in players if p["username"].lower() == mention.lower()), None)
    if not target:
        await message.answer(f"Игрок @{mention} не найден или уже выбыл.")
        return

    db.eliminate_player(message.chat.id, target["user_id"])
    await message.answer(f"👢 <b>{target['username']}</b> кикнут хостом.", parse_mode="HTML")

    from handlers.game import check_game_over
    await check_game_over(bot, message.chat.id)


@router.callback_query(F.data == "join")
async def cb_join(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    game = db.get_game(chat_id)

    if not game:
        await callback.answer("Игра не найдена.", show_alert=True)
        return
    if game["state"] != "lobby":
        await callback.answer("Игра уже началась!", show_alert=True)
        return

    players = db.get_players(chat_id)
    if len(players) >= MAX_PLAYERS:
        await callback.answer(f"Максимум {MAX_PLAYERS} игроков.", show_alert=True)
        return

    added = db.add_player(chat_id, callback.from_user.id, callback.from_user.first_name)
    if not added:
        await callback.answer("Ты уже в игре!", show_alert=True)
        return

    await callback.answer("✅ Ты в игре!")
    players = db.get_players(chat_id)
    host = next(p for p in players if p["user_id"] == game["host_id"])
    await callback.message.edit_text(
        msg.lobby_text(players, host["username"]),
        reply_markup=lobby_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "begin")
async def cb_begin(callback: CallbackQuery, bot: Bot):
    from handlers.game import start_game

    chat_id = callback.message.chat.id
    game = db.get_game(chat_id)

    if not game:
        await callback.answer("Игра не найдена.", show_alert=True)
        return
    if game["host_id"] != callback.from_user.id:
        await callback.answer("Только хост может начать игру.", show_alert=True)
        return
    if game["state"] != "lobby":
        await callback.answer("Игра уже идёт!", show_alert=True)
        return

    players = db.get_players(chat_id)
    if len(players) < MIN_PLAYERS:
        await callback.answer(
            f"Нужно минимум {MIN_PLAYERS} игрока. Сейчас: {len(players)}.",
            show_alert=True
        )
        return

    await callback.answer()
    await callback.message.edit_text(msg.generating_text(), parse_mode="HTML")
    await start_game(callback.message, bot, players)
