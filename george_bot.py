#!/usr/bin/env python3
# GRUMPY GEORGE — FINAL LIVE BOT

import os
import re
import json
import time
import random
import asyncio
import logging
import httpx
import subprocess
import io
import urllib.parse
import base64
import tempfile
import hashlib
import app
from time import time as now_ts
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict, deque
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from dotenv import load_dotenv
from typing import Optional
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

load_dotenv()

# --- MODULE IMPORTS AFTER load_dotenv ---
from buy_pints import setup_pints_globals, buypint_command, touch_chat_activity, add_active_user, rumour_guess_hook
from football_card import setup_football_card, start_card, pickteam_command, load_card_state, render_card, CARD_ACTIVE, CARD_TEAMS, CARD_ENTRIES, ALL_TEAMS, CARD_USERS, CARD_POOL

load_card_state()

from pubsong import setup_pubsong, pubsong_command

# --- ELEVENLABS ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEORGE_VOICE_ID = "t0ctzSC2zcWbWiA1EAxg"
eleven = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# ————— TELEGRAM —————
from telegram import Update, ChatPermissions, Poll, InlineKeyboardMarkup, InlineKeyboardButton, InputFile, Chat, User, Message, InlineQueryResultArticle, InputTextMessageContent, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
    JobQueue,
)

# ==================================================================
# PURE xAI / GROK – 90s TIMEOUT + RETRY = QUIZ ALWAYS WORKS
# ==================================================================
XAI_API_KEY = os.getenv("XAI_API_KEY")

async def grok_chat(messages: list, model="grok-4-latest", temperature=0.85, max_tokens=4000) -> str | None:
    if not XAI_API_KEY:
        print(">>> XAI_API_KEY missing – Grok disabled")
        return None

    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    # 90-second timeout + one retry – Grok-4 will ALWAYS deliver the 20 questions
    for attempt in range(2):
        async with httpx.AsyncClient(timeout=90.0, verify="/etc/ssl/certs/ca-certificates.crt") as client:
            try:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f">>> GROK ERROR (attempt {attempt+1}/2): {e}")
                if attempt == 0:
                    await asyncio.sleep(5)  # brief pause before retry

    print(">>> GROK FAILED AFTER RETRY – quiz cancelled")
    return None

from ai_brain import grumpy_reply

# ==================================================================
# CONFIG
# ==================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8000468938:AAGy_DU4CfEF2vD1y0LPQYH3Uc4gQpFgpVY")
CHAT_ID = -1003155680202
TWITTER_BEARER = os.getenv("TWITTER_BEARER")
TWITTER_ACCOUNT_ID = "1971588070941315072"
WEBSITE_URL = "https://officialgogcoin.com/"
X_URL = "https://x.com/OfficialGOGCoin"
KNOWN_MEMBERS_FILE = "known_members.json"
LEADERBOARD_FILE = "/root/gog_bot/quiz_leaderboard.json"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEORGE_VOICE_ID = "t0ctzSC2zcWbWiA1EAxg"
PRIZE_POOL_PK = "6a06e1ebfb220fae6b425c04c89a7168d7a76714239d387b6a1c440ae6fb1831"
PAID_ENTRIES_FILE = "/root/gog_bot/paid_entries.json"
LAST_REMINDER_SENT = False
PAID_WALLETS: set[str] = set()
PINNED_MESSAGE_ID = None
USED_QUESTIONS_FILE = "/root/gog_bot/used_questions.json"
USED_QUESTIONS = set()
PINTS_DRANK = 0
LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
SPAM_WINDOW = 5
SPAM_MAX = 3
SPAM_TRACK = {}
LINK_WARN = {}
PENDING_CAPTCHAS = {}
bot_muted = False
last_tweet_id = None
RECENT_PUB_JOKE = []
MAX_STORED_PUB_JOKE = 30
RUMOUR_ACTIVE = {}
RUMOUR_CLUES = {}
RUMOUR_TARGET = {}
RUMOUR_GUESSED = {}
PUB_USERS = {}
WEB_APP_CARD_FILE = 'grumpys_pub_games.json'
USER_WALLETS_FILE = "user_wallets.json"

# ------------------- Helper ------------------------------
from io import BytesIO
import subprocess

def convert_to_ogg_opus(audio_bytes: bytes, bitrate="32k") -> BytesIO:
    """
    Convert raw audio bytes (mp3/wav etc.) to OGG/OPUS using ffmpeg.
    Returns a BytesIO containing the OGG data.
    """
    # Run ffmpeg, capture stdout bytes (do NOT pass BytesIO as stdout)
    proc = subprocess.run(
        ["ffmpeg", "-i", "pipe:0", "-f", "ogg", "-c:a", "libopus", "-b:a", bitrate, "pipe:1"],
        input=audio_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True
    )
    ogg_bytes = proc.stdout
    ogg_buffer = BytesIO(ogg_bytes)
    ogg_buffer.seek(0)
    return ogg_buffer

def get_audio_duration_seconds_from_bytes(ogg_bytes: bytes) -> float:
    """
    Uses ffprobe to read the true audio duration.
    If ffprobe is missing, falls back to a rough estimate.
    """
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                "pipe:0"
            ],
            input=ogg_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        duration_str = proc.stdout.decode().strip()
        return float(duration_str)

    except Exception:
        # fallback if ffprobe isn't installed
        print(">>> ffprobe missing or failed — using fallback duration.")
        # Opus ~17k bytes per second at 32 kbps, so:
        fallback = max(1.0, len(ogg_bytes) / 17000)
        return fallback

# -------- GEORGE SPEAK --------
async def speak_george(
    text: str,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    parse_mode: str | None = None
):
    try:
        audio_chunks = eleven.text_to_speech.convert(
            voice_id=GEORGE_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.65,
                similarity_boost=0.85
            )
        )

        audio_bytes = b"".join(chunk for chunk in audio_chunks)
        ogg = convert_to_ogg_opus(audio_bytes)

        await context.bot.send_voice(
            chat_id=chat_id,
            voice=InputFile(ogg, "george.ogg")
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode
        )

    except Exception as e:
        print(f">>> ElevenLabs TTS FAILED: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode
        )

# ---------- PAID ENTRIES ---------------
def load_paid_entries():
    global PAID_WALLETS, PAID_PLAYERS
    if os.path.exists(PAID_ENTRIES_FILE):
        try:
            with open(PAID_ENTRIES_FILE) as f:
                data = json.load(f)
                PAID_WALLETS = set(data.get("wallets", []))
                PAID_PLAYERS = set(map(int, data.get("players", [])))
            print(f">>> Loaded {len(PAID_PLAYERS)} paid entries")
        except Exception as e:
            print(f">>> Failed to load paid entries: {e}")

def save_paid_entries():
    try:
        with open(PAID_ENTRIES_FILE, "w") as f:
            json.dump({
                "wallets": list(PAID_WALLETS),
                "players": list(PAID_PLAYERS),
            }, f)
    except Exception as e:
        print(f">>> Failed to save paid entries: {e}")

#-------- Load leaderboard on startup -----------------
if os.path.exists(LEADERBOARD_FILE):
    try:
        with open(LEADERBOARD_FILE) as f:
            LEADERBOARD = {int(k): v for k, v in json.load(f).items()}
        print(f">>> Loaded leaderboard for {len(LEADERBOARD)} players")
    except Exception as e:
        print(f">>> Failed to load leaderboard: {e}")
    except:
        LEADERBOARD = {}

load_paid_entries()

# -------- Quiz Leaderboard --------
def load_leaderboard():
    global LEADERBOARD
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r") as f:
                data = json.load(f)
                LEADERBOARD = {int(k): v for k, v in data.items()}
            print(f">>> Loaded leaderboard for {len(LEADERBOARD)} players")
        except Exception as e:
            print(f">>> Failed to load leaderboard: {e}")
            LEADERBOARD = {}
    else:
        LEADERBOARD = {}

# -------- Load Used Questions --------------
if os.path.exists(USED_QUESTIONS_FILE):
    try:
        with open(USED_QUESTIONS_FILE) as f:
            USED_QUESTIONS = set(json.load(f))
        print(f">>> Loaded {len(USED_QUESTIONS)} used questions")
    except Exception as e:
        print(f">>> Failed to load used questions: {e}")

# -------- Pinned Counter ------------
async def update_pinned_counter(context: ContextTypes.DEFAULT_TYPE):
    global PINNED_MESSAGE_ID
    chat_id = context.bot_data.get("quiz_chat_id") or CHAT_ID

    entries = len(PAID_PLAYERS)
    prize_pot = entries * 1.0  # $1 per entry

    msg_text = (
        f"🔥 SUNDAY MEGA QUIZ — LIVE ENTRY COUNTER 🔥\n\n"
        f"👥 Entries: {entries}\n"
        f"💰 Prize Pool: ${prize_pot:.2f}\n\n"
        f"Pay your $1 now — or stay poor, you useless lot."
    )

    try:
        if PINNED_MESSAGE_ID is None:
            # Send new message and pin it
            msg = await context.bot.send_message(chat_id=chat_id, text=msg_text)
            await context.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)
            PINNED_MESSAGE_ID = msg.message_id
        else:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=PINNED_MESSAGE_ID,
                    text=msg_text
                )
            except Exception as e:
                if "not modified" in str(e).lower():
                    pass
                else:
                    print(f">>> Pinned edit failed: {e}")
    except Exception as e:
        print(f">>> Pinned counter failed: {e}")

# -------- DM Functions --------
def _derive_fernet_key(pin: str, salt_b64: str) -> bytes:
    """
    Derive a Fernet key from a PIN (string of digits) and base64 salt.
    Returns base64 urlsafe key bytes suitable for Fernet.
    """
    salt = base64.b64decode(salt_b64)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(pin.encode()))
    return key

def get_user_private_key(user_wallet: dict, provided_pin: Optional[str] = None) -> Optional[str]:
    """
    Return decrypted private key if available.
    If the wallet has 'pk' and it's not "HIDDEN", return it.
    If wallet has encrypted_pk + salt, and provided_pin is given (or we try nothing),
    attempt to decrypt with provided_pin. If provided_pin is None, we will NOT try to brute force.
    """
    if not user_wallet:
        return None

    # Plain stored key (discouraged). Return if present and not HIDDEN.
    if user_wallet.get("pk") and user_wallet["pk"] != "HIDDEN":
        return user_wallet["pk"]

    # Encrypted PK path: require the user to provide PIN when calling this helper.
    if user_wallet.get("encrypted_pk") and user_wallet.get("salt_b64"):
        if not provided_pin:
            return None
        try:
            key = _derive_fernet_key(provided_pin, user_wallet["salt_b64"])
            f = Fernet(key)
            decrypted = f.decrypt(user_wallet["encrypted_pk"].encode()).decode()
            return decrypted
        except Exception:
            return None

    return None

# ----- 15 Min Reminder -----
async def dm_paid_reminder(context: ContextTypes.DEFAULT_TYPE):
    global LAST_REMINDER_SENT
    if LAST_REMINDER_SENT:
        return

    chat_id = context.bot_data.get("quiz_chat_id") or CHAT_ID  # fallback

    sent_count = 0
    for user_id_str in PAID_PLAYERS:
        try:
            await context.bot.send_message(
                chat_id=int(user_id_str),
                text="Oi. You paid your quid for the quiz. It starts in 15 minutes. Get your arse back in the group or miss out, you forgetful git."
            )
            sent_count += 1
        except Exception as e:
            print(f">>> DM reminder failed for {user_id_str}: {e}")

    LAST_REMINDER_SENT = True
    print(f">>> 30 minute DM reminder sent to {sent_count} paid punters")  # log only, no group message

# -------- 5 Min Reminder --------
async def five_minute_group_announcement(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.bot_data.get("quiz_chat_id") or CHAT_ID  # fallback

    entries = len(PAID_PLAYERS)
    pool = entries * 1.0

    base_text = f"Quiz starts in 5 minutes. {entries} paid entries. Prize pool ${pool:.2f}. Last chance."

    prompt = f"Rewrite as a short, savage, grumpy old British pub landlord announcement. Max 50 words, TTS-friendly: \"{base_text}\""
    try:
        announcement = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
        announcement = announcement.strip() or base_text
    except Exception as e:
        print(f">>> Grok roast failed for 5-min announcement: {e}")
        announcement = base_text

    # Send voice announcement
    await speak_george(chat_id=chat_id, text=announcement, context=context, parse_mode="Markdown")

    # Update or create pinned counter
    await update_pinned_counter(context)  # uses your existing pinned counter

def tg_mention(user_id: int, fallback_name: str) -> str:
    safe_name = fallback_name.replace("[", "").replace("]", "")
    return f"[{safe_name}](tg://user?id={user_id})"

# ——— CHAT LOCK / UNLOCK — PTB 20.8+ COMPATIBLE ———
async def lock_quiz_chat(chat_id: int, context):
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False
    )
    await context.bot.set_chat_permissions(chat_id=chat_id, permissions=permissions)

async def unlock_quiz_chat(chat_id: int, context):
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False
    )
    await context.bot.set_chat_permissions(chat_id=chat_id, permissions=permissions)

# -------- Manual Start Quiz --------
async def start_quiz_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can force the quiz, you cheeky sod.")
        return

    if MEGA_ACTIVE:
        await update.message.reply_text("Quiz is already running, you daft apeth!")
        return

    await update.message.reply_text(
        "George is kicking off the quiz manually — hold onto your pints!"
    )

    await start_sunday_quiz(context)

# -------- Quiz Leaderboard --------
async def quiz_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not LEADERBOARD:
        await update.message.reply_text("Leaderboard's emptier than George's wallet after a night on the lash. No one's scored yet.")
        return

    # Sort by score descending
    sorted_lb = sorted(LEADERBOARD.items(), key=lambda x: (-x[1]["score"], x[1]["name"]))

    text = "*🔥 SUNDAY MEGA QUIZ LEADERBOARD 🔥*\n\n"
    for i, (user_id, data) in enumerate(sorted_lb[:10], 1):  # Top 10
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        name = data.get("name", "Unknown Mug")
        score = data["score"]
        text += f"{medal} {name} — {score} pts\n"

    if len(sorted_lb) > 10:
        text += f"\n...and {len(sorted_lb) - 10} more useless sods below the top 10."

    await update.message.reply_text(text, parse_mode="Markdown")

# -------- Roast New Members --------
async def roast_user(user: User, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    name = user.first_name or "stranger"
    username = user.username or "nameless mug"
    prompt = (
        f"Write a short, sarcastic, grumpy old British pub landlord roast for a new group member called {name} (@{username}). "
        "Keep it under 50 words, pure banter."
    )
    try:
        roast = await grok_chat(
            [{"role": "user", "content": prompt}],
            temperature=0.9
        )
        roast = roast.strip() if roast else f"Welcome {name}. Try not to be useless."
    except Exception as e:
        print(f">>> Grok roast failed: {e}")
        roast = f"Welcome {name}. The bar’s that way — don’t trip over your ego."

    try:
        await speak_george(
            text=roast,
            chat_id=chat_id,
            context=context
        )
    except Exception as e:
        print(f">>> ROAST TTS FAILED: {e}")
        await context.bot.send_message(chat_id=chat_id, text=roast)
    await asyncio.sleep(3)

# -------- Barred Command --------
async def bar_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /barred @username or reply — George bans them with a roast """
    if not await is_admin(update, context):
        await update.message.reply_text("Sod off — only admins can bar people, you cheeky git.")
        return

    # Reply to message or mention
    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        # Try to get user from mention or username
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":
                    username = update.message.text[entity.offset:entity.offset + entity.length]
                    # Find user in chat — rough, but works
                    # Or just ban by username if possible
                    pass  # advanced — leave for now
        else:
            await update.message.reply_text("Reply to their message or tag them, you daft apeth.")
            return
    else:
        await update.message.reply_text("Who am I barring? Reply to their message or tag 'em.")
        return

    if not target_user:
        await update.message.reply_text("Couldn't find the mug. Try replying to their message.")
        return

    user_id = target_user.id
    name = target_user.first_name or "nameless git"
    username = target_user.username or ""

    try:
        await context.bot.ban_chat_member(CHAT_ID, user_id)
        roast = f"Right, @{username or name} — you've been a proper pain. You're barred. Don't come back, or George'll have words."
        await speak_george(roast, CHAT_ID, context=context)
    except Exception as e:
        await update.message.reply_text(f"Couldn't bar the git: {e}")

# -------- Help Function --------
async def pub_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🍺 The Grumpy Old Git — Help 🍺\n\n"
        "Commands:\n"
        "/football — current football card status\n"
        "/buypint — buy George a pint (he gets louder)\n"
        "/pubsong — George picks a classic and posts lyrics\n"
        "/pickteam - Add the available team you want from the football card\n"
        "/pubjoke - I tell you a pub joke. You laugh or don't\n"
        "/quizleaderboard - Check the global rankings of the Sunday Mega Quiz\n"
        "/pubrumour - When the chats deader than my nan, hear a rumour about someone in here\n"
        "/pubclue - If your to dumb to guess the user, buy a pint for a clue\n"
        "Games running:\n"
        "• Football Card — $1 per team, winner takes $28\n"
        "• Rumours — when chat goes dead start a rumours game, buy pints for clues\n"
        "• Sunday Mega Quiz 3PM UTC— big prizes, roasts, chaos\n\n"
        "• Pool & Darts - Coming soon, Don't ask\n\n"
        "• Bingo - Coming soon, have some patience\n\n"
        "Wallet needed for paid games — DM me /start if you haven't set one up yet, you skint bastards.\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# -------- Football Card --------
from football_card import CARD_ACTIVE

async def football_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_card_state()
    if not CARD_ACTIVE:
        await update.message.reply_text("No football card running right now, you impatient git.")
        return

    status = render_card()  # reuse your render function
    await update.message.reply_text(status, parse_mode="Markdown")

# -------- Pub Jokes --------
async def pubjoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    seed_phrases = [
        "Make it extra groan-worthy this time",
        "Something that would make a vicar wince",
        "Proper old-man cringe, none of that modern rubbish",
        "The kind of joke that clears a room",
        "Keep it short and painful",
        "One so bad it could curdle milk",
        "Something your grandad would tell at Christmas",
        "The type that makes people groan and leave",
        "Absolute classic dad level - no mercy",
        "Make it hurt, but in a funny way"
    ]

    joke_styles = [
        "wordplay pun",
        "misdirection joke",
        "question and answer",
        "fake anecdote",
        "anti-joke"
    ]

    seed = random.choice(seed_phrases)
    style = random.choice(joke_styles)

    recent_summary = "; ".join(RECENT_PUB_JOKE[-5:]) or "None yet"

    prompt = f"""
You are Grumpy George, a miserable old British pub landlord. Swearing is allowed if it fits the joke.
A punter has asked for a pub joke.

Avoid jokes similar to these recent ones:
{recent_summary}

Style: {style}.
{seed}.
Keep it under 30 words. Pure cringe. Deliver the joke as if spoken directly to the punter, including any grumpy intro or insult you like.
End with something like "Now sod off before I charge you for the eye-roll."
"""

    try:
        response = await grok_chat(
            [{"role": "user", "content": prompt}],
            temperature=1.1
        )

        if not response or not isinstance(response, str):
            raise ValueError("Invalid Grok response")

        pub_joke = response.strip()

        # Hard repeat guard
        if pub_joke in RECENT_PUB_JOKE:
            raise ValueError("Repeated pub joke detected")

        RECENT_PUB_JOKE.append(pub_joke)

        if len(RECENT_PUB_JOKE) > MAX_STORED_PUB_JOKE:
            RECENT_PUB_JOKE.pop(0)

    except Exception as e:
        print(f">>> PUB JOKE GROK FAILED: {e}")
        pub_joke = "Even the dad jokes have given up. Must be hereditary. Now clear off."

    await update.message.reply_text(pub_joke)

# -------- Username For Web App --------
def get_user_for_web_app(username: str | None, user_id: int | str | None) -> tuple[str | None, dict | None]:
    """
    Find stored wallet entry for a web app user.

    Prioritizes lookup by user_id (most reliable), then falls back to username.
    Returns (user_id_str, wallet_dict) on success, or (None, None) if not found.
    """
    # Prefer user_id lookup (fast and authoritative)
    user_id_str = str(user_id) if user_id is not None else None
    if user_id_str and user_id_str in WALLETS:
        return user_id_str, WALLETS[user_id_str]

    # Fallback: username lookup (case-insensitive, strip @)
    if username:
        clean_username = username.lstrip('@').lower()
        for uid, wallet_info in WALLETS.items():
            stored_username = wallet_info.get('username', '').lower()
            if stored_username == clean_username:
                return uid, wallet_info

    # No match
    return None, None

# -------- Web App Data Handler --------
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(">>> WEBAPP HANDLER HIT")
    print(update.message)
    print(f"\n{'='*60}")
    print(f">>> 🎮 WEB APP HANDLER at {datetime.now()}")
    print(f">>> From: @{update.effective_user.username or 'unknown'}")
    print(f"{'='*60}")

    if not update.message or not update.message.web_app_data:
        print(">>> No web_app_data - ignoring")
        return

    try:
        raw_data = update.message.web_app_data.data
        print(">>> Raw data:", raw_data)
        data = json.loads(raw_data)
        action = data.get("action")
        print(">>> Action:", action)

        tg_user = update.effective_user
        user_id = tg_user.id
        username = tg_user.username or ""

        # ======================================================
        # ENTER PUB (ONE-TIME USER + WALLET CHECK)
        # ======================================================
        if action == "enter_pub":
            if not username:
                await update.message.reply_text("ENTER_DENIED:NO_USERNAME")
                print(">>> Denied: No username")
                return

            # Load wallets from the dedicated file
            wallets = load_json(USER_WALLETS_FILE, {})
            wallet = wallets.get(str(user_id))
            if not wallet or not wallet.get("address"):
                await update.message.reply_text("ENTER_DENIED:NO_WALLET")
                print(">>> Denied: No wallet")
                return

            try:
                balance = await get_usdc_balance(user_id)
            except Exception:
                balance = 0

            # Mark as entered (in-memory or save to file if persistence is needed)
            PUB_USERS[str(user_id)] = {
                "user_id": str(user_id),
                "username": username,
                "balance": balance,
                "entered_at": datetime.now().isoformat()
            }

            payload = {
                "username": f"@{username}",
                "balance": balance
            }

            await update.message.reply_text("ENTER_OK:" + json.dumps(payload))
            print(">>> ENTER_OK sent")
            return

        # ======================================================
        # UNKNOWN ACTION
        # ======================================================
        else:
            await update.message.reply_text(f"Unknown action: {action}")
            print(">>> Unknown action:", action)

    except Exception as e:
        print(">>> WEB APP CRASH:", e)
        import traceback
        traceback.print_exc()
        await update.message.reply_text("❌ Bot error. Try again.")

# -------- Pub Rumours --------
async def pub_rumour_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RUMOUR_ACTIVE, RUMOUR_PINTS, RUMOUR_WINDOW_END, RUMOUR_TARGET, RUMOUR_CLUES, RUMOUR_GUESSED

    if update.effective_chat.type != "supergroup":
        await update.message.reply_text("Only works in the main group, you daft sod.")
        return

    # Optional: check if enough pints or cooldown, etc.
    if RUMOUR_ACTIVE:
        await update.message.reply_text("Rumours are already running, you impatient git. Wait for the last one to finish.")
        return

    # Start the rumour manually
    RUMOUR_ACTIVE = True
    RUMOUR_PINTS = 0  # or set a minimum if you want
    RUMOUR_WINDOW_END = datetime.now(timezone.utc) + timedelta(minutes=2)

    await speak_george(
        "Right… I've heard things. Nasty little whispers. "
        "Let's see if you lot can work it out. /pubrumours triggered this one.",
        CHAT_ID,
        context=context
    )

    # Then drop the clues as normal (your existing loop)
    RUMOUR_CLUES = await generate_rumour_clues(choose_rumour_target(), RUMOUR_PINTS or 1)
    context.bot_data["rumour_clue_msg_id"] = None

    for i, clue in enumerate(RUMOUR_CLUES):
        if RUMOUR_GUESSED:
            return
        msg = await speak_george(clue, CHAT_ID, context=context, return_message=True)
        if i == 0 and msg:
            context.bot_data["rumour_clue_msg_id"] = msg.message_id
        await asyncio.sleep(CLUE_INTERVAL)

    if not RUMOUR_GUESSED:
        reveal = "You lot are thick as mince. No guesses? Fine, I'll keep me secrets."
        await speak_george(reveal, CHAT_ID, context=context)

    reset_rumour()

# -------- Rumours Clue --------
async def pub_clue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RUMOUR_ACTIVE, RUMOUR_PINTS, RUMOUR_WINDOW_END, RUMOUR_TARGET, RUMOUR_CLUES, RUMOUR_GUESSED

    if update.effective_chat.type != "supergroup":
        await update.message.reply_text("Only works in the main group, you daft sod.")
        return

    user = update.effective_user
    user_id = str(user.id)
    username = user.username or user.first_name or "Mystery Mug"

    # Wallet & payment check
    wallet = user_wallets.get(user_id)
    if not wallet or not wallet.get('address'):
        await update.message.reply_text("No wallet found. DM me /start to set one up, you tight git.")
        return

    amount_shido = 1000 * 10**18  # 1000 SHIDO pint
    success = await send_native_shido(wallet["pk"], PINT_WALLET, amount_shido)
    if not success:
        await update.message.reply_text("Not enough SHIDO or transaction failed. Try again, you skint git.")
        return

    # Pint bought — trigger clue
    if RUMOUR_ACTIVE:
        await update.message.reply_text("Rumours are already running. Wait for the last one to finish, you impatient git.")
        return

    RUMOUR_ACTIVE = True
    RUMOUR_PINTS = 1  # one pint = one clue
    RUMOUR_WINDOW_END = datetime.now(timezone.utc) + timedelta(minutes=2)
    RUMOUR_TARGET = choose_rumour_target()
    RUMOUR_CLUES = []
    RUMOUR_GUESSED = False

    if not RUMOUR_TARGET:
        await speak_george("No juicy targets today. Better luck next pint.")
        reset_rumour()
        return

    await speak_george(
        f"Cheers, @{username} — one pint down the hatch. Right… I've heard things. Nasty little whispers. Let's see if you lot can work it out.",
        CHAT_ID,
        context=context
    )

    # Generate and send one clue
    clue = await generate_single_clue(RUMOUR_TARGET)
    msg = await speak_george(clue, CHAT_ID, context=context, return_message=True)
    if msg:
        context.bot_data["rumour_clue_msg_id"] = msg.message_id

# ==================================================================
# PERSONALITY
# ==================================================================
ROASTS = [
    "You trade like oven mitts on.", "Your stop loss is a suggestion.", "You FOMO’d into a rug.",
    "Your bags are heavier than your brain.", "You’d short the top and long the bottom."
]
WELCOME_ROASTS = ["Fine, you’re in.", "Don’t make me regret it.", "Human detected. Barely.", "Welcome. Behave."]

# ==================================================================
# ADMIN CHECK
# ==================================================================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return m.status in ("administrator", "creator")
    except:
        return False

# ==================================================================
# CAPTCHA + ROAST ON JOIN
# ==================================================================
async def on_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        user_id = member.id

        # 🔇 MUTE IMMEDIATELY
        try:
            await context.bot.restrict_chat_member(
                chat_id=CHAT_ID,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception as e:
            print(f">>> FAILED TO MUTE {user_id}: {e}")

        # 🧠 CAPTCHA
        choices = ["✅", "🔥", "🐸", "💩", "🧠", "❌"]
        answer = random.choice(choices)
        shuffled = choices[:]
        random.shuffle(shuffled)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(c, callback_data=f"captcha:{user_id}:{answer}") for c in shuffled]
        ])

        msg = await update.message.reply_html(
            f"<b>{member.first_name}</b>, tap <b>{answer}</b> in 30s or get kicked.",
            reply_markup=keyboard
        )

        PENDING_CAPTCHAS[user_id] = {
            "msg_id": msg.message_id,
            "answer": answer,
            "deadline": time.time() + 30
        }

        context.application.create_task(captcha_timeout(context, user_id))

async def captcha_timeout(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    await asyncio.sleep(31)
    if user_id not in PENDING_CAPTCHAS:
        return
    # Timeout = kick
    try:
        await context.bot.ban_chat_member(CHAT_ID, user_id)
        await context.bot.unban_chat_member(CHAT_ID, user_id)  # soft kick
    except Exception as e:
        print(f">>> TIMEOUT KICK FAILED {user_id}: {e}")
    PENDING_CAPTCHAS.pop(user_id, None)

async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("captcha:"):
        return

    _, uid_str, chosen = query.data.split(":")
    user_id = int(uid_str)

    if update.effective_user.id != user_id:
        return

    data = PENDING_CAPTCHAS.get(user_id)
    if not data:
        return

    if chosen == data["answer"]:

        username = update.effective_user.username or "nameless wanker"
        welcome_text = (
            f"🍺 Welcome to The Grumpy Old Git, @{username} 🍺\n\n"
            "You've made it past the door — barely.\n\n"
            "/help — full menu of games and commands\n"
            "DM @GrumpyGeorgeBot — set up wallet\n\n"
            "Speak up or sod off — your choice."
        )
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo="https://ik.imagekit.io/swyg02x2g/grok_1767792061439.jpg",  # your pub sign URL
                caption=welcome_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f">>> WELCOME PHOTO FAILED: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)

        # Personal roast
        try:
            await roast_user(update.effective_user, CHAT_ID, context)
        except Exception as e:
            print(f">>> ROAST FAILED ON PASS: {e}")

        # Unmute
        try:
            await context.bot.restrict_chat_member(
                chat_id=CHAT_ID,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=True)
            )
        except Exception as e:
            print(f">>> UNMUTE FAILED {user_id}: {e}")

        await query.edit_message_text("You're in. George has spoken.")
    else:
        # ❌ WRONG — KICK
        await query.edit_message_text("Wrong. Kicked.")
        try:
            await context.bot.ban_chat_member(CHAT_ID, user_id)
            await context.bot.unban_chat_member(CHAT_ID, user_id)  # soft kick
        except Exception as e:
            print(f">>> WRONG ANSWER KICK FAILED {user_id}: {e}")

    PENDING_CAPTCHAS.pop(user_id, None)

# ==================================================================
# LINK + SPAM GUARD
# ==================================================================
async def link_and_spam_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.from_user.is_bot:
        return
    if await is_admin(update, context):
        return

    text = update.message.text
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id

    if LINK_REGEX.search(text):
        if user_id in LINK_WARN and time.time() - LINK_WARN[user_id] < 60:
            await update.message.delete()
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            await context.bot.send_message(chat_id, f"{update.message.from_user.first_name} kicked for links.")
            LINK_WARN.pop(user_id, None)
        else:
            await update.message.delete()
            LINK_WARN[user_id] = time.time()
            await context.bot.send_message(chat_id, f"{update.message.from_user.mention_html()} — no links.", parse_mode="HTML")
        return

    now = time.time()
    bucket = SPAM_TRACK.setdefault(chat_id, {}).setdefault(user_id, deque())
    bucket.append(now)
    while bucket and now - bucket[0] > SPAM_WINDOW:
        bucket.popleft()
    if len(bucket) > SPAM_MAX:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await context.bot.send_message(chat_id, "Spam. Out.")
        bucket.clear()
    touch_chat_activity()
    add_active_user(update.effective_user.id)

# =============================================================================
# TWITTER_WATCHER — FINAL WORKING VERSION (NO SPAM, ROASTS WITH GROK, VOICE)
# ============================================================================
LAST_TWEET_FILE = "/root/gog_bot/last_tweet_id.json"

def load_last_tweet_id():
    if os.path.exists(LAST_TWEET_FILE):
        try:
            with open(LAST_TWEET_FILE) as f:
                return json.load(f).get("last_tweet_id")
        except:
            return None
    return None

def save_last_tweet_id(tweet_id):
    with open(LAST_TWEET_FILE, "w") as f:
        json.dump({"last_tweet_id": tweet_id}, f)

async def check_twitter(context):
    last_id = load_last_tweet_id()
    clean_token = urllib.parse.unquote(TWITTER_BEARER)
    headers = {"Authorization": f"Bearer {clean_token}"}
    url = f"https://api.twitter.com/2/users/{TWITTER_ACCOUNT_ID}/tweets"
    params = {"max_results": 5, "exclude": "retweets,replies", "tweet.fields": "created_at"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=headers, params=params)
        print(f">>> X API response: {r.status_code} at {datetime.now().strftime('%H:%M:%S')}")
        if r.status_code != 200:
            return
        data = r.json().get("data", [])
        if not data:
            return
        new_latest = None
        for tweet in reversed(data):
            tid = tweet["id"]
            if not last_id or int(tid) > int(last_id):
                if not new_latest:
                    new_latest = tid
                tweet_text = tweet["text"]
                tweet_link = f"https://x.com/OfficialGOGCoin/status/{tid}"
                roast_prompt = (
                    f"Grumpy old British git just saw this $GOG tweet. "
                    f"Give a short, savage, sarcastic voice roast (max 25 words): "
                    f'"{tweet_text}"'
                )
                try:
                    roast = await grok_chat([{"role": "user", "content": roast_prompt}], temperature=0.95)
                    roast = roast.strip() or "George saw the tweet. He’s not impressed."
                except:
                    roast = "George saw the tweet. He’s not impressed."
                full_msg = f"{roast}\n\nOriginal tweet:\n{tweet_text}\n{tweet_link}"
                try:
                    await context.bot.send_message(chat_id=CHAT_ID, text=full_msg)
                    print(f">>> SENT ROAST FOR TWEET {tid}")
                except Exception as e:
                    print(f">>> SEND FAILED FOR TWEET {tid}: {e}")
                await asyncio.sleep(3)
        if new_latest:
            save_last_tweet_id(new_latest)
            print(f">>> Saved last_tweet_id: {new_latest}")
    except Exception as e:
        print(f">>> Twitter checker crashed: {e}")

# =================================================
# ——— GRUMPY GEORGE ROASTS NEW MEMBERS WITH xAI ———
# =================================================
CHAT_ID = CHAT_ID

async def grumpy_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members is None:
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue  # ignore bots

        name = member.first_name or "stranger"
        username = member.username or "nameless mug"

        prompt = (
            f"Write a short, sarcastic, grumpy old British pub landlord roast for a new group member called {name} (@{username}). "
            "Keep it under 50 words, pure banter, no swearing."
        )

        try:
            roast = await grok_chat([{"role": "user", "content": prompt}], temperature=0.9)
            roast = roast.strip() if roast else f"Welcome {name}. Try not to be useless."
        except Exception as e:
            print(f">>> Grok roast failed: {e}")
            roast = f"Welcome {name}. The bar’s that way — don’t trip over your ego."

        await context.bot.send_message(
            chat_id=update.effective_chat.id,  # ← send to the group they joined
            text=roast
        )
        await asyncio.sleep(3)  # breathe between roasts if multiple join

# ==================================================================
# SHIDO WALLET + PAID ENTRY
# ==================================================================
from eth_account import Account
from web3 import Web3

# ——— SHIDO RPC & TOKENS ———
SHIDO_RPC = "https://evm.mavnode.io"
web3 = Web3(Web3.HTTPProvider(SHIDO_RPC))

# ——— ADDRESSES — ALL CHECKSUM (CRITICAL) ———
PRIZE_POOL = web3.to_checksum_address("0xF756f99b09202a41214b05434f1d5b545f07B7DC")
PINT_WALLET = web3.to_checksum_address("0x53054372F2ba8697dBE0E44b14A7F7dB4E07A64A")
USDC = web3.to_checksum_address("0xeE1Fc22381e6B6bb5ee3bf6B5ec58DF6F5480dF8")
WSHIDO = web3.to_checksum_address("0x8cbafFD9b658997E7bf87E98FEbF6EA6917166F7")

ENTRY_FEE = 1_000_000  # 1 USDC (6 decimals)
WALLETS_FILE = "/root/gog_bot/user_wallets.json"
WALLETS = {}
PAID_PLAYERS = set()
ENTRY_CUTOFF = None

# Load wallets
def load_wallets():
    global WALLETS
    if os.path.exists(WALLETS_FILE):
        with open(WALLETS_FILE) as f:
            WALLETS = json.load(f)
load_wallets()
load_paid_entries()

# ----------------- Main DM menu (works for /start and editing callback messages) -----------------
async def start_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Accepts Update (command) or callback Update.
    if update.callback_query:
        query = update.callback_query
        chat = query.message.chat
        can_edit = True
    else:
        query = None
        chat = update.effective_chat
        can_edit = False

    if chat.type != "private":
        return

    user_id = str(chat.id)
    wallet = WALLETS.get(user_id, {})

    keyboard = [
        [InlineKeyboardButton("Create Wallet", callback_data="create_wallet")],
        [InlineKeyboardButton("Balance", callback_data="check_balance")],
        [InlineKeyboardButton("Send SHIDO/USDC", callback_data="send_menu")],
        [InlineKeyboardButton("Enter Quiz ($1)", callback_data="enter_quiz")],
        [InlineKeyboardButton("Buy George a Pint", callback_data="buy_pint")],
        [InlineKeyboardButton("View Private Key", callback_data="view_pk")],
        [InlineKeyboardButton("🍺 Enter Pub 🍺", web_app=WebAppInfo(url="https://grumpyspubgames.vercel.app"))],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    addr = wallet.get("address", "Not created yet")
    text = f"**🍺 Grumpy's Pub Quiz Wallet 🍺**\n\nAddress: `{addr}`\n\nChoose action:"

    if can_edit:
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

# ----------------- send_token (place this above your DM block / dm_buttons) -----------------
async def send_token(private_key: str, token_address: str, to_address: str, amount: int) -> bool:
    """
    Sends ERC20 `amount` (raw integer, e.g. wei for 18-decimals) from private_key to to_address.
    Returns True on success, False on failure.
    """
    try:
        acct = Account.from_key(private_key)
        from_addr = acct.address
        token_addr = web3.to_checksum_address(token_address)
        to_addr = web3.to_checksum_address(to_address)

        print(f">>> [SEND] From: {from_addr} | To: {to_addr} | Token: {token_addr} | Amount(raw): {amount}")

        contract = web3.eth.contract(address=token_addr, abi=[{
            "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        }])

        # Get current gas price
        gas_price = web3.eth.gas_price
        print(f">>> [SEND] Current gas price: {gas_price / 1e9:.2f} gwei")

        nonce = web3.eth.get_transaction_count(from_addr)

        tx = contract.functions.transfer(to_addr, amount).build_transaction({
            'chainId': 9008,
            'gas': 200000,
            'gasPrice': gas_price * 2,
            'nonce': nonce,
        })

        print(f">>> [SEND] TX built — gas price: {tx['gasPrice'] / 1e9:.2f} gwei")

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f">>> [SEND] SUCCESS! TX: {tx_hash.hex()}")
        return True

    except Exception as e:
        print(f">>> [SEND] FAILED: {e}")
        return False

# =========== SEND NATIVE SHIDO - BUY A PINT =================
async def send_native_shido(private_key: str, to_address: str, amount: int) -> bool:
    try:
        acct = Account.from_key(private_key)
        to_addr = web3.to_checksum_address(to_address)

        nonce = web3.eth.get_transaction_count(acct.address)
        gas_price = web3.eth.gas_price

        tx = {
            'nonce': nonce,
            'to': to_addr,
            'value': amount,
            'gas': 21000,
            'gasPrice': gas_price * 2,
            'chainId': 9008
        }

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f">>> NATIVE SHIDO SENT: {tx_hash.hex()}")
        return True
    except Exception as e:
        print(f">>> NATIVE SHIDO FAILED: {e}")
        return False

# ——— AUTO SEND 90% OF PRIZE POOL TO WINNER — 10% HOUSE CUT ———
async def auto_send_prize_to_winner(context: ContextTypes.DEFAULT_TYPE):
    chat_id = CHAT_ID

    if not LEADERBOARD:
        base_text = "No one scored a single point — no prize sent, you useless lot."
        prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
        try:
            grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
            grumpy_text = grumpy_text.strip() or base_text
        except:
            grumpy_text = base_text
        await speak_george(grumpy_text, chat_id, context=context)
        return

    # Get winner
    winner_id, winner_data = max(LEADERBOARD.items(), key=lambda x: x[1]["score"])
    winner_name = winner_data["name"]
    winner_display = tg_mention(winner_id, winner_name)  # clickable mention

    winner_wallet = WALLETS.get(str(winner_id), {})
    winner_address = winner_wallet.get("address")
    if not winner_address:
        base_text = f"{winner_name} wins but has no wallet — prize held until they sort it out."
        prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
        try:
            grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
            grumpy_text = grumpy_text.strip() or base_text
        except:
            grumpy_text = base_text
        await speak_george(grumpy_text, chat_id, context=context)
        return

    try:
        balance = web3.eth.contract(address=USDC, abi=[{
            "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }]).functions.balanceOf(PRIZE_POOL).call()

        if balance < 1_000_000:
            base_text = "Prize pool too small — held for next week."
            prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
            try:
                grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
                grumpy_text = grumpy_text.strip() or base_text
            except:
                grumpy_text = base_text
            await speak_george(grumpy_text, chat_id, context=context)
            return

        prize_amount = int(balance * 0.9)
        print(f">>> SENDING PRIZE: {prize_amount / 1e6:.2f} USDC to {winner_address}")

        success = await send_token(PRIZE_POOL_PK, USDC, winner_address, prize_amount)

        if success:
            base_text = f"{winner_name} wins ${prize_amount / 1e6:.2f}! 10% house cut kept for George's beer fund. Paid instantly."
            prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 50 words, TTS-friendly: \"{base_text}\""
            try:
                grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
                grumpy_text = grumpy_text.strip() or base_text
            except:
                grumpy_text = base_text

            await speak_george(grumpy_text, chat_id, context=context)

            # Text announcement with tagged winner
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎉 **PRIZE PAID!**\n\n"
                     f"{winner_display} wins ${prize_amount / 1e6:.2f}!\n\n"
                     f"10% house cut kept for George's beer fund 🍺\n"
                     f"Paid instantly from prize pool.",
                parse_mode="Markdown"
            )
        else:
            base_text = "Prize send failed — George is investigating."
            prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
            try:
                grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
                grumpy_text = grumpy_text.strip() or base_text
            except:
                grumpy_text = base_text
            await speak_george(grumpy_text, chat_id, context=context)
    except Exception as e:
        print(f">>> PRIZE SEND ERROR: {e}")
        base_text = "Prize send error — will retry."
        prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
        try:
            grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
            grumpy_text = grumpy_text.strip() or base_text
        except:
            grumpy_text = base_text
        await speak_george(grumpy_text, chat_id, context=context)

# ----------------- All callbacks handler -----------------
async def dm_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""
    user_id = str(query.from_user.id)
    wallet = WALLETS.get(user_id, {})

    if data == "force_main_menu":
        await start_dm(update, context)
        return

    logging.debug("dm_buttons callback=%s user=%s", data, user_id)

    # --- Create wallet submenu ---
    if data == "create_wallet":
        if wallet:
            await query.edit_message_text("You already have a wallet!")
            return
        keyboard = [
            [InlineKeyboardButton("Show once (never again)", callback_data="create_show_once")],
            [InlineKeyboardButton("Protect with PIN (4-6 digits)", callback_data="create_with_pin")],
            [InlineKeyboardButton("← Back", callback_data="back_main")],
        ]
        await query.edit_message_text(
            "Choose how to receive your private key:\n\n"
            "• Show once = visible only this time (you must save it)\n"
            "• Protect with PIN = the bot will store the key (bot can still use it), and you can view it with your PIN",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # --- Show once: display PK and store plain pk so send/entry works without PIN ---
    if data == "create_show_once":
        acct = Account.create()
        pk = acct.key.hex()
        address = acct.address

        # Store plain pk (so send/entry work w/o PIN). If you later want max security, change to "HIDDEN".
        WALLETS[user_id] = {"address": address, "pk": pk}
        os.makedirs(os.path.dirname(WALLETS_FILE), exist_ok=True)
        with open(WALLETS_FILE, "w") as f:
            json.dump(WALLETS, f)

        await query.edit_message_text(
            f"**WALLET CREATED — PRIVATE KEY (SHOWING ONCE!)**\n\n"
            f"Address: `{address}`\n\n"
            f"Private Key:\n`{pk}`\n\n"
            f"⚠️ SAVE THIS NOW — THIS IS THE ONLY TIME IT WILL BE SHOWN!",
            parse_mode="Markdown"
        )
        return

    # --- Create with PIN: store plain pk (for bot use) AND an encrypted copy for PIN-based viewing ---
    if data == "create_with_pin":
        context.user_data["setting_pin"] = True
        await query.edit_message_text(
            "Enter your 4-6 digit PIN:\n\nThis will allow you to view the private key later using the PIN.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="back_main")]])
        )
        return

    # --- View private key (PIN-protected view) ---
    if data == "view_pk":
        # If an encrypted copy exists, request PIN for viewing.
        if wallet.get("encrypted_pk") and wallet.get("salt_b64"):
            context.user_data["awaiting_pin"] = True
            await query.edit_message_text("Enter your 4-6 digit PIN to view private key:")
            return
        # If plain pk stored, show directly (no PIN required)
        if wallet.get("pk") and wallet.get("pk") != "HIDDEN":
            await query.edit_message_text(f"Your private key:\n`{wallet['pk']}`", parse_mode="Markdown")
            return
        await query.edit_message_text("No private key available to view. Create one first.")
        return

    # --- Check balance: USDC + SHIDO (NATIVE) ---
    if data == "check_balance":
        if not wallet.get("address"):
            await query.edit_message_text(
                "No wallet found. Create one first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]])
            )
            return

        addr = web3.to_checksum_address(wallet["address"])

        try:
            # USDC (ERC-20) — 6 decimals
            usdc_raw = web3.eth.contract(
                address=USDC,
                abi=[{
                    "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                }]
            ).functions.balanceOf(addr).call()
            usdc_bal = usdc_raw / 1e6

            # SHIDO — NATIVE TOKEN (not WSHIDO) — 18 decimals
            shido_bal = web3.eth.get_balance(addr) / 1e18

            text = (
                f"🍺 **Grumpy's Pub Quiz Wallet** 🍺\n\n"
                f"Address: `{addr}`\n\n"
                f"💵 **USDC**: `{usdc_bal:,.6f}`\n"
                f"🪙 **SHIDO**: `{shido_bal:,.8f}`"
            )

            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]])
            )
        except Exception as e:
            await query.edit_message_text(f"Balance error:\n`{e}`")
        return

    # --- Send menu (choose token) ---
    if data == "send_menu":
        has_pk = bool(wallet.get("pk") and wallet["pk"] != "HIDDEN") or (wallet.get("encrypted_pk") and wallet.get("salt_b64"))
        if not has_pk:
            await query.edit_message_text("You must have a private key (PIN-protected or saved) to send tokens. Create one first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]]))
            return
        keyboard = [
            [InlineKeyboardButton("Send SHIDO", callback_data="send_shido")],
            [InlineKeyboardButton("Send USDC", callback_data="send_usdc")],
            [InlineKeyboardButton("← Back", callback_data="back_main")],
        ]
        await query.edit_message_text("Which token do you want to send?", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data in ("send_shido", "send_usdc"):
        token = "shido" if data == "send_shido" else "usdc"
        context.user_data["send_token"] = token
        await query.edit_message_text("Send in this single message format:\n\n`amount address`\n\nExample:\n`1 0xAbc...`", parse_mode="Markdown")
        return

    # --- Enter quiz (pay ENTRY_FEE) ---
    if data == "enter_quiz":
        if not wallet.get("address"):
            await query.edit_message_text("You need a wallet to enter the quiz. Create one first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]]))
            return

        # If bot has a plain pk stored it can attempt immediately
        if wallet.get("pk") and wallet["pk"] != "HIDDEN":
            await query.edit_message_text("Processing entry — checking balance and attempting to send 1 USDC.")
            success, msg = await try_pay_entry(user_id, context=context)
            await context.bot.send_message(chat_id=int(user_id), text=msg)
            await start_dm(update, context)
            return

        # If only encrypted copy exists, we still kept plain 'pk' at creation so this branch is unlikely.
        await query.edit_message_text("No usable private key available for sending. Create wallet with show-once or create-with-pin (bot stores key).")
        return

    # --- Buy George a Pint — Choose how many ---
    if data == "buy_pint":
        keyboard = [
            [InlineKeyboardButton("1 Pint — 1,000 SHIDO", callback_data="buy_pint_1")],
            [InlineKeyboardButton("2 Pints — 2,000 SHIDO", callback_data="buy_pint_2")],
            [InlineKeyboardButton("3 Pints — 3,000 SHIDO", callback_data="buy_pint_3")],
            [InlineKeyboardButton("5 Pints — 5,000 SHIDO", callback_data="buy_pint_5")],
            [InlineKeyboardButton("← Back", callback_data="back_main")],
        ]
        await query.edit_message_text(
            "How many pints for George?\n\n"
            "Each pint = 1,000 SHIDO\n"
            "George gets louder with every one…",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # --- Handle pint purchase ---
    if data.startswith("buy_pint_"):
        print(f">>> PINT BUY ATTEMPT — user: {query.from_user.id} data: {data}")
        print(f">>> WALLET FOUND: {wallet.get('address')} PK present: {'yes' if wallet.get('pk') else 'no'}")

        if not wallet.get("address"):
            await query.edit_message_text("No wallet found.")
            return

        pints = int(data.split("_")[-1])
        amount_shido = pints * 1000 * 10**18
        print(f">>> SENDING {pints} PINTS — {amount_shido} raw units to {PINT_WALLET}")

        success = await send_native_shido(wallet["pk"], PINT_WALLET, amount_shido)
        print(f">>> SEND_TOKEN RESULT: {success}")

        if success:
            global PINTS_DRANK
            PINTS_DRANK += pints

            username = query.from_user.username or "Legend"
            base_text = f"@{username} just bought George {pints} pint{'s' if pints > 1 else ''}! George is getting properly pissed now..."
            # Stage 1: 0-4 pints — merry, light slurring
            if PINTS_DRANK <= 4:
                extra = "George is feeling cheerful... for now."
                swear_level = 0
            # Stage 2: 5-9 pints — tipsy, getting mouthy
            elif PINTS_DRANK <= 9:
                extra = "George is getting louder... and a bit lippy."
                swear_level = 1
            # Stage 3: 10-14 pints — pissed, proper offensive
            elif PINTS_DRANK <= 14:
                extra = "George is properly pissed now. Watch your mouth, lads."
                swear_level = 2
            # Stage 4: 15+ pints — absolute carnage
            else:
                extra = "George is fucking legless. You're all cunts now."
                swear_level = 3

            full_text = base_text + extra
            full_text = base_text + extra

            # Add swearing based on level
            if swear_level >= 1:
                full_text += " You daft sods."
            if swear_level >= 2:
                full_text += " Bunch of useless twats."
            if swear_level >= 3:
                full_text += " Absolute shower of bastards."

            prompt = f"Rewrite this as a short, savage, increasingly drunk and offensive grumpy old British pub landlord voice line. Level {swear_level + 1}/4 drunk. Max 50 words, TTS-friendly: \"{full_text}\""
            try:
                grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
                grumpy_text = grumpy_text.strip() or base_text
            except:
                grumpy_text = base_text

            await speak_george(grumpy_text, CHAT_ID, context=context)

            await query.edit_message_text(
                f"@{username} just bought George **{pints} pint{'s' if pints > 1 else ''}**! 🍺\n"
                f"George is getting properly pissed now...",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                f"✅ {pints} pint{'s' if pints > 1 else ''} sent!\n"
                f"George says: \"CHEERS, YOU BEAUTY!\" 🍻"
            )
        else:
            await query.edit_message_text("❌ Not enough SHIDO or transaction failed. Try again!")
        return

    # --- Buy pint instructions ---
    if data == "buy_pint":
        await query.edit_message_text(
            "To buy George a pint, send USDC to the pint wallet address from your wallet.\n\n"
            f"Pint wallet: `{PINT_WALLET}`\n\n"
            "Your pint will be announced in the main group when detected.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]])
        )
        return

    # --- Back to main menu ---
    if data == "back_main":
        await start_dm(update, context)
        return

    # --- Unknown callback ---
    logging.warning("Unknown callback received: %s", data)
    await query.edit_message_text(f"Unknown action: `{data}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]]))
    return

    # --- Grumpy's Pub Games (wallet & username check) ---
    if data == "pub_games":
        # Check wallet
        if not wallet or not wallet.get("address"):
            await query.edit_message_text(
                "You need a wallet to enter Grumpy's Pub Games. Create one first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]])
            )
            return
        # Check username
        username = query.from_user.username
        if not username:
            await query.edit_message_text(
                "No Telegram username found. Set one in Settings > Username, then try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_main")]])
            )
            return
        # All good → redirect to new domain
        await query.edit_message_text(
            f"Wallet OK (@{username}). Opening Grumpy's Pub Games...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🍺 Grumpy's Pub Games 🍺", url="https://grumpyspubgames.vercel.app")]
            ])
        )
        return

# ------------------ SEND USDC/SHIDO ----------------------------------
async def handle_send_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(">>> SEND INPUT RECEIVED:", update.message.text)
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text("Wrong format — send: amount address")
        return

    amount_str, to_address = parts
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except:
        await update.message.reply_text("Amount must be a number > 0")
        return

    token = context.user_data.get("send_token")
    if token not in ("shido", "usdc"):
        await update.message.reply_text("No token selected — go back to menu")
        return

    user_id = str(update.effective_user.id)
    wallet = WALLETS.get(user_id)
    if not wallet or not wallet.get("pk"):
        await update.message.reply_text("No private key — create wallet first")
        return

    pk = wallet["pk"]

    if token == "usdc":
        raw_amount = int(amount * 1e6)  # USDC 6 decimals
        success = await send_token(pk, USDC, to_address, raw_amount)
        token_name = "USDC"
    else:  # shido
        raw_amount = int(amount * 1e18)  # SHIDO 18 decimals
        success = await send_native_shido(pk, to_address, raw_amount)
        token_name = "SHIDO"

    if success:
        await update.message.reply_text(f"✅ {amount} {token_name} sent to {to_address}")
    else:
        await update.message.reply_text(f"❌ Send failed — check balance/gas")

    # Clear send mode
    context.user_data.pop("send_token", None)
    await start_dm(update, context)

# ----------------- handle_pin_input (create_with_pin) -----------------
async def handle_pin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("setting_pin"):
        return

    pin = update.message.text.strip()
    if not pin.isdigit() or not 4 <= len(pin) <= 6:
        await update.message.reply_text("Invalid PIN — must be 4-6 digits. Try again:")
        return

    acct = Account.create()
    pk = acct.key.hex()
    address = acct.address

    # Derive salt + encrypt for PIN-based viewing
    salt = os.urandom(16)
    salt_b64 = base64.b64encode(salt).decode()
    fernet_key = _derive_fernet_key(pin, salt_b64)
    f = Fernet(fernet_key)
    encrypted_pk = f.encrypt(pk.encode()).decode()

    # Store BOTH plain pk (so send/entry work without asking PIN) AND encrypted copy for PIN view
    WALLETS[str(update.effective_user.id)] = {
        "address": address,
        "pk": pk,
        "encrypted_pk": encrypted_pk,
        "salt_b64": salt_b64
    }
    os.makedirs(os.path.dirname(WALLETS_FILE), exist_ok=True)
    with open(WALLETS_FILE, "w") as fjson:
        json.dump(WALLETS, fjson)

    context.user_data.pop("setting_pin", None)

    await update.message.reply_text(
        f"Wallet created!\n\nAddress: `{address}`\n\nThe bot has stored the key so on-chain actions work. Use View Private Key and your PIN to reveal the key.",
        parse_mode="Markdown"
    )
    await start_dm(update, context)

# ----------------- handle_view_pin_input (only place PIN is used) -----------------
async def handle_view_pin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_pin"):
        return

    pin = update.message.text.strip()
    if not pin.isdigit() or not 4 <= len(pin) <= 6:
        await update.message.reply_text("Invalid PIN — must be 4-6 digits. Try again:")
        return

    user_id = str(update.effective_user.id)
    wallet = WALLETS.get(user_id, {})
    if not wallet.get("encrypted_pk") or not wallet.get("salt_b64"):
        await update.message.reply_text("You don't have a PIN-protected key stored.")
        context.user_data.pop("awaiting_pin", None)
        return

    decrypted = get_user_private_key(wallet, provided_pin=pin)
    if not decrypted:
        await update.message.reply_text("Invalid PIN. Try again or cancel.")
        return

    # Show key once in chat
    await update.message.reply_text(f"Your private key:\n`{decrypted}`", parse_mode="Markdown")
    context.user_data.pop("awaiting_pin", None)
    await start_dm(update, context)

# ----------------- try_pay_entry (uses stored plain pk) -----------------
async def try_pay_entry(user_id: str, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, str]:
    print(f"\n>>> [ENTRY] User {user_id} clicked Enter Quiz")

    # Already paid — block double entry
    if int(user_id) in PAID_PLAYERS:
        print(">>> [ENTRY] Already paid — blocked double entry")
        return True, "✅ You're already in the quiz, you forgetful git! No double-dipping."

    if "quiz_chat_id" not in context.bot_data:
        context.bot_data["quiz_chat_id"] = CHAT_ID

    wallet = WALLETS.get(user_id)
    if not wallet:
        print(">>> [ENTRY] ERROR: No wallet found for this user")
        return False, "❌ No wallet found — create one first."

    if wallet.get("pk") and wallet["pk"] != "HIDDEN":
        pk = wallet["pk"]
    else:
        print(">>> [ENTRY] No usable plain PK found. Aborting.")
        return False, "❌ No private key available — create wallet with show-once or PIN."

    address = wallet.get("address")
    if not address:
        print(">>> [ENTRY] ERROR: wallet has no address")
        return False, "❌ Wallet has no address."

    print(f">>> [ENTRY] Wallet address: {address}")

    # Check USDC balance
    try:
        token_contract = web3.eth.contract(
            address=USDC,
            abi=[{
                "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }]
        )
        balance = token_contract.functions.balanceOf(web3.to_checksum_address(address)).call()
        print(f">>> [ENTRY] USDC BALANCE (raw): {balance}")
        if balance < ENTRY_FEE:
            print(">>> [ENTRY] NOT ENOUGH USDC")
            return False, "❌ Not enough USDC — top up your wallet."
    except Exception as e:
        print(f">>> [ENTRY] BALANCE CHECK FAILED: {e}")
        return False, "❌ Balance check failed — try again later."

    # Attempt send
    success = await send_token(pk, USDC, PRIZE_POOL, ENTRY_FEE)
    print(f">>> [ENTRY] Send result: {'SUCCESS' if success else 'FAILED'}")

    if success:
        PAID_PLAYERS.add(int(user_id))
        PAID_WALLETS.add(wallet["address"].lower())
        save_paid_entries()

        username = "Legend"
        try:
            user = await context.bot.get_chat(user_id)
            username = user.username or user.first_name or "Legend"
        except:
            pass

        await asyncio.sleep(3)
        await announce_entry(int(user_id), username, context)
        await update_pinned_counter(context)
        return True, "✅ Entry successful — 1 USDC sent to the prize pool."

    return False, "❌ Entry failed — check balance or gas. See bot logs."

# ——— GROUP ANNOUNCEMENTS — ENTRY + PINTS ———
PINT_QUEUE = [] # Collect pint buyers between polls

async def announce_entry(user_id: int, username: str, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.bot_data.get("quiz_chat_id") or CHAT_ID
    mention = tg_mention(user_id, username)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{mention} just paid $1 and is IN the Sunday Mega Quiz! 💰🔥",
        parse_mode="Markdown"
    )

async def announce_pints(context: ContextTypes.DEFAULT_TYPE):
    global PINT_QUEUE, PINTS_DRANK
    if not PINT_QUEUE:
        return

    count = len(PINT_QUEUE)
    buyers = " and ".join(tg_mention(uid, name) for uid, name in PINT_QUEUE)

    # Add to total pints drank
    PINTS_DRANK += count

    base_text = f"{buyers} just bought George {count} pint{'s' if count > 1 else ''}! 🍺"

    # Drunk stage extras
    extra = ""
    if PINTS_DRANK >= 5:
        extra = " George is getting proper tipsy now..."
    if PINTS_DRANK >= 10:
        extra = " George is pissed as a newt..."
    if PINTS_DRANK >= 15:
        extra = " George is absolutely bloody legless..."

    full_text = base_text + extra

    prompt = f"Rewrite this as a short, savage, increasingly drunk grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{full_text}\""
    try:
        grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
        grumpy_text = grumpy_text.strip() or full_text
    except:
        grumpy_text = full_text

    await speak_george(grumpy_text, CHAT_ID, context=context)
    PINT_QUEUE = []

# ---------- monitor_pints: poll chain for USDC transfers to PINT_WALLET ----------
async def monitor_pints(context: ContextTypes.DEFAULT_TYPE):
    # Use a small persistent last_block stored on the function to survive repeated calls
    if not hasattr(monitor_pints, "_last_block"):
        try:
            monitor_pints._last_block = web3.eth.block_number
        except Exception:
            monitor_pints._last_block = 0

    try:
        last_block = monitor_pints._last_block
        current = web3.eth.block_number
        if current <= last_block:
            return

        for blk_num in range(last_block + 1, current + 1):
            try:
                block = web3.eth.get_block(blk_num, full_transactions=True)
            except Exception as e_block:
                logging.debug("monitor_pints: failed to fetch block %s: %s", blk_num, e_block)
                continue

            for tx in block.transactions:
                if not tx.to:
                    continue

                try:
                    receipt = web3.eth.get_transaction_receipt(tx.hash)
                    for log in receipt.logs:
                        if log.address and log.address.lower() == USDC.lower():
                            if len(log.topics) >= 3:
                                to_topic = log.topics[2].hex()  # 0x000...{40 hex}
                                to_addr = "0x" + to_topic[-40:]
                                if to_addr.lower() == PINT_WALLET.lower():
                                    try:
                                        amount_raw = int(log.data.hex(), 16)
                                    except Exception:
                                        continue
                                    amount = amount_raw / 1e6  # USDC 6 decimals

                                    from_topic = log.topics[1].hex()
                                    sender = "0x" + from_topic[-40:]
                                    # find user with this address in WALLETS
                                    found_user = None
                                    for uid, w in WALLETS.items():
                                        if w.get("address") and w["address"].lower() == sender.lower():
                                            found_user = uid
                                            break
                                    username = "Legend"
                                    if found_user:
                                        try:
                                            user = await context.bot.get_chat(int(found_user))
                                            username = user.username or user.first_name or user.full_name or "Legend"
                                        except Exception:
                                            username = "Legend"
                                    # send announcement to main group
                                    base_text = f"@{username} just bought George a pint! 🍺 ({amount:.2f} USDC)"
                                    prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
                                    try:
                                        grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
                                        grumpy_text = grumpy_text.strip() or base_text
                                    except Exception as e:
                                        print(f">>> Grok failed for pint announcement: {e}")
                                        grumpy_text = base_text

                                    try:

                                        if MEGA_ACTIVE:
                                            PINT_QUEUE.append((user.id, username))
                                        else:
                                            await speak_george(grumpy_text, CHAT_ID, context=context)
                                    except Exception as e_send:
                                        logging.debug("monitor_pints: failed to announce pint: %s", e_send)

                except Exception as e_tx:
                    logging.debug("monitor_pints: error processing tx %s in block %s: %s", getattr(tx, 'hash', '?'), blk_num, e_tx)
                    continue

        monitor_pints._last_block = current

    except Exception as e:
        logging.exception("monitor_pints: unexpected error: %s", e)
        return

# ----------------- message_router (routes private text messages) -----------------
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" or not update.message or not update.message.text:
        return

    # 1) creating with pin (we expect their chosen PIN)
    if context.user_data.get("setting_pin"):
        await handle_pin_input(update, context)
        return

    # 2) awaiting PIN to view PK
    if context.user_data.get("awaiting_pin"):
        await handle_view_pin_input(update, context)
        return

    # 3) normal send flow: amount + address
    if context.user_data.get("send_token"):
        await handle_send_input(update, context)
        return

    # otherwise ignore or hint
    return

# =====================================
# GENERATE QUIZ QUESTIONS
# =====================================
async def generate_quiz_questions(category: str):
    global AI_QUESTIONS, USED_QUESTIONS
    AI_QUESTIONS = []
    print(f">>> Generating {QUESTIONS_PER_ROUND} questions for {category}")

    # Add used questions to prompt to avoid repeats
    used_examples = ""
    if USED_QUESTIONS:
        used_examples = "\n\nDO NOT repeat any of these questions EVER:\n" + "\n".join(list(USED_QUESTIONS)[:20])  # last 20

    prompt = f"""Give me exactly {QUESTIONS_PER_ROUND} BRAND NEW multiple-choice questions about {category}.
    Make sure the correct answers are EVENLY DISTRIBUTED across A, B, C, D - no more than one of each letter if possible
{USED_QUESTIONS}

Only output in this format — no intro, no numbers, no extra text:

What year was the Battle of Hastings?
A) 1066
B) 1067
C) 1065
D) 1068
Correct: A

Do it for {QUESTIONS_PER_ROUND} questions about {category}. Start now."""

    try:
        raw = await grok_chat([{"role": "user", "content": prompt}], temperature=1.0)  # max creativity
        print(f">>> Grok raw:\n{raw}")

        questions = []
        new_used = set()
        for block in raw.split('\n\n'):
            if 'Correct:' in block:
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                if len(lines) >= 6:
                    q = lines[0]
                    if q in USED_QUESTIONS:
                        continue  # skip repeat
                    opts = [lines[i][3:].strip() for i in range(1, 5)]
                    correct = lines[-1].split("Correct:")[1].strip()[0]
                    if correct in "ABCD" and len(opts) == 4:
                        questions.append({"q": q, "options": opts, "correct": correct})
                        new_used.add(q)

        AI_QUESTIONS = questions

        # Save new used questions
        USED_QUESTIONS.update(new_used)
        try:
            with open(USED_QUESTIONS_FILE, "w") as f:
                json.dump(list(USED_QUESTIONS), f)
        except Exception as e:
            print(f">>> Failed to save used questions: {e}")

        print(f">>> Generated {len(AI_QUESTIONS)} new questions")
    except Exception as e:
        print(f">>> Grok failed: {e}")
        AI_QUESTIONS = []

# ================================
# SUNDAY MEGA QUIZ — FINAL LIVE + INSTANT TEST ON RESTART
# ================================
QUESTIONS_PER_ROUND = 5
TOTAL_ROUNDS = 5
MEGA_ACTIVE = False
AI_QUESTIONS = []
QUESTION_INDEX = 0
CURRENT_ROUND = 0

async def start_sunday_quiz(context: ContextTypes.DEFAULT_TYPE, update: Update | None = None):
    global MEGA_ACTIVE, QUESTION_INDEX, AI_QUESTIONS, CURRENT_ROUND, LEADERBOARD, PAID_PLAYERS, PINTS_DRANK

    if len(PAID_PLAYERS) < 3:
        if update:
            await update.message.reply_text("Not enough punters paid up — need at least 3 for the quiz. Try again next week, you tight gits.")
        print(">>> QUIZ CANCELLED — LESS THAN 3 PAID PLAYERS")
        return

    if MEGA_ACTIVE:
        if update and update.message:
            await update.message.reply_text("Quiz already running, you daft apeth!")
        return

    MEGA_ACTIVE = True
    CURRENT_ROUND = 0
    QUESTION_INDEX = 0
    LEADERBOARD = {}
    PINTS_DRANK = 0  # reset drunk George

    context.bot_data["poll_map"] = {}
    context.bot_data["poll_start_time"] = {}

    # Get chat_id
    chat_id = update.effective_chat.id if update and update.effective_chat else context.bot_data.get("quiz_chat_id") or CHAT_ID
    context.bot_data["quiz_chat_id"] = chat_id

    await update_pinned_counter(context)

    # LOCK CHAT
    try:
        await lock_quiz_chat(chat_id, context)

        base_text = "Chat locked – shut yer gobs!"
        prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
        try:
            grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
            grumpy_text = grumpy_text.strip() or base_text
        except:
            grumpy_text = base_text

        await speak_george(grumpy_text, chat_id, context=context)
    except Exception as e:
        print(f">>> Lock failed: {e}")

    # INTRO
    try:
        intro = await grok_chat([{"role": "user", "content": "Short sarcastic Grumpy Old Git quiz intro, roast the punters, TTS-friendly."}])
        await speak_george(text=f"🗣️ {intro or 'Right, quiz time. Try not to be useless.'}", chat_id=chat_id, context=context)
    except Exception as e:
        print(f">>> Intro roast failed: {e}")

    # ROUNDS
    categories = ["Pub Trivia", "Music", "History", "Film & TV", "Sports"]
    random.shuffle(categories)
    for round_num, category in enumerate(categories[:TOTAL_ROUNDS], 1):
        CURRENT_ROUND = round_num
        base_text = f"Round {round_num}: {category.upper()}"
        prompt = f"Announce this round in the voice of a sarcastic, grumpy old British pub landlord. Short and natural for TTS: \"{base_text}\""
        try:
            grumpy_round = await grok_chat([{"role": "user", "content": prompt}], temperature=0.9)
            grumpy_round = grumpy_round.strip() or base_text
        except:
            grumpy_round = base_text

        await speak_george(
            text=grumpy_round,
            chat_id=chat_id,
            context=context
        )

        await generate_quiz_questions(category)
        if len(AI_QUESTIONS) < QUESTIONS_PER_ROUND:
            await context.bot.send_message(chat_id=chat_id, text="Grok’s being lazy – round skipped.")
            continue

        for q_num, q in enumerate(AI_QUESTIONS[:QUESTIONS_PER_ROUND], 1):
            bold_header = f"*Round {round_num}, Question {q_num}:*"
            base_text = f"Question {q_num}: {q['q']}"
            prompt = f"Read this question in the voice of a sarcastic, grumpy old British pub landlord. Keep it short and natural for TTS: \"{base_text}\""
            try:
                grumpy_question = await grok_chat([{"role": "user", "content": prompt}], temperature=0.9)
                grumpy_question = grumpy_question.strip() or base_text
            except:
                grumpy_question = base_text

            await speak_george(grumpy_question, chat_id, context=context)
            await asyncio.sleep(14)

            poll = await context.bot.send_poll(
                chat_id=chat_id,
                question=f"Q{q_num}: {q['q']}",
                options=q["options"],
                type=Poll.QUIZ,
                correct_option_id="ABCD".index(q["correct"]),
                is_anonymous=False,
                open_period=10
            )

            correct_idx = "ABCD".index(q["correct"])
            context.bot_data["poll_map"][poll.poll.id] = correct_idx
            context.bot_data["poll_start_time"][poll.poll.id] = now_ts()
            await asyncio.sleep(14)  # poll + pint buffer
            await announce_pints(context)  # ← Pints announced here — perfect timing

        # END OF ROUND ROAST
        top5 = "\n".join(f"{i+1}. {v['name']} — {v['score']} pts"
                        for i, (_, v) in enumerate(sorted(LEADERBOARD.items(), key=lambda x: -x[1]["score"])[:5]))
        roast = await grok_chat([{"role": "user", "content": f"Short brutal roast for end of round {round_num}. Leaderboard:\n{top5 or 'Everyone is useless'}"}])
        await speak_george(chat_id=chat_id, text=f"🗣️ {roast or 'Pathetic bunch.'}", context=context)
        await asyncio.sleep(5)

    # END QUIZ
    MEGA_ACTIVE = False

    global PINNED_MESSAGE_ID
    if PINNED_MESSAGE_ID:
        try:
            await context.bot.unpin_chat_message(chat_id=chat_id, message_id=PINNED_MESSAGE_ID)
        except Exception as e:
            print(f">>> Unpin failed: {e}")
        PINNED_MESSAGE_ID = None

    PAID_PLAYERS.clear()
    PAID_WALLETS.clear()
    if os.path.exists(PAID_ENTRIES_FILE):
        try:
            os.remove(PAID_ENTRIES_FILE)
            print(">>> Paid entries file deleted")
        except Exception as e:
            print(f"Failed to delete paid entries file: {e}")

    # Final leaderboard
    if LEADERBOARD:
        # Sorted leaderboard with tagged names
        sorted_board = sorted(LEADERBOARD.items(), key=lambda x: -x[1]["score"])
        board_lines = []
        for i, (user_id, data) in enumerate(sorted_board, 1):
            mention = tg_mention(user_id, data["name"])
            board_lines.append(f"{i}. {mention} — {data['score']} pts")
        board = "\n".join(board_lines)
        base_text = f"Final leaderboard:\n{board}"
    else:
        base_text = "Not a single point scored. You’re all useless."

    # Grok roast of the leaderboard
    prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 50 words, TTS-friendly: \"{base_text}\""
    try:
        final_roast = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
        final_roast = final_roast.strip() or base_text
    except:
        final_roast = base_text

    # George speaks the roast
    await speak_george(final_roast, chat_id, context=context)

    # Then send the actual leaderboard as text (tagged, readable)
    leaderboard_text = base_text if not LEADERBOARD else f"**Final Leaderboard**\n\n{board}"
    await context.bot.send_message(
        chat_id=chat_id,
        text=leaderboard_text,
        parse_mode="Markdown"
    )

    # Auto payout
    await auto_send_prize_to_winner(context)

    # UNLOCK CHAT
    try:
        await unlock_quiz_chat(chat_id, context)

        base_text = "Chat unlocked — you can speak again!"
        prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
        try:
            grumpy_unlock = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
            grumpy_unlock = grumpy_unlock.strip() or base_text
        except:
            grumpy_unlock = base_text

        await speak_george(grumpy_unlock, chat_id, context=context)
    except Exception as e:
        print(f">>> UNLOCK FAILED: {e}")

        # Force unlock
        try:
            await context.bot.set_chat_permissions(
                chat_id=chat_id,
                permissions=ChatPermissions(can_send_messages=True)
            )

            base_text = "Chat force-unlocked — George kicked the door in!"
            prompt = f"Rewrite this as a short, savage, grumpy old British pub landlord voice line. Max 40 words, TTS-friendly: \"{base_text}\""
            try:
                grumpy_force = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
                grumpy_force = grumpy_force.strip() or base_text
            except:
                grumpy_force = base_text

            await speak_george(grumpy_force, chat_id, context=context)
        except Exception as e_force:
            print(f">>> Force unlock failed: {e_force}")

    # Save leaderboard
    try:
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump(LEADERBOARD, f)
        print(">>> Leaderboard saved")
    except Exception as e:
        print(f">>> Save leaderboard failed: {e}")

# ——— POLL ANSWER — PAID PLAYERS ONLY — FIXED & DEBUGGED ———
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MEGA_ACTIVE:
        return

    answer = update.poll_answer
    user = answer.user

    # Find the wallet for this user ID
    wallet = WALLETS.get(str(user.id))
    if not wallet:
        return  # no wallet — ignore

    # Check if this wallet's address is paid
    paid_address = wallet.get("address", "").lower()
    if paid_address not in PAID_WALLETS:
        return  # wallet not paid — ignore

    if not answer.option_ids:
        return

    poll_map = context.bot_data.get("poll_map", {})
    poll_times = context.bot_data.get("poll_start_time", {})

    if answer.poll_id not in poll_map:
        return

    chosen = answer.option_ids[0]
    correct_idx = poll_map[answer.poll_id]

    poll_start = poll_times.get(answer.poll_id)
    if not poll_start:
        return

    elapsed = now_ts() - poll_start

    # ⏱️ Time-based scoring
    if chosen == correct_idx:
        if elapsed <= 5:
            points = 5
        elif elapsed <= 10:
            points = 3
        else:
            points = 0
    else:
        points = 0

    if user.id not in LEADERBOARD:
        LEADERBOARD[user.id] = {
            "name": user.full_name or "Stranger",
            "username": user.username,
            "score": 0
        }

    LEADERBOARD[user.id]["score"] += points

    # Silent DM feedback
    try:
        if points > 0:
            await context.bot.send_message(user.id, f"Correct! +{points} pts")
        else:
            await context.bot.send_message(user.id, "Wrong")
    except:
        pass

# ==================================================================
# GHOST CLEANUP
# ==================================================================
async def cleanup_ghost_accounts(context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(KNOWN_MEMBERS_FILE):
        return
    try:
        with open(KNOWN_MEMBERS_FILE, "r") as f:
            known = json.load(f)
    except:
        return
    kicked = 0
    for user_id_str in list(known.keys()):
        user_id = int(user_id_str)
        try:
            member = await context.bot.get_chat_member(CHAT_ID, user_id)
            if member.status in ("left", "kicked") or member.user.is_deleted:
                await context.bot.ban_chat_member(CHAT_ID, user_id)
                kicked += 1
                del known[user_id_str]
        except:
            del known[user_id_str]
            kicked += 1
    with open(KNOWN_MEMBERS_FILE, "w") as f:
        json.dump(known, f)
    if kicked:
        await context.bot.send_message(CHAT_ID, f"Cleaned {kicked} ghosts.")

# ==================================================================
# COMMANDS & AI CHAT
# ==================================================================
async def roast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(ROASTS))

async def website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WEBSITE_URL)

async def x_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(X_URL)

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_muted or not update.message or not update.message.text:
        return
    text = update.message.text.lower()
    me = (await context.bot.get_me()).username.lower()
    mentioned = f"@{me}" in text
    replied = update.message.reply_to_message and update.message.reply_to_message.from_user.id == (await context.bot.get_me()).id
    if mentioned or replied:
        reply = await grumpy_reply(update.message.text, update.effective_user.id, update.effective_chat.id)
        await update.message.reply_text(reply)
    touch_chat_activity()
    add_active_user(update.effective_user.id)

# ==================================================================
# MAIN
# ==================================================================
async def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(10).get_updates_read_timeout(1).build()

    print(">>> 🤖 BOT STARTING - Testing web app data flow")

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_members))
    app.add_handler(CallbackQueryHandler(captcha_callback, pattern=r"^captcha:"))

    # ------------------ handlers ------------------
    app.add_handler(CommandHandler("startquiz", start_quiz_backup))
    app.add_handler(CommandHandler("start", start_dm))
    app.add_handler(CommandHandler("buypint", buypint_command))
    app.add_handler(CommandHandler("pickteam", pickteam_command))
    app.add_handler(CommandHandler("pubhelp", pub_help_command))
    app.add_handler(CommandHandler("football", football_command))
    app.add_handler(CommandHandler("pubsong", pubsong_command))
    app.add_handler(CommandHandler("pubjoke", pubjoke_command))
    app.add_handler(CommandHandler("pubrumour", pub_rumour_command))
    app.add_handler(CommandHandler("pubclue", pub_clue_command))


        # AI chat — mentions or replies
    app.add_handler(CallbackQueryHandler(dm_buttons))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & (filters.Regex(r'@GrumpyGeorgeBot') | filters.REPLY), ai_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, message_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, link_and_spam_guard))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_send_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, rumour_guess_hook))

    app.add_handler(CommandHandler("roast", roast))
    app.add_handler(CommandHandler("website", website))
    app.add_handler(CommandHandler("x", x_cmd))
    app.add_handler(CommandHandler("quizleaderboard", quiz_leaderboard))
    app.add_handler(CommandHandler("barred", bar_user))
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    # ------------------ jobs ------------------
    app.job_queue.run_repeating(monitor_pints, interval=30, first=10)
    app.job_queue.run_once(start_card, when=5)

    def next_sunday_3pm_london():
        now = datetime.now(ZoneInfo("Europe/London"))
        days_ahead = (6 - now.weekday()) % 7
        next_sunday = now + timedelta(days=days_ahead)
        target = next_sunday.replace(hour=15, minute=0, second=0, microsecond=0)
        if target > now:
            return target
        return target + timedelta(weeks=1)

    first_quiz = next_sunday_3pm_london()

    # Weekly Sunday quiz at 3 PM London
    app.job_queue.run_repeating(
        callback=start_sunday_quiz,
        interval=timedelta(weeks=1),
        first=first_quiz,
        name="Sunday Mega Quiz Weekly"
    )

    # 15-minute DM reminder
    app.job_queue.run_repeating(
        callback=dm_paid_reminder,
        interval=timedelta(weeks=1),
        first=first_quiz - timedelta(minutes=15),
        name="Sunday Quiz 15 Min Reminder"
    )

    # 5-minute group announcement
    app.job_queue.run_repeating(
        callback=five_minute_group_announcement,
        interval=timedelta(weeks=1),
        first=first_quiz - timedelta(minutes=5),
        name="Sunday Quiz 5 Min Announcement"
    )

    print(f">>> SUNDAY MEGA QUIZ WEEKLY — EVERY SUNDAY 3 PM LONDON (FIRST RUN: {first_quiz.isoformat()})")

    app.job_queue.run_daily(cleanup_ghost_accounts, time=datetime.strptime("03:00", "%H:%M").time())
    app.job_queue.run_repeating(
        check_twitter,
        interval=43200,
        first=30,
    )
    print("GRUMPY GEORGE STARTING – PURE GROK-4 – FULLY ARMED")

    setup_pints_globals(WALLETS, PINT_WALLET, CHAT_ID, speak_george, grok_chat, send_native_shido, MEGA_ACTIVE)

    setup_football_card({
        "CHAT_ID": CHAT_ID,
        "speak_george": speak_george,
        "send_usdc": send_token,
        "WALLETS": WALLETS,
        "USDC": USDC,
        "CARD_POOL_PK": "2693abc999283c7372d0c74faf664eb22d3aff2a2eda8bc0bf5e3a66cd0d9f3f"
    })

    setup_pubsong({
        "speak_george": speak_george,
        "grok_chat": grok_chat
    })

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    print("GRUMPY GEORGE IS ALIVE AND GRUMPY")

    load_leaderboard()
    await asyncio.Event().wait()  # keep running forever

if __name__ == "__main__":
    asyncio.run(main())
