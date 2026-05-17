import asyncio
import random
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import database as db
import messages as msg
from keyboards import vote_keyboard
from config import VOTE_TIMEOUT

router = Router()

_vote_timers: dict[int, asyncio.Task] = {}


async def start_voting(bot: Bot, chat_id: int):
    game = db.get_game(chat_id)
    players = db.get_players(chat_id, active_only=True)

    await bot.send_message(
        chat_id,
        msg.vote_start_text(game["round"]),
        parse_mode="HTML"
    )

    for p in players:
        try:
            await bot.send_message(
                p["user_id"],
                f"🗳 <b>Голосование — Раунд {game['round']}</b>\nКто покинет убежище?",
                reply_markup=vote_keyboard(players, p["user_id"]),
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Таймер
    if chat_id in _vote_timers:
        _vote_timers[chat_id].cancel()
    _vote_timers[chat_id] = asyncio.create_task(
        _vote_timeout(bot, chat_id, game["round"], game["revote"])
    )


async def _vote_timeout(bot: Bot, chat_id: int, round_n: int, revote_n: int):
    await asyncio.sleep(VOTE_TIMEOUT)
    game = db.get_game(chat_id)
    if not game or game["state"] != "voting":
        return
    if game["round"] != round_n or game["revote"] != revote_n:
        return

    # Кто не проголосовал — голос пропускается
    players = db.get_players(chat_id, active_only=True)
    votes = db.get_votes(chat_id, round_n, revote_n)
    voted_ids = {v["voter_id"] for v in votes}

    for p in players:
        if p["user_id"] not in voted_ids:
            await bot.send_message(
                chat_id,
                msg.vote_timeout_text(p["username"]),
                parse_mode="HTML"
            )

    await resolve_vote(bot, chat_id)


@router.callback_query(F.data.startswith("vote:"))
async def cb_vote(callback: CallbackQuery, bot: Bot):
    if callback.message.chat.type != "private":
        await callback.answer("Голосуй в личке с ботом!", show_alert=True)
        return

    voter_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])

    chat_id = db.get_player_game(voter_id)
    if not chat_id:
        await callback.answer("Ты не участвуешь в активной игре.", show_alert=True)
        return

    game = db.get_game(chat_id)
    if not game or game["state"] != "voting":
        await callback.answer("Сейчас не фаза голосования.", show_alert=True)
        return

    target = db.get_player(chat_id, target_id)
    if not target or target["eliminated"]:
        await callback.answer("Этот игрок уже выбыл.", show_alert=True)
        return

    db.cast_vote(chat_id, game["round"], game["revote"], voter_id, target_id)
    await callback.answer(f"✅ Голос за {target['username']} засчитан!")
    await callback.message.edit_text(
        msg.vote_cast_text(target["username"]),
        parse_mode="HTML"
    )

    await check_all_voted(bot, chat_id)


async def check_all_voted(bot: Bot, chat_id: int):
    game = db.get_game(chat_id)
    if not game:
        return
    players = db.get_players(chat_id, active_only=True)
    votes = db.get_votes(chat_id, game["round"], game["revote"])
    if len(votes) < len(players):
        return

    if chat_id in _vote_timers:
        _vote_timers[chat_id].cancel()
        del _vote_timers[chat_id]

    await resolve_vote(bot, chat_id)


async def resolve_vote(bot: Bot, chat_id: int):
    game = db.get_game(chat_id)
    players = db.get_players(chat_id, active_only=True)
    counts = db.count_votes(chat_id, game["round"], game["revote"])

    # Если никто не проголосовал — рандом
    if not counts:
        counts = {p["user_id"]: 0 for p in players}

    players_map = {p["user_id"]: p["username"] for p in players}

    # Показываем результаты
    await bot.send_message(
        chat_id,
        msg.vote_results_text(counts, players_map),
        parse_mode="HTML"
    )

    max_votes = max(counts.values(), default=0)
    losers = [uid for uid, cnt in counts.items() if cnt == max_votes]

    # Ничья — переголосование (один раз)
    if len(losers) > 1 and game["revote"] == 0:
        db.update_game(chat_id, revote=1)
        await bot.send_message(chat_id, msg.revote_text(), parse_mode="HTML")

        # Голосуем только между теми у кого ничья
        tied_players = [p for p in players if p["user_id"] in losers]
        for p in players:
            try:
                await bot.send_message(
                    p["user_id"],
                    f"⚖️ <b>Переголосование!</b>\nВыбери между: {', '.join(pp['username'] for pp in tied_players)}",
                    reply_markup=vote_keyboard(tied_players, p["user_id"]),
                    parse_mode="HTML"
                )
            except Exception:
                pass

        _vote_timers[chat_id] = asyncio.create_task(
            _vote_timeout(bot, chat_id, game["round"], 1)
        )
        return

    # Выбываем — при повторной ничье рандом
    eliminated_id = random.choice(losers)
    eliminated = db.get_player(chat_id, eliminated_id)
    db.eliminate_player(chat_id, eliminated_id)

    await bot.send_message(
        chat_id,
        msg.eliminated_text(eliminated["username"], eliminated["cards"]),
        parse_mode="HTML"
    )

    # Проверяем победу
    from handlers.game import check_game_over, start_reveal_round
    if await check_game_over(bot, chat_id):
        return

    # Следующий раунд
    new_round = game["round"] + 1
    db.update_game(chat_id, round=new_round, state="reveal", revote=0)

    remaining = db.get_players(chat_id, active_only=True)
    await bot.send_message(
        chat_id,
        f"➡️ <b>Раунд {new_round}</b>\n"
        f"<code>{'─' * 28}</code>\n"
        f"Осталось: <b>{len(remaining)}</b> | Нужно выжить: <b>{game['survivors']}</b>",
        parse_mode="HTML"
    )

    class FakeMessage:
        def __init__(self, bot, chat_id):
            self.bot = bot
            self.chat = type("C", (), {"id": chat_id, "type": "group"})()

        async def answer(self, text, **kwargs):
            await self.bot.send_message(self.chat.id, text, **kwargs)

    await start_reveal_round(FakeMessage(bot, chat_id), bot)
