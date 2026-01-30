# =================================================
# ——— GEORGE'S PUB SONG COMMAND (REQUEST MODE) ———
# Punters request a song, George grumbles, half-hums,
# then sends a YouTube link. No pre-set playlist.
# =================================================

import random
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone

# Globals for cooldown (global limit)
SONG_COUNT = 0
LAST_SONG_TIME = None
MAX_SONGS = 3
COOLDOWN_MINUTES = 10

# Setup function (called from main)
def setup_pubsong(globals_dict):
    global speak_george, grok_chat
    speak_george = globals_dict["speak_george"]
    grok_chat = globals_dict["grok_chat"]

# -------------------------------------------------
# /pubsong command — accepts song request
# -------------------------------------------------
async def pubsong_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SONG_COUNT, LAST_SONG_TIME
    now = datetime.now(timezone.utc)

    # Cooldown reset check
    if LAST_SONG_TIME and (now - LAST_SONG_TIME).total_seconds() / 60 >= COOLDOWN_MINUTES:
        SONG_COUNT = 0

    # Global limit check
    if SONG_COUNT >= MAX_SONGS:
        minutes_left = COOLDOWN_MINUTES - int((now - LAST_SONG_TIME).total_seconds() / 60)
        await update.message.reply_text(
            f"Three songs is the pub limit. Wait {minutes_left} minutes, you greedy sods."
        )
        return

    chat_id = update.effective_chat.id

    # Get requested song from args
    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Oi, you tone-deaf twat — give me a song! Like: /pubsong AC/DC Highway to Hell"
        )
        return

    song_query = " ".join(context.args)

    # George grumbles about the request (Grok makes it funny)
    grumble_prompt = (
        f"You are Grumpy George, a grumpy old British pub landlord.\n"
        f"Some mug just requested '{song_query}' on the jukebox.\n"
        f"Grumble about why this song is rubbish, try to hum the opening very badly WITHOUT using real lyrics, "
        f"then give up and tell them to play it themselves.\n"
        f"Be funny, sarcastic, under 60 words, no swearing."
    )

    try:
        grumble = await grok_chat(
            [{"role": "user", "content": grumble_prompt}],
            temperature=0.9
        )
        text = grumble.strip()
    except Exception as e:
        print(f">>> PUBSONG GROK FAILED: {e}")
        text = f"Bloody '{song_query}'? I tried humming it once and my ears filed for divorce. Play it yourself, you tone-deaf prat."

    # Speak the grumble (ElevenLabs)
    try:
        await speak_george(
            text=text,
            chat_id=chat_id,
            context=context
        )
    except Exception as e:
        print(f">>> PUBSONG TTS FAILED: {e}")
        await context.bot.send_message(chat_id=chat_id, text=text)

    # Find YouTube link (Grok searches)
    search_prompt = (
        f"Search YouTube for the official audio or music video of '{song_query}' by the original artist. "
        f"Return ONLY the clean YouTube URL, nothing else. "
        f"If you can't find it, return a Rick Roll."
    )

    try:
        url = await grok_chat(
            [{"role": "user", "content": search_prompt}],
            temperature=0.3
        )
        url = url.strip()
        if not url.startswith("https://www.youtube.com/"):
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll fallback
    except:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll fallback

    # Drop the link
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Here, you whinging git — {url}",
        disable_web_page_preview=False
    )

    # Update request count
    SONG_COUNT += 1
    LAST_SONG_TIME = now
