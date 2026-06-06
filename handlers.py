import time
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMINS, REFERRAL_BONUS, DEFAULT_AUCTION_DURATION
from database import *
from keyboards import *

router = Router()

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
        winner_name = u[3] if u else f"ID:{winner}"
    status_emoji = "🟢" if status == 'active' else "🔴"
    return f"""{status_emoji} <b>{title}</b>

📝 {desc}

💰 Boshlang'ich narx: <b>{start}₱</b>
🔥 Joriy narx: <b>{current}₱</b>
📈 Minimal qadam: <b>{min_step}₱</b>
👑 Hozirgi g'olib: <b>{winner_name}</b>
⏰ Qoldi: <b>{format_time_left(end_time)}</b>

🎯 Stavka qo'yish uchun tugma bosing!""".strip()

async def finish_auction_task(bot, auction_id, chat_id):
    auction = get_auction(auction_id)
    if not auction or auction[8] != 'active':
        return
    winner_id = finish_auction(auction_id)
    if winner_id:
        winner = get_user(winner_id)
        winner_name = winner[3] if winner else "Noma'lum"
        final_price = auction[5]
        await bot.send_message(chat_id, f"🎉 <b>AUKSION TUGADI!</b>\n\n🏆 G'olib: <b>{winner_name}</b>\n💰 Narx: <b>{final_price}₱</b>\n🎁 Lot: <b>{auction[1]}</b>", parse_mode="HTML")
        await bot.send_message(winner_id, f"🎊 Tabriklaymiz! <b>{auction[1]}</b> lotini <b>{final_price}₱</b>ga yutib oldingiz!", parse_mode="HTML")
    else:
        await bot.send_message(chat_id, f"😔 <b>{auction[1]}</b> auksionida hech kim ishtirok etmadi.", parse_mode="HTML")

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    user_id = msg.from_user.id
    username = msg.from_user.username or ""
    full_name = msg.from_user.full_name or "Foydalanuvchi"
    args = msg.text.split()
    ref_code = args[1] if len(args) > 1 else None
    existing = get_user(user_id)
    if not existing:
        referrer = None
        if ref_code:
            referrer_user = get_user_by_ref(ref_code)
            if referrer_user and referrer_user[0] != user_id:
                referrer = referrer_user[0]
        my_ref = create_user(user_id, username, full_name, referrer)
        if referrer:
            add_referral(referrer, user_id)
            update_coins(referrer, REFERRAL_BONUS, "referral", f"Referral: {full_name}")
            await msg.bot.send_message(referrer, f"🎉 Yangi referral! <b>{full_name}</b> qo'shildi! +{REFERRAL_BONUS} tanga!", parse_mode="HTML")
        await msg.answer(f"👋 Xush kelibsiz, <b>{full_name}</b>!\n\n🎁 <b>5 tanga</b> sovg'a!\n📌 Referral kodingiz: <code>{my_ref}</code>", reply_markup=main_menu(), parse_mode="HTML")
    else:
        await msg.answer(f"👋 Qaytib keldingiz, <b>{full_name}</b>!", reply_markup=main_menu(), parse_mode="HTML")

@router.message(F.text == "👤 Profil")
async def profile(msg: Message):
    user = get_user(msg.from_user.id)
    if not user:
        await msg.answer("Iltimos /start bosing")
        return
    uid, username, name, coins, ref_code, ref_by, wins, bids, joined, banned = user[:10]
    ref_count = get_referral_count(uid)
    await msg.answer(f"👤 <b>Profil</b>\n\n🆔 ID: <code>{uid}</code>\n📛 Ism: <b>{name}</b>\n💰 Tangalar: <b>{coins}₱</b>\n🏆 G'alabalar: <b>{wins}</b>\n🎯 Stavkalar: <b>{bids}</b>\n👥 Referrallar: <b>{ref_count}</b>\n\n🔗 Havola:\n<code>https://t.me/my_auksionbot?start={ref_code}</code>", parse_mode="HTML")

@router.message(F.text == "🏆 Auksionlar")
async def show_auctions(msg: Message):
    auctions = get_active_auctions()
    if not auctions:
        await msg.answer("😔 Hozir faol auksionlar yo'q.")
        return
    await msg.answer(f"🏆 <b>Faol auksionlar: {len(auctions)} ta</b>", parse_mode="HTML")
    for auction in auctions:
        aid = auction[0]
        text = auction_text(auction)
        kb = auction_keyboard(aid, auction[5], auction[6])
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("bid:"))
async def place_bid_callback(cb: CallbackQuery):
    _, auction_id, amount = cb.data.split(":")
    auction_id = int(auction_id)
    amount = float(amount)
    user = get_user(cb.from_user.id)
    if not user:
        await cb.answer("Iltimos /start bosing!", show_alert=True)
        return
    auction = get_auction(auction_id)
    if not auction or auction[8] != 'active':
        await cb.answer("❌ Bu auksion tugagan!", show_alert=True)
        return
    if auction[7] == cb.from_user.id:
        await cb.answer("⚠️ Siz allaqachon yuqoridasiz!", show_alert=True)
        return
    if amount <= auction[5]:
        await cb.answer(f"❌ Minimal stavka: {auction[5]+auction[6]}₱", show_alert=True)
        return
    kb = confirm_bid_keyboard(auction_id, amount)
    await cb.message.answer(f"⚠️ Tasdiqlash\n\n🎯 <b>{auction[1]}</b>\n💰 Stavkangiz: <b>{amount}₱</b>\n\nDavom etasizmi?", reply_markup=kb, parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("custom_bid:"))
async def custom_bid(cb: CallbackQuery, state: FSMContext):
    auction_id = int(cb.data.split(":")[1])
    await state.set_state(BidState.custom_amount)
    await state.update_data(auction_id=auction_id)
    auction = get_auction(auction_id)
    await cb.message.answer(f"✍️ Stavka kiriting (₱)\nMinimal: <b>{auction[5] + auction[6]}₱</b>", parse_mode="HTML")
    await cb.answer()

@router.message(BidState.custom_amount)
async def process_custom_bid(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text)
    except:
        await msg.answer("❌ Raqam kiriting!")
        return
    data = await state.get_data()
    auction_id = data['auction_id']
    auction = get_auction(auction_id)
    if not auction or auction[8] != 'active':
        await msg.answer("❌ Auksion tugagan!")
        await state.clear()
        return
    if amount < auction[5] + auction[6]:
        await msg.answer(f"❌ Minimal: {auction[5] + auction[6]}₱")
        return
    await state.clear()
    kb = confirm_bid_keyboard(auction_id, amount)
    await msg.answer(f"⚠️ Tasdiqlash\n\n💰 Stavkangiz: <b>{amount}₱</b>\n\nDavom etasizmi?", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("confirm_bid:"))
async def confirm_bid(cb: CallbackQuery, bot: Bot):
    _, auction_id, amount = cb.data.split(":")
    auction_id = int(auction_id)
    amount = float(amount)
    auction = get_auction(auction_id)
    if not auction or auction[8] != 'active':
        await cb.answer("❌ Auksion tugagan!", show_alert=True)
        return
    prev_winner = auction[7]
    place_bid(auction_id, cb.from_user.id, amount)
    if prev_winner and prev_winner != cb.from_user.id:
        try:
            await bot.send_message(prev_winner, f"⚠️ <b>{auction[1]}</b> da kimdir ustingizdan oshdi!\nYangi narx: <b>{amount}₱</b>", parse_mode="HTML")
        except:
            pass
    await cb.message.edit_text(f"✅ Stavka qabul qilindi!\n\n💰 <b>{amount}₱</b>\n\n🤞 Omad!", parse_mode="HTML")
    await cb.answer(f"✅ {amount}₱ qo'yildi!", show_alert=True)

@router.callback_query(F.data.startswith("cancel_bid:"))
async def cancel_bid(cb: CallbackQuery):
    await cb.message.edit_text("❌ Bekor qilindi.")
    await cb.answer()

@router.callback_query(F.data.startswith("refresh:"))
async def refresh_auction(cb: CallbackQuery):
    auction_id = int(cb.data.split(":")[1])
    auction = get_auction(auction_id)
    if not auction:
        await cb.answer("Topilmadi!", show_alert=True)
        return
    try:
        await cb.message.edit_text(auction_text(auction), reply_markup=auction_keyboard(auction_id, auction[5], auction[6]), parse_mode="HTML")
    except:
        pass
    await cb.answer("✅ Yangilandi!")

@router.callback_query(F.data.startswith("history:"))
async def bid_history(cb: CallbackQuery):
    auction_id = int(cb.data.split(":")[1])
    bids = get_auction_bids(auction_id, 10)
    if not bids:
        await cb.answer("Hali stavka yo'q!", show_alert=True)
        return
    text = "📊 <b>Oxirgi stavkalar:</b>\n\n"
    for i, (amount, bid_time, name) in enumerate(bids, 1):
        t = time.strftime("%H:%M:%S", time.localtime(bid_time))
        text += f"{i}. <b>{name}</b> — {amount}₱ ({t})\n"
    await cb.message.answer(text, parse_mode="HTML")
    await cb.answer()

@router.message(F.text == "👥 Referral")
async def referral_info(msg: Message):
    user = get_user(msg.from_user.id)
    if not user:
        return
    ref_count = get_referral_count(msg.from_user.id)
    await msg.answer(f"👥 <b>Referral</b>\n\n🔗 Havolangiz:\n<code>https://t.me/my_auksionbot?start={user[4]}</code>\n\n👥 Taklif qilinganlar: <b>{ref_count}</b>\n💰 Daromad: <b>{ref_count * REFERRAL_BONUS}₱</b>\n\nHar bir do'st uchun <b>{REFERRAL_BONUS} tanga</b>!", parse_mode="HTML")

@router.message(F.text == "💰 Tanga olish")
async def buy_coins(msg: Message):
    await msg.answer("💰 <b>Tanga sotib olish</b>\n\n📦 Paketlar:\n• 50 tanga — 5₱\n• 150 tanga — 12₱\n• 500 tanga — 35₱\n• 1000 tanga — 60₱\n\n📩 Admin: @admin_username", parse_mode="HTML")

@router.message(F.text == "📊 Reyting")
async def leaderboard(msg: Message):
    users = get_top_users(10)
    text = "🏆 <b>TOP 10</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, name, coins, wins) in enumerate(users, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} <b>{name}</b> — {coins}₱ | {wins} g'alaba\n"
    await msg.answer(text, parse_mode="HTML")

@router.message(F.text == "ℹ️ Yordam")
async def help_cmd(msg: Message):
    await msg.answer("ℹ️ <b>Qo'llanma</b>\n\n🏆 Eng yuqori stavka g'olib bo'ladi\n💰 Referral orqali tanga ishlang\n⚠️ Savollar: @admin_username", parse_mode="HTML")

@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id not in ADMINS:
        return
    await msg.answer("👑 Admin panel", reply_markup=admin_menu())

@router.message(F.text == "➕ Auksion yaratish")
async def start_create_auction(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMINS:
        return
    await state.set_state(AuctionCreate.title)
    await msg.answer("📝 Auksion nomini kiriting:")

@router.message(AuctionCreate.title)
async def auction_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await state.set_state(AuctionCreate.description)
    await msg.answer("📋 Tavsif kiriting:")

@router.message(AuctionCreate.description)
async def auction_desc(msg: Message, state: FSMContext):
    await state.update_data(description=msg.text)
    await state.set_state(AuctionCreate.start_price)
    await msg.answer("💰 Boshlang'ich narx (₱):")

@router.message(AuctionCreate.start_price)
async def auction_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text)
    except:
        await msg.answer("❌ Raqam kiriting!")
        return
    await state.update_data(start_price=price)
    await state.set_state(AuctionCreate.min_step)
    await msg.answer("📈 Minimal qadam (₱):")

@router.message(AuctionCreate.min_step)
async def auction_step(msg: Message, state: FSMContext):
    try:
        step = float(msg.text)
    except:
        await msg.answer("❌ Raqam kiriting!")
        return
    await state.update_data(min_step=step)
    await state.set_state(AuctionCreate.duration)
    await msg.answer("⏱ Davomiylik (daqiqada):")

@router.message(AuctionCreate.duration)
async def auction_duration(msg: Message, state: FSMContext, bot: Bot):
    try:
        minutes = int(msg.text)
    except:
        await msg.answer("❌ Raqam kiriting!")
        return
    data = await state.get_data()
    await state.clear()
    auction_id = create_auction(data['title'], data['description'], data['start_price'], data['min_step'], minutes * 60, msg.from_user.id, msg.chat.id)
    auction = get_auction(auction_id)
    text = auction_text(auction)
    kb = auction_keyboard(auction_id, data['start_price'], data['min_step'])
    await msg.answer(f"✅ Auksion yaratildi!\n\n{text}", reply_markup=kb, parse_mode="HTML")
    asyncio.get_event_loop().call_later(minutes * 60, lambda: asyncio.create_task(finish_auction_task(bot, auction_id, msg.chat.id)))

@router.message(F.text == "📋 Barcha auksionlar")
async def all_auctions(msg: Message):
    if msg.from_user.id not in ADMINS:
        return
    auctions = get_active_auctions()
    if not auctions:
        await msg.answer("Faol auksionlar yo'q.")
        return
    text = f"📋 Faol: {len(auctions)}\n\n"
    for a in auctions:
        text += f"🆔 {a[0]} | {a[1]} | {a[5]}₱ | {format_time_left(a[11])}\n"
    await msg.answer(text)

@router.message(F.text == "🔙 Asosiy menyu")
async def back_main(msg: Message):
    await msg.answer("🏠 Asosiy menyu", reply_markup=main_menu())