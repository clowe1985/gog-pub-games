# twitter_watcher.py
import json
import os
import urllib.parse
import httpx
from datetime import datetime

# CHANGE THESE TO MATCH YOUR MAIN SCRIPT
TWITTER_BEARER = os.getenv("TWITTER_BEARER")
TWITTER_ACCOUNT_ID = "1971588070941315072"  # OfficialGOGCoin
CHAT_ID = -1003155680202
LAST_TWEET_FILE = "/root/gog_bot/last_tweet_id.json"

# Load last seen tweet ID (survives restarts!)
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

async def check_twitter(bot):
    global last_tweet_id
    last_tweet_id = load_last_tweet_id()
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
            if not last_tweet_id or int(tid) > int(last_tweet_id):
                if not new_latest:
                    new_latest = tid
                # Inside the tweet loop — replace the old msg with this:
                roast_prompt = (
                    f"Grumpy old British git just saw this $GOG tweet. "
                    f"Give a short, savage, sarcastic voice roast (max 25 words): "
                    f'"{tweet["text"]}"'
                )
                try:
                    roast = await grok_chat([{"role": "user", "content": roast_prompt}], temperature=0.95)
                    roast = roast.strip() if roast else "Another tweet. Brilliant."
                except:
                    roast = "George saw the tweet. He’s not impressed."
                await asyncio.sleep(3)  # let him breathe between tweets
        if new_latest:
            save_last_tweet_id(new_latest)
            print(f">>> Saved last_tweet_id: {new_latest}")
    except Exception as e:
        print(f">>> Twitter checker crashed: {e}")
