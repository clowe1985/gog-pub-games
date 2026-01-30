# football_card.py — Grumpy's Football Card

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from datetime import datetime, timezone
import random
import asyncio
import os
import json

# ---------------- CONFIG ----------------
CARD_PRICE_USDC = 1 * 10**6   # 1 USDC (6 decimals)
MAX_TEAMS = 32
MAX_TEAMS_PER_USER = 5
HOUSE_CUT = 0.10
CARD_POOL_WALLET = "0x94a50E18D16CD14A2e3f8139358Deb341A3B564e"

# ---------------- STATE ----------------
CARD_ACTIVE = False
CARD_TEAMS = []
CARD_ENTRIES = {}    # team -> user data
CARD_USERS = {}      # user_id -> count
CARD_MESSAGE_ID = None
CARD_POOL = 0
CARD_STATE_FILE = "/root/gog_bot/football_card.json"
CARD_POOL_PK = "2693abc999283c7372d0c74faf664eb22d3aff2a2eda8bc0bf5e3a66cd0d9f3f"

# Global variables that will be set by setup_football_card
CHAT_ID = None
speak_george = None
send_usdc = None
WALLETS = None
USDC = None

# ---------------- TEAMS ----------------
ALL_TEAMS = [
    "Arsenal", "Aston Villa", "Birmingham", "Brentford", "Brighton",
    "Burnley", "Chelsea", "Crystal Palace", "Everton", "Fulham",
    "Leeds", "Leicester", "Liverpool", "Luton", "Man City",
    "Man United", "Newcastle", "Norwich", "Nottingham Forest",
    "Sheffield United", "Southampton", "Tottenham", "West Ham",
    "Wolves", "Blackburn", "Bolton", "Derby", "Middlesbrough",
    "QPR", "Reading", "Stoke", "Sunderland", "Watford"
]

# ---------------- HELPERS ----------------
def reset_card():
    global CARD_ACTIVE, CARD_TEAMS, CARD_ENTRIES
    global CARD_USERS, CARD_MESSAGE_ID, CARD_POOL

    CARD_ACTIVE = False
    CARD_TEAMS = []
    CARD_ENTRIES = {}
    CARD_USERS = {}
    CARD_MESSAGE_ID = None
    CARD_POOL = 0

    save_card_state()

def render_card():
    lines = ["🍺 Grumpy's Football Card 🍺", ""]
    for team in CARD_TEAMS:
        if team in CARD_ENTRIES:
            user = CARD_ENTRIES[team]
            name = user.get("username") or user.get("name", "Legend")
            # Escape special Markdown characters in name
            escaped_name = (name
                .replace("_", "\\_")
                .replace("*", "\\*")
                .replace("[", "\\[")
                .replace("`", "\\`")
                .replace(">", "\\>")
                .replace("#", "\\#")
                .replace("+", "\\+")
                .replace("-", "\\-")
                .replace("=", "\\=")
                .replace("|", "\\|")
                .replace("{", "\\{")
                .replace("}", "\\}")
                .replace(".", "\\.")
                .replace("!", "\\!")
            )
            lines.append(f"❌ {team} — @{escaped_name}")
        else:
            lines.append(f"⬜️ {team}")
    lines.append("")
    lines.append("💰 $1 USDC per team | Max 5 per person")
    lines.append("🏆 Winner takes 90% | House keeps 10%")
    return "\n".join(lines)

def setup_football_card(globals_dict):
    global CHAT_ID, speak_george, send_usdc, WALLETS, USDC, CARD_POOL_PK
    CHAT_ID = globals_dict["CHAT_ID"]
    speak_george = globals_dict["speak_george"]
    send_usdc = globals_dict["send_usdc"]
    WALLETS = globals_dict["WALLETS"]
    USDC = globals_dict["USDC"]
    CARD_POOL_PK = globals_dict["CARD_POOL_PK"]

def save_card_state():
    print(">>> SAVING FOOTBALL CARD STATE - TEAMS FILLED: {}/{}".format(len(CARD_ENTRIES), MAX_TEAMS))
    state = {
        "active": CARD_ACTIVE,
        "teams": CARD_TEAMS,
        "entries": {team: {
            "id": data["id"],
            "username": data.get("username"),
            "name": data.get("name", "Legend")
        } for team, data in CARD_ENTRIES.items()},
        "users": CARD_USERS,
        "message_id": CARD_MESSAGE_ID,
        "pool": CARD_POOL
    }
    try:
        with open(CARD_STATE_FILE, "w") as f:
            json.dump(state, f)
        print(">>> Football card state saved")
    except Exception as e:
        print(f">>> Failed to save football card state: {e}")

def load_card_state():
    print(">>> ATTEMPTING TO LOAD FOOTBALL CARD STATE")
    global CARD_ACTIVE, CARD_TEAMS, CARD_ENTRIES, CARD_USERS, CARD_MESSAGE_ID, CARD_POOL
    if not os.path.exists(CARD_STATE_FILE):
        return
    try:
        with open(CARD_STATE_FILE) as f:
            state = json.load(f)
        CARD_ACTIVE = state.get("active", False)
        CARD_TEAMS = state.get("teams", [])
        CARD_ENTRIES = {
            team: {
                "id": data["id"],
                "username": data.get("username"),
                "name": data.get("name", "Legend")
            } for team, data in state.get("entries", {}).items()
        }
        CARD_USERS = state.get("users", {})
        CARD_MESSAGE_ID = state.get("message_id")
        CARD_POOL = state.get("pool", 0)
        print(f">>> Football card state loaded — active: {CARD_ACTIVE}, teams filled: {len(CARD_ENTRIES)}/{len(CARD_TEAMS)}")
    except Exception as e:
        print(f">>>> Failed to load football card state: {e}")

def safe_md(text: str) -> str:
    return escape_markdown(text)

# ---------------- START CARD ----------------
async def start_card(context: ContextTypes.DEFAULT_TYPE):
    global CARD_ACTIVE, CARD_TEAMS, CARD_MESSAGE_ID

    if CARD_ACTIVE:
        return

    CARD_TEAMS = random.sample(ALL_TEAMS, MAX_TEAMS)
    CARD_ACTIVE = True

    msg = await context.bot.send_message(
        chat_id=CHAT_ID,
        text=render_card(),
        parse_mode="Markdown"
    )

    await context.bot.pin_chat_message(
        chat_id=CHAT_ID,
        message_id=msg.message_id,
        disable_notification=True
    )

    CARD_MESSAGE_ID = msg.message_id

    await speak_george(
        "Right then you greedy sods. Grumpy's football card is live. "
        "One dollar a team. Choose badly and suffer.",
        CHAT_ID,
        context=context
    )

# ---------------- PICKTEAM COMMAND (CHAT & WEB APP) ----------------
async def pickteam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CARD_POOL

    if not CARD_ACTIVE:
        # Check if this is from web app
        if context.user_data.get('is_web_app'):
            original_update = context.user_data.get('web_app_original_update')
            if original_update:
                await original_update.message.reply_text("❌ No football card running right now.")
        else:
            await update.message.reply_text("No card running, you impatient git.")
        return

    # ===== GET TEAM NAME =====
    team = None
    is_web_app = context.user_data.get('is_web_app', False)
    web_app_user_data = context.user_data.get('web_app_user', {})
    
    if is_web_app and web_app_user_data:
        # From web app - team is in context
        team = web_app_user_data.get('team', '')
        if not team and context.args:
            team = " ".join(context.args)
    else:
        # From chat command
        if not context.args:
            await update.message.reply_text("Usage: /pickteam <team name>")
            return
        team = " ".join(context.args)

    if not team:
        error_msg = "No team specified."
        if is_web_app:
            original_update = context.user_data.get('web_app_original_update')
            if original_update:
                await original_update.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return

    # ===== GET USER INFO =====
    user_id = None
    username = None
    
    if is_web_app and web_app_user_data:
        # Web app user
        user_id = web_app_user_data.get('id')
        username = web_app_user_data.get('username', '').lstrip('@')
    else:
        # Chat user
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or user.first_name

    # ===== VALIDATE TEAM =====
    if team not in CARD_TEAMS:
        error_msg = f"'{team}' not on the card."
        if is_web_app:
            original_update = context.user_data.get('web_app_original_update')
            if original_update:
                await original_update.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return

    if team in CARD_ENTRIES:
        current_user = CARD_ENTRIES[team].get('username', 'someone')
        error_msg = f"❌ {team} already claimed by @{current_user}."
        if is_web_app:
            original_update = context.user_data.get('web_app_original_update')
            if original_update:
                await original_update.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return

    # ===== CHECK USER LIMITS =====
    uid = str(user_id)
    if CARD_USERS.get(uid, 0) >= MAX_TEAMS_PER_USER:
        error_msg = "❌ Max 5 teams per person."
        if is_web_app:
            original_update = context.user_data.get('web_app_original_update')
            if original_update:
                await original_update.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return

    # ===== CHECK WALLET =====
    wallet = WALLETS.get(uid)
    if not wallet or not wallet.get("pk"):
        error_msg = "❌ No wallet found. Use /start in DM to create one."
        if is_web_app:
            original_update = context.user_data.get('web_app_original_update')
            if original_update:
                await original_update.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return

    # ===== PROCESS PAYMENT =====
    success = await send_usdc(
        wallet["pk"],
        USDC,
        CARD_POOL_WALLET,
        CARD_PRICE_USDC
    )

    if not success:
        error_msg = "❌ Payment failed. Try again."
        if is_web_app:
            original_update = context.user_data.get('web_app_original_update')
            if original_update:
                await original_update.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return

    # ===== ASSIGN TEAM =====
    CARD_USERS[uid] = CARD_USERS.get(uid, 0) + 1
    CARD_ENTRIES[team] = {
        "id": uid,
        "username": username or "unknown",
        "name": username or "unknown"
    }
    CARD_POOL += CARD_PRICE_USDC

    # Update card display
    await context.bot.edit_message_text(
        chat_id=CHAT_ID,
        message_id=CARD_MESSAGE_ID,
        text=render_card(),
        parse_mode="Markdown"
    )

    # Send success messages
    success_msg = f"✅ {team} claimed by @{username}!"
    
    # To web app user
    if is_web_app:
        original_update = context.user_data.get('web_app_original_update')
        if original_update:
            await original_update.message.reply_text(success_msg)
    # To chat user  
    else:
        await update.message.reply_text(success_msg)
    
    # Announce in group
    if speak_george and CHAT_ID:
        await speak_george(
            f"⚽ @{username} claimed {team} on Grumpy's Football Card!",
            CHAT_ID,
            context=context
        )

    save_card_state()

    # Check if card is full
    if len(CARD_ENTRIES) == MAX_TEAMS:
        await finish_card(context)

# ---------------- FINISH CARD ----------------
async def finish_card(context: ContextTypes.DEFAULT_TYPE):
    global CARD_ACTIVE, CARD_POOL, CARD_ENTRIES

    CARD_ACTIVE = False

    if not CARD_ENTRIES:
        await speak_george(
            "Card's full but somehow empty? You lot are useless. No winner today.",
            CHAT_ID,
            context=context
        )
        CARD_POOL = 0
        CARD_ENTRIES = {}
        return

    # Announce full card
    await speak_george(
        "Card's full, you greedy sods. Time to scratch this filthy thing.",
        CHAT_ID,
        context=context
    )
    await asyncio.sleep(5)  # dramatic pause

    # Pick random winning team
    winner_team = random.choice(list(CARD_ENTRIES.keys()))
    winner = CARD_ENTRIES[winner_team]
    winner_id = winner["id"]
    winner_name = winner.get("username") or winner.get("name") or "Some anonymous mug"

    # Exact USDC split: $28 to winner, $4 to house (dev wallet)
    winner_payout = 28 * 10**6  # USDC has 6 decimals
    house_cut = 4 * 10**6

    # Send payout to winner
    winner_address = WALLETS.get(winner_id, {}).get("address")
    if not winner_address:
        await speak_george(
            f"Winner is {winner_name} on {winner_team}... but they have no wallet address? Tough luck. $28 lost in the void.",
            CHAT_ID,
            context=context
        )
    else:
        success = await send_usdc(
            CARD_POOL_PK,
            winner_address,
            winner_payout
        )
        if success:
            await speak_george(
                f"Scratch scratch… {winner_team} wins!\n"
                f"Congrats @{winner_name} — $28 USDC is yours!\n"
                f"House keeps the $4 USDC for George's beer fund, obviously.",
                CHAT_ID,
                context=context
            )
        else:
            await speak_george(
                f"Winner picked ({winner_name} on {winner_team}), but payout failed. George is looking into it. Hold tight.",
                CHAT_ID,
                context=context
            )

    # Send house cut to dev wallet
    dev_address = "0xf1B4aCA502213Ebb1a542B239495F5068d28bC50"
    house_success = await send_usdc(
        CARD_POOL_PK,
        dev_address,
        house_cut
    )
    if not house_success:
        print(">>> HOUSE CUT FAILED - $4 USDC stuck in pool!")

    # Reset card
    CARD_POOL = 0
    CARD_ENTRIES = {}
