import urllib.request
import urllib.parse
import json
import logging
import time
import hmac
import hashlib
import base64
import secrets
from config import (
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN, TWITTER_SEARCH_QUERIES,
    MAX_TWITTER_ACTIONS_PER_DAY, DRY_RUN
)
from database import is_item_seen, mark_item_seen, record_action, get_action_count_today
from content_engine import generate_twitter_reply, generate_twitter_post

logger = logging.getLogger("CTRLX.Social.Twitter")

class TwitterBot:
    def __init__(self):
        pass

    def is_configured(self) -> bool:
        return bool(
            TWITTER_API_KEY and TWITTER_API_SECRET and
            TWITTER_ACCESS_TOKEN and TWITTER_ACCESS_SECRET
        )

    def _build_oauth1_header(self, method: str, url: str, params: dict = None) -> str:
        oauth_params = {
            "oauth_consumer_key": TWITTER_API_KEY,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": TWITTER_ACCESS_TOKEN,
            "oauth_version": "1.0"
        }

        all_params = {}
        all_params.update(oauth_params)
        if params:
            all_params.update(params)

        sorted_params = sorted(all_params.items())
        param_str = "&".join(f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params)
        base_string = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"

        signing_key = f"{urllib.parse.quote(TWITTER_API_SECRET, safe='')}&{urllib.parse.quote(TWITTER_ACCESS_SECRET, safe='')}".encode("utf-8")
        signature = base64.b64encode(hmac.new(signing_key, base_string.encode("utf-8"), hashlib.sha1).digest()).decode("utf-8")
        oauth_params["oauth_signature"] = signature

        parts = [f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"' for k, v in sorted(oauth_params.items())]
        return "OAuth " + ", ".join(parts)

    def search_tweets(self, query: str, limit: int = 10) -> list:
        if not TWITTER_BEARER_TOKEN:
            if DRY_RUN:
                logger.info(f"[SIMULATION] Mode sans cles pour la requete '{query}' (renseignez TWITTER_BEARER_TOKEN pour l'API reelle)")
                return [
                    {
                        "id": f"sim_tweet_{abs(hash(query)) % 100000}",
                        "text": f"Je viens de deployer mon side project dev en prod, preneur de vos avis techniques",
                        "author_id": "tech_creator_fr"
                    }
                ]
            return []

        url = f"https://api.twitter.com/2/tweets/search/recent?query={urllib.parse.quote(query)}&max_results={max(10, min(100, limit))}&tweet.fields=author_id,created_at,text"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
                "User-Agent": "CTRLXGrowth/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("data", [])
        except Exception as e:
            logger.warning(f"Twitter search error for query '{query}': {e}")
            return []

    def post_tweet(self, text: str, in_reply_to_tweet_id: str = None) -> bool:
        if DRY_RUN or not self.is_configured():
            target_info = f" in reply to {in_reply_to_tweet_id}" if in_reply_to_tweet_id else ""
            logger.info(f"[DRY RUN] Would post Tweet{target_info}: {text}")
            return True

        url = "https://api.twitter.com/2/tweets"
        payload = {"text": text}
        if in_reply_to_tweet_id:
            payload["reply"] = {"in_reply_to_tweet_id": str(in_reply_to_tweet_id)}

        auth_header = self._build_oauth1_header("POST", url)
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
                "User-Agent": "CTRLXGrowth/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                tweet_id = res.get("data", {}).get("id")
                return bool(tweet_id)
        except Exception as e:
            logger.error(f"Twitter post error: {e}")
            return False

    def scan_and_reply_cycle(self) -> int:
        daily_actions = get_action_count_today("twitter")
        if daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
            logger.info(f"Twitter daily limit reached ({daily_actions}/{MAX_TWITTER_ACTIONS_PER_DAY})")
            return 0

        replies_count = 0
        for query in TWITTER_SEARCH_QUERIES:
            if replies_count + daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
                break

            tweets = self.search_tweets(query, limit=10)
            for tweet in tweets:
                t_id = tweet["id"]
                if is_item_seen("twitter", t_id):
                    continue

                text = tweet.get("text", "")
                author_id = tweet.get("author_id", "")

                reply_text = generate_twitter_reply(text, author_id)
                success = self.post_tweet(reply_text, in_reply_to_tweet_id=t_id)
                status = "success" if success else "failed"

                record_action(
                    platform="twitter",
                    action_type="reply",
                    target_id=t_id,
                    target_url=f"https://x.com/i/status/{t_id}",
                    content=reply_text,
                    status=status
                )
                mark_item_seen("twitter", t_id, author_id, text[:150], f"https://x.com/i/status/{t_id}")
                replies_count += 1
                time.sleep(2)
                break

        return replies_count

    def publish_original_tweet(self) -> bool:
        daily_actions = get_action_count_today("twitter")
        if daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
            return False

        content = generate_twitter_post()
        success = self.post_tweet(content)
        record_action(
            platform="twitter",
            action_type="original_post",
            target_id="self",
            target_url="",
            content=content,
            status="success" if success else "failed"
        )
        return success
