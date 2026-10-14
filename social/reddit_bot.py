import urllib.request
import urllib.parse
import json
import base64
import logging
import time
from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
    REDDIT_USERNAME, REDDIT_PASSWORD,
    REDDIT_TOKEN_V2, REDDIT_SESSION,
    REDDIT_USER_AGENT, MONITORED_SUBREDDITS,
    MAX_REDDIT_ACTIONS_PER_DAY, DRY_RUN
)
from database import is_item_seen, mark_item_seen, record_action, get_action_count_today, has_acted_on
from content_engine import generate_reddit_reply, generate_reddit_post, should_and_generate_followup_reply

logger = logging.getLogger("CTRLX.Social.Reddit")

class RedditBot:
    def __init__(self):
        self.access_token = None
        self.token_expiry = 0

    def is_configured(self) -> bool:
        return bool(REDDIT_TOKEN_V2 or (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET and REDDIT_USERNAME and REDDIT_PASSWORD))

    def get_token(self) -> str | None:
        if REDDIT_TOKEN_V2:
            return REDDIT_TOKEN_V2

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
            if DRY_RUN and not self.is_configured():
                logger.info(f"[SIMULATION] Mode sans clés pour r/{subreddit}")
                return [
                    {
                        "id": f"t3_sim_{subreddit}_1",
                        "raw_id": f"sim_{subreddit}_1",
                        "title": "Besoin d'avis et de retours sur l'architecture de mon projet dev",
                        "selftext": "Je développe un projet solo depuis deux mois et j'aimerais avoir des retours techniques sur mes choix.",
                        "author": "dev_builder_fr",
                        "permalink": f"https://reddit.com/r/{subreddit}/comments/sample",
                        "subreddit": subreddit
                    }
                ]
            logger.warning(f"Erreur lors de la récupération de r/{subreddit}: {e}")
            return []

    def reply_to_post(self, parent_fullname: str, comment_text: str) -> bool:
        if DRY_RUN or not self.is_configured():
            logger.info(f"[DRY RUN] Réponse simulée à {parent_fullname}: {comment_text}")
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
                    logger.error(f"Erreur Reddit commentaire : {errors}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Échec de publication du commentaire Reddit : {e}")
            return False

    def get_subreddit_flair_id(self, subreddit: str) -> str | None:
        token = self.get_token()
        if not token:
            return None
        url = f"https://oauth.reddit.com/r/{subreddit}/api/link_flair_v2"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": REDDIT_USER_AGENT
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                flairs = json.loads(resp.read().decode("utf-8"))
                if flairs and isinstance(flairs, list):
                    for f in flairs:
                        txt = (f.get("text") or "").lower()
                        if any(k in txt for k in ["projet", "logiciel", "discussion", "aide", "général", "news"]):
                            return f.get("id")
                    return flairs[0].get("id")
        except Exception as e:
            logger.warning(f"Échec de récupération des flairs pour r/{subreddit} : {e}")
        return None

    def create_post(self, subreddit: str, title: str, body: str, flair_id: str = None) -> bool:
        if DRY_RUN or not self.is_configured():
            logger.info(f"[DRY RUN] Création de post simulé dans r/{subreddit}:\nTitre: {title}\nCorps:\n{body}")
            return True

        token = self.get_token()
        if not token:
            return False

        target_flair = flair_id or self.get_subreddit_flair_id(subreddit)

        post_data = {
            "api_type": "json",
            "kind": "self",
            "sr": subreddit,
            "title": title,
            "text": body
        }
        if target_flair:
            post_data["flair_id"] = target_flair

        data = urllib.parse.urlencode(post_data).encode("utf-8")

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
                    logger.error(f"Erreur soumission Reddit : {errors}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Échec soumission du post Reddit : {e}")
            return False

    def mark_message_read(self, message_id: str) -> bool:
        token = self.get_token()
        if not token or not message_id:
            return False

        data = urllib.parse.urlencode({"id": message_id}).encode("utf-8")
        req = urllib.request.Request(
            "https://oauth.reddit.com/api/read_message",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": REDDIT_USER_AGENT
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    def scan_inbox_and_reply(self) -> int:
        token = self.get_token()
        if not token:
            return 0

        daily_actions = get_action_count_today("reddit")
        if daily_actions >= MAX_REDDIT_ACTIONS_PER_DAY:
            return 0

        endpoints = [
            "https://oauth.reddit.com/message/unread?limit=10",
            "https://oauth.reddit.com/message/comments?limit=10"
        ]

        processed = 0
        for url in endpoints:
            if processed + daily_actions >= MAX_REDDIT_ACTIONS_PER_DAY:
                break

            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": REDDIT_USER_AGENT
                }
            )

            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    children = data.get("data", {}).get("children", [])

                    for child in children:
                        cd = child.get("data", {})
                        msg_id = cd.get("name")
                        author = cd.get("author", "")
                        body = cd.get("body", "")
                        context = cd.get("context", "")
                        subject = cd.get("subject", "")

                        if not msg_id or author == REDDIT_USERNAME:
                            self.mark_message_read(msg_id)
                            continue

                        if has_acted_on("reddit", msg_id) or is_item_seen("reddit", msg_id):
                            self.mark_message_read(msg_id)
                            continue

                        lang = "en" if any(s in context.lower() for s in ["webdev", "sideproject", "python"]) else "fr"
                        followup = should_and_generate_followup_reply(body, context_text=subject, language=lang)

                        if followup:
                            success = self.reply_to_post(msg_id, followup)
                            status = "success" if success else "failed"
                            record_action(
                                platform="reddit",
                                action_type="followup_reply",
                                target_id=msg_id,
                                target_url=f"https://reddit.com{context}",
                                content=followup,
                                status=status
                            )
                            processed += 1
                            logger.info(f"Suivi conversationnel publié sur Reddit pour {msg_id}")

                        mark_item_seen("reddit", msg_id, author, subject, f"https://reddit.com{context}")
                        self.mark_message_read(msg_id)
                        time.sleep(2)
            except Exception as e:
                logger.warning(f"Erreur vérification messagerie Reddit ({url}) : {e}")

        return processed

    def scan_and_reply_cycle(self) -> int:
        daily_actions = get_action_count_today("reddit")
        if daily_actions >= MAX_REDDIT_ACTIONS_PER_DAY:
            logger.info(f"Limite quotidienne Reddit atteinte ({daily_actions}/{MAX_REDDIT_ACTIONS_PER_DAY})")
            return 0

        replies_count = self.scan_inbox_and_reply()
        keywords = ["projet", "feedback", "avis", "test", "side project", "app", "code", "architecture", "portfolio"]

        for sub in MONITORED_SUBREDDITS:
            if replies_count + daily_actions >= MAX_REDDIT_ACTIONS_PER_DAY:
                break

            posts = self.fetch_new_posts(sub, limit=8)
            for post in posts:
                post_id = post["id"]
                if is_item_seen("reddit", post_id) or has_acted_on("reddit", post_id):
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
