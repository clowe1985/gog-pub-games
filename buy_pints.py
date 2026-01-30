# buy_pints.py — /buypint command, drunk George, dead-chat rumours, the lot
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import random
import asyncio
from datetime import datetime, timedelta, timezone

rumour_lock = asyncio.Lock()

PINTS_DRANK = 0
LAST_MESSAGE_TIME = datetime.now(timezone.utc)
RUMOUR_TARGET = None
RUMOUR_PINTS = 0
RUMOUR_CLUES = []
RUMOUR_GUESSED = False
DEAD_CHAT_THRESHOLD = 60 * 60
RUMOUR_PINT_WINDOW = 120
CLUE_INTERVAL = 20
RECENT_ACTIVE_USERS = []
LAST_RUMOUR_START = None

# ---------------- HELPERS ----------------
def touch_chat_activity():
    global LAST_MESSAGE_TIME
    LAST_MESSAGE_TIME = datetime.now(timezone.utc)

def reset_rumour():
    global RUMOUR_ACTIVE, RUMOUR_TARGET, RUMOUR_CLUES
    global RUMOUR_PINTS, RUMOUR_GUESSED, RUMOUR_WINDOW_END

    RUMOUR_ACTIVE = False
    RUMOUR_TARGET = None
    RUMOUR_CLUES = []
    RUMOUR_PINTS = 0
    RUMOUR_GUESSED = False
    RUMOUR_WINDOW_END = None

def setup_pints_globals(wallets_dict, pint_wallet_addr, chat_id_const, speak_func, grok_func, send_func, mega_active_global):
    global WALLETS, PINT_WALLET, CHAT_ID, speak_george, grok_chat, send_native_shido, MEGA_ACTIVE
    WALLETS = wallets_dict
    PINT_WALLET = pint_wallet_addr
    CHAT_ID = chat_id_const
    speak_george = speak_func
    grok_chat = grok_func
    send_native_shido = send_func
    MEGA_ACTIVE = mega_active_global

def add_active_user(user_id: int):
    global RECENT_ACTIVE_USERS
    if user_id not in RECENT_ACTIVE_USERS:
        RECENT_ACTIVE_USERS.append(user_id)
    RECENT_ACTIVE_USERS = RECENT_ACTIVE_USERS[-50:]

def is_rumour_guess(update, context):
    if not RUMOUR_ACTIVE or RUMOUR_GUESSED:
        return False

    msg = update.message
    if not msg or not msg.reply_to_message:
        return False

    return (
        msg.reply_to_message.message_id
        == context.bot_data.get("rumour_clue_msg_id")
    )

# ---------- /buypint COMMAND ----------
async def buypint_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PINTS_DRANK, RUMOUR_ACTIVE, RUMOUR_PINTS, RUMOUR_WINDOW_END, LAST_MESSAGE_TIME

    if update.effective_chat.type != "supergroup":
        await update.message.reply_text("Only works in the main group, you daft sod.")
        return

    user = update.effective_user
    args = context.args
    try:
        pints = int(args[0]) if args else 1
        if pints < 1 or pints > 20:
            raise ValueError
    except:
        await update.message.reply_text("Usage: /buypint <number> (1-20)\nOr just /buypint for 1")
        return

    user_id = str(user.id)
    wallet = WALLETS.get(user_id)
    if not wallet or not wallet.get("pk") or wallet.get("pk") == "HIDDEN":
        await update.message.reply_text("You need a wallet with stored private key first, mate. Use /start in DMs.")
        return

    amount_shido = pints * 1000 * 10**18
    success = await send_native_shido(wallet["pk"], PINT_WALLET, amount_shido)

    if not success:
        await update.message.reply_text("Not enough SHIDO or transaction failed. Try again, you skint git.")
        return

    PINTS_DRANK += pints
    LAST_MESSAGE_TIME = datetime.now(timezone.utc)

    username = user.username or user.first_name or "Legend"

    # Drunk level for the announcement
    if PINTS_DRANK <= 4:
        level = "cheerful"
    elif PINTS_DRANK <= 9:
        level = "tipsy"
    elif PINTS_DRANK <= 14:
        level = "pissed"
    else:
        level = "legless"

    base_text = f"@{username} just bought George {pints} pint{'s' if pints > 1 else ''}! George is now {level}..."
    prompt = f"Rewrite as a short, savage, drunk grumpy old British pub landlord voice line. He's {level}. Max 40 words: \"{base_text}\""
    try:
        grumpy_text = await grok_chat([{"role": "user", "content": prompt}], temperature=0.95)
        grumpy_text = grumpy_text.strip() or base_text
    except:
        grumpy_text = base_text

    await speak_george(grumpy_text, CHAT_ID, context=context)

    if not RUMOUR_ACTIVE:
        await update.message.reply_text(f"Cheers, {username}! {pints} pints sent. George is getting louder...")

    if RUMOUR_ACTIVE:
        RUMOUR_PINTS += pints
        print(f">>> RUMOUR ACTIVE: {RUMOUR_ACTIVE} — ADDING {pints} PINTS — TOTAL {RUMOUR_PINTS + pints}")
        if RUMOUR_PINTS >= 1:

            await start_rumour(context)

# ---------------- START RUMOUR ----------------
async def start_rumour(context: ContextTypes.DEFAULT_TYPE):
    async with rumour_lock:
        if MEGA_ACTIVE:
            print(">>> RUMOUR BLOCKED — QUIZ RUNNING")
            reset_rumour()
            return

        print(f">>> START_RUMOUR CALLED - PINTS: {RUMOUR_PINTS}")

        global RUMOUR_TARGET, RUMOUR_CLUES, RUMOUR_ACTIVE, RUMOUR_GUESSED

        if RUMOUR_PINTS <= 0:
            await speak_george(
                "No pints? Miserable lot. I'll keep me mouth shut this time.",
                CHAT_ID,
                context=context
            )
            reset_rumour()
            return

        RUMOUR_TARGET = choose_rumour_target()
        if not RUMOUR_TARGET:
            reset_rumour()
            return

        # Only send intro ONCE
        await speak_george(
            "Right… I've heard things. Nasty little whispers. "
            "Let's see if you lot can work it out.",
            CHAT_ID,
            context=context
        )

        RUMOUR_CLUES = await generate_rumour_clues(RUMOUR_TARGET, RUMOUR_PINTS)

        # Drop clues one by one — no duplicates
        context.bot_data["rumour_clue_msg_id"] = None
        for i, clue in enumerate(RUMOUR_CLUES):
            if RUMOUR_GUESSED:
                return
            msg = await speak_george(
                clue,
                CHAT_ID,
                context=context,
                return_message=True
            )
            # Only first clue is guessable
            if i == 0 and msg:
                context.bot_data["rumour_clue_msg_id"] = msg.message_id
            await asyncio.sleep(CLUE_INTERVAL)

        # Nobody guessed
        if not RUMOUR_GUESSED:
            reveal = (
                f"You lot are thick as mince. "
                f"It was @{RUMOUR_TARGET['username']} all along."
                if RUMOUR_TARGET.get("username")
                else f"It was {RUMOUR_TARGET['name']}."
            )
            await speak_george(reveal, CHAT_ID, context=context)

        reset_rumour()

# ---------------- TARGET SELECTION ----------------
def choose_rumour_target():
    if not RECENT_ACTIVE_USERS:
        return None

    return random.choice(RECENT_ACTIVE_USERS)

# ---------------- CLUE GENERATION ----------------
async def generate_rumour_clues(target, pints):
    clues = []
    name_hint = target.get("name", "some mug").split()[0]  # first name only
    username_hint = target.get("username", "that nameless git")

    # Base clue — always free
    clues.append("Never buys a round but always has an opinion.")

    # 3+ pints — tipsy, cheeky
    if pints >= 3:
        clues.append("Thinks they're the cleverest in the pub but couldn't pour piss out of a boot.")

    # 5+ pints — pissed, personal
    if pints >= 5:
        clues.append(f"Goes by {name_hint} — probably thinks it's a proper name.")

    # 7+ pints — legless, brutal
    if pints >= 7:
        clues.append("Profile pic's older than my ex-wife's grudges.")

    # 10+ pints — barely coherent, almost giveaway
    if pints >= 10:
        clues.append(f"Username starts with '@{username_hint[0]}' — figure it out, you thick sods.")

    # 15+ pints — George regrets everything
    if pints >= 15:
        clues.append(f"Fine, it's @{username_hint}. Happy now, you greedy bastards?")

    return clues[:4]  # max 4 clues, keeps it moving

# ---------------- MESSAGE GUESS HOOK ----------------
async def rumour_guess_hook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RUMOUR_GUESSED

    if not RUMOUR_ACTIVE or RUMOUR_GUESSED or not RUMOUR_TARGET:
        return

    if not update.message or not update.message.text:
        return

    # Must be reply to George's first clue
    reply = update.message.reply_to_message
    if not reply:
        return

    if reply.message_id != context.bot_data.get("rumour_clue_msg_id"):
        return

    text = update.message.text.lower()

    username = RUMOUR_TARGET.get("username")
    if username and f"@{username.lower()}" in text:
        await rumour_win(update, context)

# ---------------- WIN HANDLER ----------------
async def rumour_win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RUMOUR_GUESSED

    RUMOUR_GUESSED = True
    winner = update.effective_user.username or update.effective_user.first_name

    await speak_george(
        f"Well I'll be buggered… {winner} clocked it. "
        f"It was {RUMOUR_TARGET['name']} all along.",
        CHAT_ID,
        context=context
    )

    reset_rumour()
