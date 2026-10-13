import urllib.request
import urllib.parse
import json
import base64
import logging
import time
from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
    REDDIT_USERNAME, REDDIT_PASSWORD,
    REDDIT_USER_AGENT, MONITORED_SUBREDDITS,
    MAX_REDDIT_ACTIONS_PER_DAY, DRY_RUN
)
from database import is_item_seen, mark_item_seen, record_action, get_action_count_today
from content_engine import generate_reddit_reply, generate_reddit_post

logger = logging.getLogger("CTRLX.Social.Reddit")

class RedditBot:
    def __init__(self):
        self.access_token = None
        self.token_expiry = 0

    def is_configured(self) -> bool:
        return bool(REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET and REDDIT_USERNAME and REDDIT_PASSWORD)

    def get_token(self) -> str | None:
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        if not self.is_configured():
            return None

        auth_str = f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        data = urllib.parse.urlencode({
            "grant_type": "password",
            "username": REDDIT_USERNAME,
            "password": REDDIT_PASSWORD
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://www.reddit.com/api/v1/access_token",
            data=data,
            headers={
                "Authorization": f"Basic {b64_auth}",
                "User-Agent": REDDIT_USER_AGENT
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                self.access_token = res.get("access_token")
                expires_in = int(res.get("expires_in", 3600))
                self.token_expiry = time.time() + expires_in - 60
                return self.access_token
        except Exception as e:
            logger.error(f"Reddit token error: {e}")
            return None

    def fetch_new_posts(self, subreddit: str, limit: int = 10) -> list:
        token = self.get_token()
        headers = {"User-Agent": REDDIT_USER_AGENT}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            url = f"https://oauth.reddit.com/r/{subreddit}/new?limit={limit}"
        else:
            url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                children = data.get("data", {}).get("children", [])
                posts = []
                for child in children:
                    cdata = child.get("data", {})
                    posts.append({
                        "id": cdata.get("name") or f"t3_{cdata.get('id')}",
                        "raw_id": cdata.get("id"),
                        "title": cdata.get("title", ""),
                        "selftext": cdata.get("selftext", ""),
                        "author": cdata.get("author", ""),
                        "permalink": f"https://reddit.com{cdata.get('permalink', '')}",
                        "subreddit": subreddit
                    })
                return posts
        except Exception as e:
            logger.warning(f"Error fetching r/{subreddit}: {e}")
            return []

    def reply_to_post(self, parent_fullname: str, comment_text: str) -> bool:
        if DRY_RUN or not self.is_configured():
            logger.info(f"[DRY RUN] Would reply to Reddit post {parent_fullname}: {comment_text}")
            return True

        token = self.get_token()
        if not token:
            return False

        data = urllib.parse.urlencode({
            "api_type": "json",
            "thing_id": parent_fullname,
            "text": comment_text
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://oauth.reddit.com/api/comment",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": REDDIT_USER_AGENT
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                errors = res.get("json", {}).get("errors", [])
                if errors:
                    logger.error(f"Reddit reply error: {errors}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Failed to post Reddit comment: {e}")
            return False

    def create_post(self, subreddit: str, title: str, body: str) -> bool:
        if DRY_RUN or not self.is_configured():
            logger.info(f"[DRY RUN] Would create Reddit submission in r/{subreddit}:\nTitle: {title}\nBody:\n{body}")
            return True

        token = self.get_token()
        if not token:
            return False

        data = urllib.parse.urlencode({
            "api_type": "json",
            "kind": "self",
            "sr": subreddit,
            "title": title,
            "text": body
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://oauth.reddit.com/api/submit",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": REDDIT_USER_AGENT
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                errors = res.get("json", {}).get("errors", [])
                if errors:
                    logger.error(f"Reddit submission error: {errors}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Failed to submit Reddit post: {e}")
            return False

    def scan_and_reply_cycle(self) -> int:
        daily_actions = get_action_count_today("reddit")
        if daily_actions >= MAX_REDDIT_ACTIONS_PER_DAY:
            logger.info(f"Reddit daily limit reached ({daily_actions}/{MAX_REDDIT_ACTIONS_PER_DAY})")
            return 0

        replies_count = 0
        keywords = ["projet", "feedback", "avis", "test", "side project", "app", "code", "architecture", "portfolio"]

        for sub in MONITORED_SUBREDDITS:
            if replies_count + daily_actions >= MAX_REDDIT_ACTIONS_PER_DAY:
                break

            posts = self.fetch_new_posts(sub, limit=8)
            for post in posts:
                post_id = post["id"]
                if is_item_seen("reddit", post_id):
                    continue

                full_text = f"{post['title']} {post['selftext']}".lower()
                has_keyword = any(kw in full_text for kw in keywords)

                if has_keyword and post["author"] != REDDIT_USERNAME:
                    reply_text = generate_reddit_reply(post["title"], post["selftext"], sub)
                    success = self.reply_to_post(post_id, reply_text)
                    status = "success" if success else "failed"

                    record_action(
                        platform="reddit",
                        action_type="reply",
                        target_id=post_id,
                        target_url=post["permalink"],
                        content=reply_text,
                        status=status
                    )
                    mark_item_seen("reddit", post_id, post["author"], post["title"], post["permalink"])
                    replies_count += 1
                    time.sleep(2)
                    break
                else:
                    mark_item_seen("reddit", post_id, post["author"], post["title"], post["permalink"])

        return replies_count
