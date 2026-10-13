import sys
import os
import time
import random
import logging
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    DRY_RUN, MONITORED_SUBREDDITS,
    COOLDOWN_BETWEEN_ACTIONS_SEC,
    MAX_REDDIT_ACTIONS_PER_DAY,
    MAX_TWITTER_ACTIONS_PER_DAY
)
from database import (
    init_social_db, get_action_count_today,
    get_recent_actions, record_action
)
from content_engine import generate_reddit_post, generate_twitter_post
from reddit_bot import RedditBot
from twitter_bot import TwitterBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CTRLX.Social.Orchestrator")

def run_single_cycle(reddit: RedditBot, twitter: TwitterBot):
    logger.info("Starting social growth scan cycle...")
    r_today = get_action_count_today("reddit")
    t_today = get_action_count_today("twitter")
    logger.info(f"Today actions: Reddit={r_today}/{MAX_REDDIT_ACTIONS_PER_DAY}, Twitter={t_today}/{MAX_TWITTER_ACTIONS_PER_DAY}")

    reddit_replies = reddit.scan_and_reply_cycle()
    logger.info(f"Reddit scan complete: {reddit_replies} actions processed.")

    time.sleep(random.uniform(2, 5))

    twitter_replies = twitter.scan_and_reply_cycle()
    logger.info(f"Twitter scan complete: {twitter_replies} actions processed.")

def post_reddit_topic(reddit: RedditBot, target_sub: str = "developpeurs"):
    title, body = generate_reddit_post()
    logger.info(f"Publishing discussion to r/{target_sub}...")
    success = reddit.create_post(target_sub, title, body)
    record_action(
        platform="reddit",
        action_type="original_post",
        target_id=target_sub,
        target_url=f"https://reddit.com/r/{target_sub}",
        content=f"{title}\n\n{body}",
        status="success" if success else "failed"
    )
    logger.info("Reddit post action logged.")

def post_tweet_topic(twitter: TwitterBot):
    logger.info("Publishing original tweet...")
    success = twitter.publish_original_tweet()
    logger.info(f"Original tweet action logged (success={success}).")

def show_stats():
    print("========================================")
    print("CTRLX SOCIAL AUTOMATION • STATISTIQUES")
    print("========================================")
    print(f"Mode DRY_RUN : {DRY_RUN}")
    print(f"Actions Reddit aujourd'hui : {get_action_count_today('reddit')}/{MAX_REDDIT_ACTIONS_PER_DAY}")
    print(f"Actions Twitter aujourd'hui : {get_action_count_today('twitter')}/{MAX_TWITTER_ACTIONS_PER_DAY}")
    print("\nDernières actions enregistrées :")
    actions = get_recent_actions(limit=8)
    if not actions:
        print("Aucune action enregistrée pour le moment.")
    for a in actions:
        print(f"[{a['created_at']}] {a['platform'].upper()} ({a['action_type']}) : {a['content'][:70]}... [{a['status']}]")
    print("========================================")

def run_daemon(reddit: RedditBot, twitter: TwitterBot):
    logger.info("Starting CTRLX Social daemon...")
    while True:
        try:
            run_single_cycle(reddit, twitter)
        except Exception as e:
            logger.error(f"Error in daemon cycle: {e}")

        jitter = random.uniform(0.8, 1.3)
        sleep_duration = int(COOLDOWN_BETWEEN_ACTIONS_SEC * jitter)
        logger.info(f"Sleeping for {sleep_duration}s until next cycle...")
        time.sleep(sleep_duration)

def main():
    parser = argparse.ArgumentParser(description="CTRLX Social Automation Engine")
    parser.add_argument("--once", action="store_true", help="Run a single scan and reply cycle")
    parser.add_argument("--daemon", action="store_true", help="Run continuous background loop")
    parser.add_argument("--post-reddit", action="store_true", help="Publish a discussion topic to Reddit")
    parser.add_argument("--post-twitter", action="store_true", help="Publish an original tweet")
    parser.add_argument("--stats", action="store_true", help="Show today action counts and history")
    parser.add_argument("--subreddit", type=str, default="developpeurs", help="Target subreddit for original post")

    args = parser.parse_args()

    init_social_db()
    reddit = RedditBot()
    twitter = TwitterBot()

    if args.stats:
        show_stats()
    elif args.post_reddit:
        post_reddit_topic(reddit, args.subreddit)
    elif args.post_twitter:
        post_tweet_topic(twitter)
    elif args.daemon:
        run_daemon(reddit, twitter)
    else:
        run_single_cycle(reddit, twitter)

if __name__ == "__main__":
    main()
