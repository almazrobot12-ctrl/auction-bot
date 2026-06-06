from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🏆 Auksionlar"), KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="👥 Referral"), KeyboardButton(text="💰 Tanga olish")],
        [KeyboardButton(text="📊 Reyting"), KeyboardButton(text="ℹ️ Yordam")]
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Auksion yaratish"), KeyboardButton(text="📋 Barcha auksionlar")],
        [KeyboardButton(text="🔙 Asosiy menyu")]
    ], resize_keyboard=True)

def auction_keyboard(auction_id, current_price, min_step):
    step1 = min_step
    step2 = min_step * 5
    step3 = min_step * 10
    step4 = min_step * 20
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"💵 +{step1}₱ ({current_price + step1:.1f}₱)", callback_data=f"bid:{auction_id}:{current_price + step1:.1f}"),
            InlineKeyboardButton(text=f"💵 +{step2}₱ ({current_price + step2:.1f}₱)", callback_data=f"bid:{auction_id}:{current_price + step2:.1f}"),
        ],
        [
            InlineKeyboardButton(text=f"💵 +{step3}₱ ({current_price + step3:.1f}₱)", callback_data=f"bid:{auction_id}:{current_price + step3:.1f}"),
            InlineKeyboardButton(text=f"💵 +{step4}₱ ({current_price + step4:.1f}₱)", callback_data=f"bid:{auction_id}:{current_price + step4:.1f}"),
        ],
        [InlineKeyboardButton(text="✍️ O'z summa kiritish", callback_data=f"custom_bid:{auction_id}")],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"refresh:{auction_id}"),
            InlineKeyboardButton(text="📊 Tarix", callback_data=f"history:{auction_id}")
        ]
    ])

def confirm_bid_keyboard(auction_id, amount):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ Ha, {amount}₱ qo'yaman", callback_data=f"confirm_bid:{auction_id}:{amount}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data=f"cancel_bid:{auction_id}")
        ]
    ])