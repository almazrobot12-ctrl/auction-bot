import sqlite3
import time
from config import DB_FILE, START_COINS

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        coins INTEGER DEFAULT 0,
        referral_code TEXT UNIQUE,
        referred_by INTEGER,
        total_wins INTEGER DEFAULT 0,
        total_bids INTEGER DEFAULT 0,
        joined_at INTEGER,
        is_banned INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        image_url TEXT,
        start_price REAL,
        current_price REAL,
        min_step REAL DEFAULT 1,
        current_winner INTEGER,
        status TEXT DEFAULT 'active',
        created_by INTEGER,
        start_time INTEGER,
        end_time INTEGER,
        message_id INTEGER,
        chat_id INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        auction_id INTEGER,
        user_id INTEGER,
        amount REAL,
        bid_time INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        created_at INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        type TEXT,
        description TEXT,
        created_at INTEGER
    )''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username, full_name, referred_by=None):
    import random, string
    ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, coins, referral_code, referred_by, joined_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (user_id, username, full_name, START_COINS, ref_code, referred_by, int(time.time())))
    conn.commit()
    conn.close()
    return ref_code

def update_coins(user_id, amount, tx_type, description):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
    c.execute("INSERT INTO transactions (user_id, amount, type, description, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, amount, tx_type, description, int(time.time())))
    conn.commit()
    conn.close()

def get_user_by_ref(ref_code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE referral_code=?", (ref_code,))
    user = c.fetchone()
    conn.close()
    return user

def add_referral(referrer_id, referred_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id, created_at) VALUES (?, ?, ?)",
              (referrer_id, referred_id, int(time.time())))
    conn.commit()
    conn.close()

def get_referral_count(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_top_users(limit=10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, coins, total_wins FROM users ORDER BY coins DESC LIMIT ?", (limit,))
    users = c.fetchall()
    conn.close()
    return users

def create_auction(title, description, start_price, min_step, duration, created_by, chat_id, image_url=None):
    now = int(time.time())
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO auctions (title, description, image_url, start_price, current_price, min_step, created_by, status, start_time, end_time, chat_id) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)",
              (title, description, image_url, start_price, start_price, min_step, created_by, now, now + duration, chat_id))
    auction_id = c.lastrowid
    conn.commit()
    conn.close()
    return auction_id

def get_auction(auction_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM auctions WHERE id=?", (auction_id,))
    auction = c.fetchone()
    conn.close()
    return auction

def get_active_auctions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM auctions WHERE status='active' ORDER BY end_time ASC")
    auctions = c.fetchall()
    conn.close()
    return auctions

def place_bid(auction_id, user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE auctions SET current_price=?, current_winner=? WHERE id=? AND status='active'",
              (amount, user_id, auction_id))
    c.execute("INSERT INTO bids (auction_id, user_id, amount, bid_time) VALUES (?, ?, ?, ?)",
              (auction_id, user_id, amount, int(time.time())))
    c.execute("UPDATE users SET total_bids = total_bids + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def finish_auction(auction_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE auctions SET status='finished' WHERE id=?", (auction_id,))
    c.execute("SELECT current_winner FROM auctions WHERE id=?", (auction_id,))
    winner = c.fetchone()
    if winner and winner[0]:
        c.execute("UPDATE users SET total_wins = total_wins + 1 WHERE user_id=?", (winner[0],))
    conn.commit()
    conn.close()
    return winner[0] if winner else None

def get_auction_bids(auction_id, limit=5):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT b.amount, b.bid_time, u.full_name FROM bids b JOIN users u ON b.user_id=u.user_id WHERE b.auction_id=? ORDER BY b.bid_time DESC LIMIT ?",
              (auction_id, limit))
    bids = c.fetchall()
    conn.close()
    return bids

def update_auction_message(auction_id, message_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE auctions SET message_id=? WHERE id=?", (message_id, auction_id))
    conn.commit()
    conn.close()