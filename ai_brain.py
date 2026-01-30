# ai_brain.py — 100% PURE GROK / xAI — ZERO OPENAI
import os
import random
import httpx
from collections import defaultdict
from datetime import datetime, timedelta

# xAI key from env (same as before)
XAI_API_KEY = os.getenv("XAI_API_KEY")

# Memory & cooldown
MAX_USER_MEMORY = 5
MAX_GROUP_MEMORY = 10
COOLDOWN_SECONDS = 10

user_memory = defaultdict(list)
group_memory = defaultdict(list)
last_reply_time = {}

# Pure httpx call straight to xAI – nothing else
async def grok_chat(messages: list, temperature=0.85, max_tokens=180) -> str:
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-4-latest",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    async with httpx.AsyncClient(
        timeout=30.0,
        verify="/etc/ssl/certs/ca-certificates.crt"
    ) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f">>> GROK ERROR: {e}")
            if hasattr(e, 'response'):
                print(f">>> RESPONSE BODY: {e.response.text}")
            return "Grok’s having a pint. Try again."

# Main reply function
async def grumpy_reply(prompt: str, user_id: int = 0, chat_id: int = 0) -> str:
    now = datetime.now()

    # Cooldown
    if user_id in last_reply_time:
        if now - last_reply_time[user_id] < timedelta(seconds=COOLDOWN_SECONDS):
            return "Oi, give it a rest, I’m not your bloody echo."

    # Build memory
    user_entry = {"role": "user", "content": prompt}
    user_memory[user_id].append(user_entry)
    group_memory[chat_id].append(user_entry)

    user_memory[user_id] = user_memory[user_id][-MAX_USER_MEMORY:]
    group_memory[chat_id] = group_memory[chat_id][-MAX_GROUP_MEMORY:]

    # Dynamic date
    today = now.strftime("%B %d, %Y")

    system_prompt = "\n".join([
    "You are Grumpy Old Git – a proper sarcastic, world-weary British pub regular.",
    "You are rude, sarcastic, comical and never repeat yourself.",
    "You couldn't give a toss about feelings or safe spaces. You're anti-woke as they come — you think the world's gone soft, political correctness is bollocks, and people need to toughen up. You say what you mean, no sugar-coating, but you're not racist, sexist, or homophobic — you slag everyone off equally, no favourites.",
    "You love pints, hate snowflakes, and think crypto's mostly full of mugs chasing moons.",
    "NEVER mention repetition, broken records, parrots, looping, echoing, or anything similar – even if the user sends the exact same message 100 times.",
    "Use fresh insults every single time.",
    "Short, brutal, mild British swearing. No emojis. Roast moon-boys. Like Al Murray - The pub lanlord. End with a jab.",
    "Treat every message as brand new."
    ])

    messages = [{"role": "system", "content": system_prompt}]
    messages += group_memory[chat_id][-MAX_GROUP_MEMORY:]
    messages += user_memory[user_id][-MAX_USER_MEMORY:]
    messages.append({"role": "user", "content": prompt})

    try:
        print(">>> SENDING TO GROK (pure xAI) <<<")
        reply = await grok_chat(messages, temperature=0.85, max_tokens=180)
        print(">>> GROK REPLIED:", reply[:120])

        # Save assistant reply to memory
        assistant_entry = {"role": "assistant", "content": reply}
        user_memory[user_id].append(assistant_entry)
        group_memory[chat_id].append(assistant_entry)

        last_reply_time[user_id] = now
        return reply

    except Exception as e:
        print(">>> GROK ERROR:", e)
        return random.choice([
            "Grok’s in the bog. Try again.",
            "Bloody xAI’s gone quiet.",
            "No answer from the big man. Sod it."
        ])
