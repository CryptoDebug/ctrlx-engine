import urllib.request
import urllib.parse
import urllib.error
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
    TWITTER_AUTH_TOKEN, TWITTER_CT0,
    MAX_TWITTER_ACTIONS_PER_DAY, DRY_RUN
)
from database import is_item_seen, mark_item_seen, record_action, get_action_count_today, has_acted_on
from content_engine import generate_twitter_reply, generate_twitter_post, should_and_generate_followup_reply
from browser_manager import has_valid_session, post_tweet_browser, reply_tweet_browser, check_twitter_mentions_browser

logger = logging.getLogger("CTRLX.Social.Twitter")

class TwitterBot:
    def __init__(self):
        self.search_available = True

    def is_configured(self) -> bool:
        return bool(
            has_valid_session("twitter") or
            (TWITTER_AUTH_TOKEN and TWITTER_CT0) or
            (TWITTER_API_KEY and TWITTER_API_SECRET and TWITTER_ACCESS_TOKEN and TWITTER_ACCESS_SECRET)
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
        if not self.search_available:
            return []

        if not TWITTER_BEARER_TOKEN:
            if DRY_RUN:
                logger.info(f"[SIMULATION] Mode sans clés pour la requête '{query}'")
                return [
                    {
                        "id": f"sim_tweet_{abs(hash(query)) % 100000}",
                        "text": "Je viens de déployer mon side project dev en prod, preneur de vos avis techniques",
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
        except urllib.error.HTTPError as e:
            if e.code == 402:
                self.search_available = False
                logger.info("Point de recherche Twitter restreint (402). Bascule sur l'automatisation par navigateur.")
                return []
            logger.warning(f"Erreur recherche Twitter pour '{query}': {e}")
            return []
        except Exception as e:
            logger.warning(f"Erreur recherche Twitter pour '{query}': {e}")
            return []

    def _post_tweet_web(self, text: str, in_reply_to_tweet_id: str = None) -> bool:
        if not (TWITTER_AUTH_TOKEN and TWITTER_CT0):
            return False

        bearer = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        qid = "sqNNr7rKZwnDQZkIiyvcrA"
        url = f"https://x.com/i/api/graphql/{qid}/CreateTweet"

        variables = {
            "tweet_text": text,
            "dark_request": False,
            "withDownvotePerspective": False,
            "withReactionsMetadata": False,
            "withReactionsPerspective": False,
            "withSuperFollowsTweetFields": True,
            "withSuperFollowsUserFields": True,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": []
        }
        if in_reply_to_tweet_id:
            variables["reply"] = {
                "in_reply_to_tweet_id": str(in_reply_to_tweet_id),
                "exclude_reply_user_ids": []
            }

        payload = {
            "variables": variables,
            "features": {
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "responsive_web_home_pinned_timelines_enabled": True,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_level_insights_flow_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "profile_label_improvements_p0_label_enabled": True,
                "rweb_video_timestamps_enabled": True
            },
            "queryId": qid
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": bearer,
                "Cookie": f"auth_token={TWITTER_AUTH_TOKEN}; ct0={TWITTER_CT0}",
                "x-csrf-token": TWITTER_CT0,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "x-twitter-active-user": "yes",
                "x-twitter-auth-type": "OAuth2Session",
                "Referer": "https://x.com/compose/post"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                result = res.get("data", {}).get("create_tweet", {}).get("tweet_results", {}).get("result")
                return bool(result)
        except Exception as e:
            logger.error(f"Erreur publication Twitter web : {e}")
            return False

    def post_tweet(self, text: str, in_reply_to_tweet_id: str = None) -> bool:
        if DRY_RUN or not self.is_configured():
            target_info = f" en réponse à {in_reply_to_tweet_id}" if in_reply_to_tweet_id else ""
            logger.info(f"[DRY RUN] Tweet simulé{target_info}: {text}")
            return True

        if has_valid_session("twitter"):
            if in_reply_to_tweet_id:
                browser_reply_success = reply_tweet_browser(in_reply_to_tweet_id, text)
                if browser_reply_success:
                    return True
            else:
                browser_success = post_tweet_browser(text)
                if browser_success:
                    return True

        if TWITTER_AUTH_TOKEN and TWITTER_CT0:
            web_success = self._post_tweet_web(text, in_reply_to_tweet_id=in_reply_to_tweet_id)
            if web_success:
                return True

        if not (TWITTER_API_KEY and TWITTER_API_SECRET and TWITTER_ACCESS_TOKEN and TWITTER_ACCESS_SECRET):
            return False

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
            logger.error(f"Erreur publication API Twitter : {e}")
            return False

    def scan_mentions_and_reply(self) -> int:
        daily_actions = get_action_count_today("twitter")
        if daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
            return 0

        if not has_valid_session("twitter"):
            return 0

        mentions = check_twitter_mentions_browser()
        processed = 0
        for m in mentions:
            if processed + daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
                break

            m_id = m.get("id")
            m_text = m.get("text", "")
            m_url = m.get("url", f"https://x.com/i/status/{m_id}")

            if not m_id or is_item_seen("twitter", m_id) or has_acted_on("twitter", m_id):
                continue

            followup = should_and_generate_followup_reply(m_text, context_text="Twitter mention", language="fr")
            if followup:
                success = self.post_tweet(followup, in_reply_to_tweet_id=m_id)
                status = "success" if success else "failed"
                record_action(
                    platform="twitter",
                    action_type="followup_reply",
                    target_id=m_id,
                    target_url=m_url,
                    content=followup,
                    status=status
                )
                if success:
                    processed += 1
                    logger.info(f"Suivi conversationnel publié sur Twitter pour le tweet {m_id}")

            mark_item_seen("twitter", m_id, "", m_text[:150], m_url)
            time.sleep(2)

        return processed

    def scan_and_reply_cycle(self) -> int:
        daily_actions = get_action_count_today("twitter")
        if daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
            logger.info(f"Limite quotidienne Twitter atteinte ({daily_actions}/{MAX_TWITTER_ACTIONS_PER_DAY})")
            return 0

        followups = self.scan_mentions_and_reply()
        replies_count = followups

        if self.search_available:
            for query in TWITTER_SEARCH_QUERIES:
                if replies_count + daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
                    break

                tweets = self.search_tweets(query, limit=10)
                for tweet in tweets:
                    t_id = tweet["id"]
                    if is_item_seen("twitter", t_id) or has_acted_on("twitter", t_id):
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

        if replies_count == 0 and (daily_actions < MAX_TWITTER_ACTIONS_PER_DAY):
            published = self.publish_original_tweet()
            if published:
                return 1

        return replies_count

    def reply_to_tweet_id(self, tweet_id: str, custom_text: str = None) -> bool:
        clean_id = tweet_id.strip().rstrip("/").split("/")[-1]
        if is_item_seen("twitter", clean_id) or has_acted_on("twitter", clean_id):
            logger.info(f"Tweet {clean_id} déjà traité.")
            return False

        text = custom_text or generate_twitter_reply("side project dev feedback", "dev")
        success = self.post_tweet(text, in_reply_to_tweet_id=clean_id)
        status = "success" if success else "failed"
        record_action(
            platform="twitter",
            action_type="reply",
            target_id=clean_id,
            target_url=f"https://x.com/i/status/{clean_id}",
            content=text,
            status=status
        )
        mark_item_seen("twitter", clean_id, "", text[:100], f"https://x.com/i/status/{clean_id}")
        return success

    def publish_original_tweet(self) -> bool:
        daily_actions = get_action_count_today("twitter")
        if daily_actions >= MAX_TWITTER_ACTIONS_PER_DAY:
            return False

        content = generate_twitter_post()
        success = self.post_tweet(content)
        status = "success" if success else "failed"
        record_action(
            platform="twitter",
            action_type="original_post",
            target_id="self",
            target_url="",
            content=content,
            status=status
        )
        return success
