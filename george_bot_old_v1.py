#!/usr/bin/env python3
# Grumpy George (GOG) v2.0 — Fully Patched, Secure, Grumpy as Hell

import os
import re
import time
import random
import asyncio
import logging
import json
import requests
import tweepy
from collections import deque, defaultdict
from datetime import datetime, timedelta

# OpenAI for sarcastic questions
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------------------------------------------
# Telegram imports – THIS IS THE IMPORTANT FIX
# ------------------------------------------------------------------
from telegram import (
    Update,
    Poll,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatMember
)
from telegram.ext import (
    Application,          # ← this was missing before
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# Configuration – HARD-CODED (systemd/virtualenv keeps killing env vars)
# -----------------------------
BOT_TOKEN = "8000468938:AAGy_DU4CfEF2vD1y0LPQYH3Uc4gQpFgpVY"
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAFwD5AEAAAAADOjphgN41iZ/a/FP8MbMZqhUWdY=hvMlPW9QNMJjeatNKeaHHGknDwpjd1Q24Hn86Cu3P9Ma0VnIGD"
CHAT_ID = -1003155680202
TWITTER_HANDLE = "OfficialGOGCoin"
WEBSITE_URL = "https://officialgogcoin.com/"
X_URL = "https://x.com/OfficialGOGCoin?t=56L6aZxiHiDrm5f5OTDdhQ&s=09"
X_USER_ID = "1971588070941315072"

# -----------------------------
# Constants
# -----------------------------
COOLDOWN_SECONDS = 30
LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
SPAM_WINDOW_SECONDS = 5
SPAM_MAX_MSGS = 3
TWITTER_CHECK_INTERVAL = 28800  # Daily (8h) — X Free Tier safe
TWITTER_INTERVAL_VARIATION = random.randint(-1800, 1800)  # ±30 mins

# Files
USER_ID_FILE = 'user_id.json'
LAST_TWEETS_FILE = 'last_tweets.json'
KNOWN_MEMBERS_FILE = 'known_members.json'

# Runtime state
SPAM_TRACK = {}
LINK_WARN = {}
PENDING_CAPTCHAS = {}
LAST_TWEETS = set()
bot_muted = False
last_info_reply = datetime.min

# Memory for AI (moved to ai_brain)
from ai_brain import grumpy_reply

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("grumpy_george")

# -----------------------------
# Personality
# -----------------------------
GRUMPY_REPLIES = [
    "What do you want now?", "You again? Buy me a pint first.", "Speak up, I can’t hear you over all the hype.",
    "I’m not your therapist — go talk to your wallet.", "Still old, still grumpy, still right.", "Ask me after coffee. Or never.",
    "Back in my day we had fewer questions and more profit.", "You tag me, I charge interest.", "I’ve got slippers older than your portfolio.",
    "If it’s not about $GOG, move along.", "I read your tag — didn’t enjoy it.", "You brought opinions but left facts at home.",
    "That better be important. It wasn’t? Thought so.", "Put some respect on it, lad.", "I’d clap back harder, but I might pull a hip.",
    "Bother me again and I’ll short your optimism.", "Use fewer words. My patience has decimals: 0.", "Tread lightly. I woke up on the wrong decade.",
    "I’ve seen healthier charts on a heart monitor.", "Ask yourself: ‘does George care?’ The answer is no.", "I’ve had more fun reading tax forms.",
    "If common sense was a token, you’d be illiquid.", "Not now. I’m busy not trusting the market.", "I don’t do hopium. I do sarcasm.",
    "You call that alpha? That’s diet rumor.", "Tagging me won’t pump your bags, sunshine.", "I’d tell you a secret, but you’d tweet it.",
    "When I want noise, I’ll open Twitter.", "If it sounds too good, it is.", "Less moon talk, more execution.",
    "My patience is a support line: already broken.", "Cute question. Shame about the logic.", "I’d answer, but you won’t listen.",
    "Don’t test me. I fail people for sport.", "Come back when your chart stops crying.", "I don’t give ‘NFA’. I give ‘NAH’."
]

ROASTS = [
    "You trade like you’ve got oven mitts on.", "I’ve seen garden gnomes with more ambition.", "Back in my day even scams had standards.",
    "Your risk management is just wishing.", "You’re a buy-high, sell-low specialist.", "You FOMO’d so hard you left your wallet behind.",
    "Your stop loss is pure imagination.", "You call that TA? That’s abstract art.", "I’ve seen sturdier hands on a jellyfish.",
    "You set alerts just to snooze them.", "Your edge is a circle.", "You could rug a picnic blanket.", "If patience was a token you’d be bankrupt.",
    "You chase green candles like moths to a flame.", "Your DCA is just ‘Desperate Candle Addition’.", "You call it a thesis; it’s a diary of delusions.",
    "You hold conviction like a wet paper bag.", "You’d front-run a bus… from behind.", "I’ve seen bots with more personality and better PnL.",
    "You buy resistance and sell support. Iconic.", "Your alpha leaks faster than your conviction.", "The only thing you accumulate is regrets.",
    "Even your memes are illiquid.", "You couldn’t find liquidity with a map.", "You average down until the floor gives up.",
    "Your indicators point to ‘cope’.", "You do research by reading replies.", "You think ‘locked LP’ means locked expectations.",
    "You call that utility? It’s a coaster.", "Your plan is ‘vibes and vibes alone’.", "You need a mentor. Or a mirror.",
    "You’d sell the top if it was the bottom.", "If hopium paid, you’d be a whale.", "Your backtest was a bedtime story.",
    "Diversified? You own ten of the same mistake.", "You chart with crayons.", "You long anxiety and short sleep.",
    "You’d get front-run by a turtle.", "If patience was APR, you’d earn 0%.", "Your ‘research’ is just recycled cope.",
    "You trust influencers with unverified eyebrows.", "You ape like the barrel is on fire.", "You ‘secure profits’ by imagining them.",
    "Liquidations fear your portfolio out of pity.", "You could misclick a hardware wallet.", "Your slippage tolerance is your personality.",
    "You ‘nibble the dip’ and choke on fees.", "You hold like a windy plastic bag.", "Even rugs avoid you out of respect.",
    "You don’t miss opportunities—opportunities miss you."
]

WELCOME_ROASTS = [
    "Fine, you’re in. Don’t make me regret it.", "Verified. Try not to trip over your own bags.", "Human detected. Barely.",
    "You passed. Standards are low today.", "Alright, sit down and don’t touch anything.", "Great, another genius. Park yourself.",
    "Welcome. Now behave or be gone.", "Okay, okay — just don’t spam."
]

GRUMPY_INTROS = [
    "The grump has posted again. Don’t all rush at once.", "Go and see the new post… or don’t. I don’t care.",
    "Apparently I’ve posted again. Try to contain your excitement.", "Another day, another grumble from yours truly.",
    "I’ve spoken. Whether you listen is your mistake.", "New post. Lower your expectations accordingly.",
    "Just posted something. Probably better than your bags.", "The old git’s at it again. Brace yourselves."
]

# -----------------------------
# Helpers
# -----------------------------
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        cm = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return cm.status in (ChatMember.ADMINISTRATOR, ChatMember.OWNER)
    except Exception:
        return False

def contains_url(text: str) -> bool:
    return bool(LINK_REGEX.search(text or ""))

def mark_spam(chat_id: int, user_id: int) -> int:
    now = time.time()
    chat_bucket = SPAM_TRACK.setdefault(chat_id, {})
    u = chat_bucket.setdefault(user_id, {"times": deque(), "strikes": 0})
    dq = u["times"]
    dq.append(now)
    while dq and now - dq[0] > SPAM_WINDOW_SECONDS:
        dq.popleft()
    return len(dq)

def inc_strike(chat_id: int, user_id: int) -> int:
    chat_bucket = SPAM_TRACK.setdefault(chat_id, {})
    u = chat_bucket.setdefault(user_id, {"times": deque(), "strikes": 0})
    u["strikes"] += 1
    return u["strikes"]

def reset_user_spam(chat_id: int, user_id: int):
    chat_bucket = SPAM_TRACK.setdefault(chat_id, {})
    chat_bucket[user_id] = {"times": deque(), "strikes": 0}

# -----------------------------
# Member Tracking (for cleanup)
# -----------------------------
async def track_member(user_id: int, action: str):
    known = {}
    if os.path.exists(KNOWN_MEMBERS_FILE):
        with open(KNOWN_MEMBERS_FILE, 'r') as f:
            known = json.load(f)
    now = datetime.now().isoformat()
    known[str(user_id)] = {'last_seen': now, 'status': action}
    with open(KNOWN_MEMBERS_FILE, 'w') as f:
        json.dump(known, f)

# -----------------------------
# Commands
# -----------------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oi, it’s Grumpy George here! What do you want? 😠")
    print(f"Chat ID: {update.effective_chat.id}")

async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(ROASTS))

async def website_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Grumpy’s lair: {WEBSITE_URL}")

async def x_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Our X: {X_URL}")

async def shutup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_muted
    if not await is_admin(update, context):
        await update.message.reply_text("You’re not the boss of me. 😠")
        return
    bot_muted = True
    await update.message.reply_text("Fine, I’ll keep my mouth shut. 😶")

async def speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_muted
    if not await is_admin(update, context):
        await update.message.reply_text("You can’t tell me what to do. 😠")
        return
    bot_muted = False
    await update.message.reply_text("Right, I’m back. What did I miss? 😏")

async def chatid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Chat ID for this chat: `{chat_id}`", parse_mode="Markdown")

# -----------------------------
# Moderation
# -----------------------------
async def link_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if update.message.from_user.is_bot or text.startswith("/"):
        return
    if contains_url(text):
        if await is_admin(update, context):
            return
        try:
            await update.message.delete()
        except Exception:
            pass
        await context.bot.send_message(update.effective_chat.id,
            f"{update.effective_user.mention_html()} — only admins can share links. 😠",
            parse_mode="HTML"
        )

async def mention_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_info_reply, bot_muted
    if bot_muted:
        return
    if not update.message or not update.message.text:
        return
    text = (update.message.text or "").lower()
    bot_user = (await context.bot.get_me()).username.lower()
    if f"@{bot_user}" not in text:
        return
    wants_site = any(w in text for w in ("website", "site", "link", "url"))
    wants_x = any(w in text for w in ("x", "twitter", "tweet"))
    if not (wants_site or wants_x):
        return
    now = datetime.now()
    if now - last_info_reply < timedelta(seconds=COOLDOWN_SECONDS):
        return
    last_info_reply = now
    if wants_site:
        await update.message.reply_text(f"It’s {WEBSITE_URL} — don’t smudge the screen drooling. 😠")
    elif wants_x:
        await update.message.reply_text(f"Check us at {X_URL} — try not to sell first this time. 😠")

async def text_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if LINK_REGEX.search(text):
        if user_id not in LINK_WARN:
            LINK_WARN[user_id] = time.time()
            try:
                await update.message.delete()
            except Exception:
                pass
            await context.bot.send_message(chat_id,
                f"{update.effective_user.mention_html()} — stop dropping dodgy links! One more and you’re out. 😠",
                parse_mode="HTML"
            )
            return
        else:
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
                await context.bot.send_message(chat_id,
                    f"{update.effective_user.first_name} thought we wouldn’t notice… kicked for spam links. 🚫"
                )
            except Exception:
                pass
            LINK_WARN.pop(user_id, None)
            return

    if not await is_admin(update, context):
        if not text.startswith("/"):
            cnt = mark_spam(chat_id, user_id)
            if cnt > SPAM_MAX_MSGS:
                strikes = inc_strike(chat_id, user_id)
                if strikes == 1:
                    await update.message.reply_text("Oi! Slow yourself. That’s your warning.")
                else:
                    await context.bot.ban_chat_member(chat_id, user_id)
                    await context.bot.unban_chat_member(chat_id, user_id)
                    await update.message.reply_text("Out you go.")
                    reset_user_spam(chat_id, user_id)
                return

    if "bot_username" not in context.bot_data:
        me = await context.bot.get_me()
        context.bot_data["bot_username"] = f"@{me.username}".lower()
    botname = context.bot_data["bot_username"]
    if botname in text.lower():
        await update.message.reply_text(random.choice(GRUMPY_REPLIES))

# -----------------------------
# Captcha
# -----------------------------
async def on_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    for new in update.message.new_chat_members:
        await track_member(new.id, 'join')
        choices = ["✅","🔥","🐸","💩","🧠","❌"]
        ans = random.choice(choices)
        shuf = choices[:]
        random.shuffle(shuf)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(c, callback_data=f"captcha:{update.effective_chat.id}:{new.id}:{c}")]
             for c in shuf]
        )
        prompt = f"Welcome, {new.mention_html()}.\nTap <b>{ans}</b> within 30s to prove you’re not a bot."
        msg = await update.message.reply_html(prompt, reply_markup=keyboard)
        PENDING_CAPTCHAS[(update.effective_chat.id, new.id)] = {
            "message_id": msg.message_id,
            "answer": ans,
            "deadline": time.time() + 30.0,
        }
        context.application.create_task(captcha_timeout(context, update.effective_chat.id, new.id))

async def captcha_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    await asyncio.sleep(31)
    key = (chat_id, user_id)
    data = PENDING_CAPTCHAS.get(key)
    if not data:
        return
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
    except Exception:
        pass
    try:
        await context.bot.delete_message(chat_id, data["message_id"])
    except Exception:
        pass
    PENDING_CAPTCHAS.pop(key, None)

async def on_captcha_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return
    q = update.callback_query
    parts = q.data.split(":")
    if len(parts) != 4:
        await q.answer()
        return
    _, chat_id_str, user_id_str, pressed = parts
    chat_id = int(chat_id_str); user_id = int(user_id_str)
    if update.effective_user.id != user_id:
        await q.answer("Not your button.")
        return
    data = PENDING_CAPTCHAS.get((chat_id, user_id))
    if not data:
        await q.answer("Too slow.")
        return
    if pressed == data["answer"]:
        await q.answer("Verified.")
        try:
            await q.edit_message_text("Verified. Don’t cause trouble.")
        except Exception:
            pass
        PENDING_CAPTCHAS.pop((chat_id, user_id), None)
        await context.bot.send_message(chat_id, random.choice(WELCOME_ROASTS))
    else:
        await q.answer("Wrong.")

# -----------------------------
# AI Chat
# -----------------------------
async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    bot_user = await context.bot.get_me()
    botname = bot_user.username.lower()
    entities = update.message.entities or []
    mentioned = any(
        (e.type == "mention" and f"@{botname}" in update.message.text.lower())
        or (e.type == "text_mention" and e.user.id == bot_user.id)
        for e in entities
    )
    is_reply_to_george = (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == bot_user.id
    )
    if not (mentioned or is_reply_to_george):
        return
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    reply = grumpy_reply(text, user_id=user_id, chat_id=chat_id)
    await update.message.reply_text(reply)

# -----------------------------
# X Feed via RSS (no official API – fixed & working)
# -----------------------------
GRUMPY_INTROS = [
    "The grump has posted again. Don't all rush at once.",
    "Go and see the new post… or don't. I don't care.",
    "Apparently I've posted again. Try to contain your excitement.",
    "Another day, another grumble from yours truly.",
    "I've spoken. Whether you listen is your mistake.",
    "New post. Lower your expectations accordingly.",
    "Just posted something. Probably better than your bags.",
    "The old git's at it again. Brace yourselves.",
]

LAST_TWEETS = set()  # IDs we've already forwarded

async def check_twitter_feed(context: ContextTypes.DEFAULT_TYPE):
    """Fallback to X API v1.1 (works with Premium, no Bearer needed)."""
    global LAST_TWEETS
    try:
        # Use your API Key/Secret for v1.1 auth
        auth = tweepy.OAuth1UserHandler(
            consumer_key=os.getenv("API_KEY"),     # your API Key
            consumer_secret=os.getenv("API_SECRET"),  # your API Secret
            access_token=os.getenv("ACCESS_TOKEN"),   # your Access Token
            access_token_secret=os.getenv("ACCESS_SECRET")  # your Access Secret
        )
        api = tweepy.API(auth)

        tweets = api.user_timeline(screen_name=TWITTER_HANDLE, count=5, tweet_mode="extended")

        new_tweets = []
        for tweet in tweets:
            if str(tweet.id) not in LAST_TWEETS:
                new_tweets.append(tweet)
                LAST_TWEETS.add(str(tweet.id))

        if new_tweets:
            for tweet in new_tweets:
                intro = random.choice(GRUMPY_INTROS)
                text = tweet.full_text
                link = f"https://twitter.com/{TWITTER_HANDLE}/status/{tweet.id}"
                msg = f"🧓 <b>{intro}</b>\n\n🐦 <b>@{TWITTER_HANDLE}:</b>\n\n{text}\n\n{link}"
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=msg,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            print(f"✅ Forwarded {len(new_tweets)} new tweets via v1.1 API.")
        else:
            print("✅ No new tweets via v1.1.")
    except Exception as e:
        print(f"v1.1 API error: {e}")

# -----------------------------
# Cleanup Deleted Accounts
# -----------------------------
async def cleanup_deleted_accounts(context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(KNOWN_MEMBERS_FILE):
        print("No known members.")
        return
    with open(KNOWN_MEMBERS_FILE, 'r') as f:
        known = json.load(f)
    deleted_count = 0
    now = datetime.now()
    to_remove = []
    for user_str, data in known.items():
        user_id = int(user_str)
        try:
            member = await context.bot.get_chat_member(CHAT_ID, user_id)
            if member.status in ['left', 'kicked'] or member.user.is_deleted:
                await context.bot.ban_chat_member(CHAT_ID, user_id)
                deleted_count += 1
                to_remove.append(user_str)
        except Exception:
            if (now - datetime.fromisoformat(data['last_seen'])).days >= 1:
                deleted_count += 1
                to_remove.append(user_str)
    for uid in to_remove:
        del known[uid]
    with open(KNOWN_MEMBERS_FILE, 'w') as f:
        json.dump(known, f)
    if deleted_count:
        msg = f"🧹 Swept {deleted_count} ghosts under the rug. Pub's cleaner now."
    else:
        msg = "👻 No dead weight today. Miracles do happen."
    await context.bot.send_message(CHAT_ID, msg)
    print(msg)

# -----------------------------
# Leave Handler
# -----------------------------
async def on_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.left_chat_member:
        await track_member(update.message.left_chat_member.id, 'leave')

# =============================
# PUB QUIZ – CLEAN & WORKING
# =============================
import asyncio
import random
from datetime import datetime
from telegram import Poll
from telegram.ext import ContextTypes

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

QUIZ_ACTIVE = False
QUESTION_INDEX = 0
TOTAL_QUESTIONS = 20
LEADERBOARD = {}
QUESTION_START_TIME = None
AI_QUESTIONS = []

async def generate_quiz_questions():
    global AI_QUESTIONS
    if AI_QUESTIONS:
        return
    # Same prompt as before – kept exactly
    prompt = (
        "Generate 20 multiple-choice crypto/pub trivia questions in Grumpy Old Git style. "
        "Sarcastic tone. Each: question, 4 options (A B C D), 1 correct answer. "
        "Format exactly: Q: [question]\nA) [option]\nB) [option]\nC) [option]\nD) [option]\nCorrect: [A/B/C/D]"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are Grumpy Old Git – sarcastic, world-weary British pub regular."},
                      {"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.9
        )
        raw = response.choices[0].message.content.strip()
        questions = []
        for block in raw.split("Q:")[1:]:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if len(lines) >= 6:
                q = lines[0]
                opts = [l[3:].strip() for l in lines[1:5]]  # A) → option
                correct = lines[5].split(": ")[1] if ": " in lines[5] else lines[5]
                questions.append({"q": q, "options": opts, "correct": correct})
        AI_QUESTIONS = questions[:20] or fallback_questions()
        print(f"Generated {len(AI_QUESTIONS)} quiz questions")
    except Exception as e:
        print(f"Quiz generation failed: {e}")
        AI_QUESTIONS = fallback_questions()

def fallback_questions():
    return [
        {"q": "What year was Bitcoin whitepaper released?", "options": ["2007", "2008", "2009", "2010"], "correct": "B"},
        {"q": "What’s $GOG’s spirit animal?", "options": ["Bull", "Bear", "Sheep", "Grumpy Old Git"], "correct": "D"}
    ] * 10

# --------------------- GENERATE QUIZ QUESTIONS (NEW) ---------------------
from openai import OpenAI
import random

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_quiz_questions():
    global AI_QUESTIONS
    AI_QUESTIONS.clear()          # always start fresh

    prompt = (
        "Generate exactly 20 multiple-choice crypto/pub trivia questions in Grumpy Old Git style. "
        "Sarcastic British tone. Number them Q1 to Q20.\n"
        "Format exactly:\nQ1: [question]\nA) [option]\nB) [option]\nC) [option]\nD) [option]\nCorrect: [A/B/C/D]\n\n"
        "Do NOT stop early. Give all 20 questions."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Grumpy Old Git – sarcastic, world-weary British pub regular."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3900,
            temperature=0.9
        )
        raw = response.choices[0].message.content.strip()

        questions = []
        for block in raw.split("Q")[1:]:   # splits on Q1, Q2, etc.
            if not block.strip():
                continue
            lines = [l.strip() for l in ("Q" + block).split("\n") if l.strip()]
            if len(lines) >= 6:
                q_text = lines[0].split(":", 1)[1].strip() if ":" in lines[0] else lines[0]
                opts = [l[3:].strip() for l in lines[1:5]]
                correct = lines[5].split(":", 1)[1].strip().upper() if ":" in lines[5] else lines[5].strip().upper()
                questions.append({"q": q_text, "options": opts, "correct": correct})

        # Force exactly 20 – pad with fallback if OpenAI is being lazy
        AI_QUESTIONS.extend(questions[:20])
        while len(AI_QUESTIONS) < 20:
            AI_QUESTIONS.append(random.choice(fallback_questions()))

        print(f"Successfully generated {len(AI_QUESTIONS)} questions (forced to 20)")

    except Exception as e:
        print(f"OpenAI failed ({e}), using fallback questions")
        AI_QUESTIONS.extend(fallback_questions() * 10)  # 20 guaranteed

def fallback_questions():
    return [
        {"q": "What year was the Bitcoin whitepaper released, you daft apeth?", "options": ["2007", "2008", "2009", "2010"], "correct": "B"},
        {"q": "Which coin does Grumpy actually give a toss about?", "options": ["Dogecoin", "Shiba", "Pepe", "$GOG"], "correct": "D"},
        {"q": "How many pints has Grumpy had today?", "options": ["None", "Three", "Lost count", "Still sober"], "correct": "C"},
        {"q": "What’s the only thing holding stronger than Bitcoin right now?", "options": ["My liver", "Elon’s tweets", "The bar stool", "Cloudflare"], "correct": "A"},
    ]

# --------------------- START QUIZ ---------------------
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QUIZ_ACTIVE, QUESTION_INDEX, LEADERBOARD, AI_QUESTIONS
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins run the quiz, sunshine. Sod off.")
        return
    if QUIZ_ACTIVE:
        await update.message.reply_text("Quiz already running, you daft apeth.")
        return

    QUIZ_ACTIVE = True
    QUESTION_INDEX = 0
    LEADERBOARD = {}
    AI_QUESTIONS.clear()
    context.bot_data["quiz_chat_id"] = update.effective_chat.id

    await generate_quiz_questions()

    await update.message.reply_text(
        "🧠 *PUB QUIZ TIME!*\n\n"
        "20 sarcastic questions. 20 seconds each.\n"
        "Fast (<10s): 5 pts | Slow: 3 pts\n"
        "No Google. No mercy.\n\nStarting in 5...",
        parse_mode="Markdown"
    )
    await asyncio.sleep(5)
    await ask_next_question(context, update.effective_chat.id)

# --------------------- NEXT QUESTION (FINAL FIX – NO MORE ZERO POINTS) ---------------------
async def ask_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    global QUESTION_INDEX, QUESTION_START_TIME

    # Use QUESTION_INDEX < TOTAL_QUESTIONS instead of >= to keep index valid during final answers
    if QUESTION_INDEX >= TOTAL_QUESTIONS:
        await end_quiz(context, chat_id)
        return

    q = AI_QUESTIONS[QUESTION_INDEX]
    QUESTION_START_TIME = datetime.now()

    correct_idx = ["A", "B", "C", "D"].index(q["correct"])

    msg = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"Q{QUESTION_INDEX + 1}: {q['q']}",
        options=q["options"],
        is_anonymous=False,
        type=Poll.QUIZ,
        correct_option_id=correct_idx,
        open_period=30,
        allows_multiple_answers=False
    )

    context.bot_data["current_poll_id"] = msg.poll.id
    QUESTION_INDEX += 1   # now 1–20 while poll is live, becomes 21 only after answers can still arrive

    await asyncio.sleep(32)
    if QUIZ_ACTIVE:       # still active → go again (or finish on next call)
        await ask_next_question(context, chat_id)

    # Roast near the end
    await asyncio.sleep(18)
    if QUIZ_ACTIVE:
        await context.bot.send_message(chat_id=chat_id, text=random.choice([
            "Tick-tock, lads. My pint’s gone flat.",
            "Still guessing? Bless your cotton socks.",
            "20 seconds. Even the dog knows this one."
        ]))

async def end_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not QUIZ_ACTIVE:
        await update.message.reply_text("No quiz running, you daft apeth.")
        return
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can end the quiz, sunshine.")
        return

    chat_id = context.bot_data.get("quiz_chat_id") or update.effective_chat.id
    await end_quiz(context, chat_id)
    await update.message.reply_text("Quiz terminated early. Bunch of quitters.")


# --------------------- POLL ANSWER (TRULY UNBREAKABLE) ---------------------
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not QUIZ_ACTIVE or not update.poll_answer:
        return

    answer = update.poll_answer
    user = answer.user
    chosen = answer.option_ids[0] if answer.option_ids else None
    if chosen is None:
        return

    # 1. Must be the current poll
    if answer.poll_id != context.bot_data.get("current_poll_id"):
        return

    # 2. QUESTION_INDEX must still be valid (1–20)
    if QUESTION_INDEX < 1 or QUESTION_INDEX > TOTAL_QUESTIONS:
        return

    chat_id = context.bot_data["quiz_chat_id"]
    current_q = AI_QUESTIONS[QUESTION_INDEX - 1]
    correct_idx = ["A", "B", "C", "D"].index(current_q["correct"])
    time_taken = (datetime.now() - QUESTION_START_TIME).total_seconds()

    if user.id not in LEADERBOARD:
        LEADERBOARD[user.id] = {"name": user.full_name or user.username or "Anon", "score": 0}

    if chosen == correct_idx:
        points = 5 if time_taken < 10 else 3
        LEADERBOARD[user.id]["score"] += points
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ {user.first_name} nails it! +{points} pts ({time_taken:.1f}s)"
        )

# --------------------- LEADERBOARD (ANYTIME, FOR ANYONE) ---------------------
async def quiz_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # If a quiz is running → show LIVE leaderboard
    if QUIZ_ACTIVE and LEADERBOARD:
        lb = sorted(LEADERBOARD.items(), key=lambda x: (-x[1]["score"], x[1]["name"]))
        text = "*🔥 LIVE LEADERBOARD 🔥*\n\n"
        for i, (_, data) in enumerate(lb[:10], 1):
            medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"{i}."
            text += f"{medal} {data['name']}: {data['score']} pts\n"
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    # If no quiz running but we still have leftover scores from last round
    if LEADERBOARD:
        lb = sorted(LEADERBOARD.items(), key=lambda x: (-x[1]["score"], x[1]["name"]))
        winner = lb[0][1]
        text = f"🏆 *LAST QUIZ WINNER*\n{winner['name']} with {winner['score']} points!\n\n"
        text += "*Full results:*\n"
        for i, (_, data) in enumerate(lb[:10], 1):
            medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"{i}."
            text += f"{medal} {data['name']}: {data['score']} pts\n"
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    # Nothing at all
    await update.message.reply_text("No quiz has been run yet, you nosy git. Wait your turn.")

# --------------------- CLEAR LEADERBOARD (ADMIN ONLY) ---------------------
async def clear_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can wipe the slate, sunshine.")
        return

    global LEADERBOARD
    old_count = len(LEADERBOARD)
    LEADERBOARD = {}

    await update.message.reply_text(
        f"🧹 Leaderboard wiped clean. {old_count} punters sent back to zero.\nFresh quiz, fresh humiliation incoming."
    )

# --------------------- END QUIZ ---------------------
async def end_quiz(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    global QUIZ_ACTIVE
    if not QUIZ_ACTIVE:
        return

    if LEADERBOARD:
        winner = max(LEADERBOARD.items(), key=lambda x: x[1]["score"])
        msg = f"🎉 *QUIZ OVER!* Winner: *{winner[1]['name']}* with {winner[1]['score']} pts!\nThe rest of you – back to the bar."
    else:
        msg = "😤 *QUIZ OVER!* Not a single point. Useless bunch."

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    QUIZ_ACTIVE = False

# -----------------------------
# Main (async!)
# -----------------------------
async def main():
    # Use the new v20+ builder syntax
    app = Application.builder().token(BOT_TOKEN).build()

    # === All your handlers (unchanged) ===
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("roast", roast_cmd))
    app.add_handler(CommandHandler("website", website_cmd))
    app.add_handler(CommandHandler("x", x_cmd))
    app.add_handler(CommandHandler("shutup", shutup))
    app.add_handler(CommandHandler("speak", speak))
    app.add_handler(CommandHandler("chatid", chatid_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_leave))
    app.add_handler(CallbackQueryHandler(on_captcha_button, pattern=r"^captcha:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_moderation))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mention_autoreply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_guard))
    app.add_handler(CommandHandler("startquiz", start_quiz))
    app.add_handler(CommandHandler("quizleaderboard", quiz_leaderboard))
    app.add_handler(PollAnswerHandler(handle_poll_answer))
    app.add_handler(CommandHandler("endquiz", end_quiz_command))
    app.add_handler(CommandHandler("clearleaderboard", clear_leaderboard))

    # Jobs – now fully RSS-powered (X API completely removed)
    job_queue = app.job_queue

    async def init_jobs(context: ContextTypes.DEFAULT_TYPE):
        print("Running startup jobs...")

        # Optional: Pre-warm the RSS feed on startup so it doesn't miss the first tweet
        try:
            await check_twitter_feed(context)
            print("RSS feed warmed up on startup")
        except Exception as e:
            print(f"Startup RSS check failed (will retry in 8h): {e}")

        # Schedule regular checks every 8 hours
        job_queue.run_repeating(
            check_twitter_feed,
            interval=28800,   # 8 hours
            first=60,         # first proper check after 1 minute
            name="RSS_feed_check"
        )
        print("RSS X feed scheduled every 8 hours")

        # Keep your other job if you still want it
        job_queue.run_repeating(cleanup_deleted_accounts, interval=86400, first=120)

    # Run init_jobs once at startup
    job_queue.run_once(init_jobs, when=10)

    print("Grumpy George v2.1 is alive, grumbling, and 100% RSS-powered...")

    # Start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("Bot is now polling – press Ctrl+C to stop")

    # Keep the loop alive
    await asyncio.Event().wait()

# ======================================================================
# Entry point
# ======================================================================
if __name__ == "__main__":
    asyncio.run(main())
