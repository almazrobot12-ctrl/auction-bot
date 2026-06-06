import time
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text

from config import ADMINS, REFERRAL_BONUS, DEFAULT_AUCTION_DURATION
from database import *
from keyboards import *

def register_handlers(dp: Dispatcher):

    class AuctionCreate(StatesGroup):
        title = State()
        description = State()
        start_price = State()
        min_step = State()
        duration = State()

    class BidState(StatesGroup):
        custom_amount = State()

    def format_time_left(end_time):
        left = end_time - int(time.time())
        if left <= 0:
            return "⏰ Tugadi"
        h = left // 3600
        m = (left % 3600) // 60
        s = left % 60
        if h > 0:
            return f"{h}s {m}d {s}son"
        elif m > 0:
            return f"{m}d {s}son"
        return f"{s}son"

    def auction_text(auction):
        aid, title, desc, img, start, current, min_step, winner, status, *rest = auction
        end_time = auction[11]
        winner_name = "Hech kim"
        if winner:
            u = get_user(winner)
