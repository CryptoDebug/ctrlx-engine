import sys
import os
import time
import random
import logging
import argparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    DRY_RUN, MONITORED_SUBREDDITS,
    COOLDOWN_BETWEEN_ACTIONS_SEC,
    MAX_REDDIT_ACTIONS_PER_DAY,
    MAX_TWITTER_ACTIONS_PER_DAY,
    MAX_FACEBOOK_ACTIONS_PER_DAY
)
from database import (
    init_social_db, get_action_count_today,
    get_recent_actions, record_action, count_facebook_groups
)
from content_engine import generate_reddit_post, generate_twitter_post, generate_facebook_post
from reddit_bot import RedditBot
from twitter_bot import TwitterBot
from facebook_bot import FacebookBot
from browser_manager import interactive_login, ensure_all_sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CTRLX.Social.Orchestrator")

def run_single_cycle(reddit: RedditBot, twitter: TwitterBot, facebook: FacebookBot):
    logger.info("Démarrage du cycle d'automatisation sociale CTRLX...")
    r_today = get_action_count_today("reddit")
    t_today = get_action_count_today("twitter")
    f_today = get_action_count_today("facebook")
    logger.info(f"Actions du jour : Reddit={r_today}/{MAX_REDDIT_ACTIONS_PER_DAY}, Twitter={t_today}/{MAX_TWITTER_ACTIONS_PER_DAY}, Facebook={f_today}/{MAX_FACEBOOK_ACTIONS_PER_DAY}")

    reddit_replies = reddit.scan_and_reply_cycle()
    logger.info(f"Cycle Reddit terminé : {reddit_replies} action(s) effectuée(s).")

    time.sleep(random.uniform(2, 5))

    twitter_replies = twitter.scan_and_reply_cycle()
    logger.info(f"Cycle Twitter terminé : {twitter_replies} action(s) effectuée(s).")

    time.sleep(random.uniform(2, 5))

    facebook_actions = facebook.scan_and_post_cycle()
    logger.info(f"Cycle Facebook terminé : {facebook_actions} action(s) effectuée(s).")

def post_reddit_topic(reddit: RedditBot, target_sub: str = "developpeurs"):
    title, body = generate_reddit_post()
    logger.info(f"Publication d'une discussion sur r/{target_sub}...")
    success = reddit.create_post(target_sub, title, body)
    record_action(
        platform="reddit",
        action_type="original_post",
        target_id=target_sub,
        target_url=f"https://reddit.com/r/{target_sub}",
        content=f"{title}\n\n{body}",
        status="success" if success else "failed"
    )
    logger.info("Action Reddit enregistrée dans l'historique.")

def post_tweet_topic(twitter: TwitterBot):
    logger.info("Publication d'un tweet original...")
    success = twitter.publish_original_tweet()
    logger.info(f"Action Tweet enregistrée (succès={success}).")

def post_facebook_topic(facebook: FacebookBot):
    logger.info("Publication d'un post Facebook...")
    success = facebook.publish_original_post()
    logger.info(f"Action Facebook enregistrée (succès={success}).")

def show_stats():
    print("========================================")
    print("CTRLX AUTOMATISATION SOCIALE | STATISTIQUES")
    print("========================================")
    print(f"Mode DRY_RUN : {DRY_RUN}")
    print(f"Actions Reddit aujourd'hui : {get_action_count_today('reddit')}/{MAX_REDDIT_ACTIONS_PER_DAY}")
    print(f"Actions Twitter aujourd'hui : {get_action_count_today('twitter')}/{MAX_TWITTER_ACTIONS_PER_DAY}")
    print(f"Actions Facebook aujourd'hui : {get_action_count_today('facebook')}/{MAX_FACEBOOK_ACTIONS_PER_DAY}")
    print(f"Groupes Facebook répertoriés : {count_facebook_groups()}")
    print("\nDernières actions enregistrées :")
    actions = get_recent_actions(limit=8)
    if not actions:
        print("Aucune action enregistrée pour le moment.")
    for a in actions:
        print(f"[{a['created_at']}] {a['platform'].upper()} ({a['action_type']}) : {a['content'][:70]}... [{a['status']}]")
    print("========================================")

def run_daemon(reddit: RedditBot, twitter: TwitterBot, facebook: FacebookBot):
    logger.info("Lancement du démon CTRLX Social 24/7...")
    while True:
        try:
            run_single_cycle(reddit, twitter, facebook)
        except Exception as e:
            logger.error(f"Erreur dans la boucle du démon : {e}")

        jitter = random.uniform(0.8, 1.3)
        sleep_duration = int(COOLDOWN_BETWEEN_ACTIONS_SEC * jitter)
        logger.info(f"Pause de {sleep_duration}s jusqu'au prochain cycle d'engagement...")
        time.sleep(sleep_duration)

def handle_auth(platform: str):
    target = platform.lower()
    if target == "all":
        for p in ["twitter", "reddit", "facebook"]:
            interactive_login(p)
    else:
        interactive_login(target)

def main():
    parser = argparse.ArgumentParser(description="CTRLX Social Automation Engine")
    parser.add_argument("--once", action="store_true", help="Exécuter un cycle unique de scan et de réponse")
    parser.add_argument("--daemon", action="store_true", help="Exécuter en continu 24/7 en arrière-plan")
    parser.add_argument("--post-reddit", action="store_true", help="Publier une discussion sur Reddit")
    parser.add_argument("--post-twitter", action="store_true", help="Publier un tweet original")
    parser.add_argument("--post-facebook", action="store_true", help="Publier sur Facebook")
    parser.add_argument("--reply-tweet", type=str, default="", help="Répondre à un ID ou URL de tweet")
    parser.add_argument("--text", type=str, default="", help="Texte personnalisé pour une réponse ou un tweet")
    parser.add_argument("--auth", type=str, default="", help="Connexion interactive (twitter, reddit, facebook, all)")
    parser.add_argument("--discover-groups", action="store_true", help="Lancer la recherche de groupes Facebook français")
    parser.add_argument("--stats", action="store_true", help="Afficher les statistiques et l'historique d'actions")
    parser.add_argument("--subreddit", type=str, default="developpeurs", help="Subreddit cible pour publication")

    args = parser.parse_args()

    init_social_db()
    reddit = RedditBot()
    twitter = TwitterBot()
    facebook = FacebookBot()

    if args.auth:
        handle_auth(args.auth)
    elif args.stats:
        show_stats()
    elif args.discover_groups:
        added = facebook.discover_groups()
        print(f"{added} nouveau(x) groupe(s) français répertorié(s). Total : {count_facebook_groups()}")
    elif args.post_reddit:
        post_reddit_topic(reddit, args.subreddit)
    elif args.post_twitter:
        post_tweet_topic(twitter)
    elif args.post_facebook:
        post_facebook_topic(facebook)
    elif args.reply_tweet:
        logger.info(f"Réponse au tweet {args.reply_tweet}...")
        success = twitter.reply_to_tweet_id(args.reply_tweet, custom_text=args.text or None)
        logger.info(f"Réponse tweet enregistrée (succès={success}).")
    elif args.once:
        ensure_all_sessions()
        run_single_cycle(reddit, twitter, facebook)
    else:
        ensure_all_sessions()
        run_daemon(reddit, twitter, facebook)

if __name__ == "__main__":
    main()
