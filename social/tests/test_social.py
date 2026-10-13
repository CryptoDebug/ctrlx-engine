import unittest
import os
import tempfile
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
import database
from content_engine import (
    strip_emojis, generate_reddit_reply,
    generate_reddit_post, generate_twitter_reply,
    generate_twitter_post, EMOJI_PATTERN
)

class TestSocialModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
        cls.temp_db.close()
        cls.orig_db_path = config.SOCIAL_DB_PATH
        config.SOCIAL_DB_PATH = cls.temp_db.name
        database.SOCIAL_DB_PATH = cls.temp_db.name
        database.init_social_db()

    @classmethod
    def tearDownClass(cls):
        config.SOCIAL_DB_PATH = cls.orig_db_path
        database.SOCIAL_DB_PATH = cls.orig_db_path
        if os.path.exists(cls.temp_db.name):
            try:
                os.remove(cls.temp_db.name)
            except OSError:
                pass

    def test_strip_emojis(self):
        text_with_emojis = "Super projet ! 🚀🔥 J'adore cette stack. 👍💻"
        result = strip_emojis(text_with_emojis)
        self.assertNotIn("🚀", result)
        self.assertNotIn("🔥", result)
        self.assertNotIn("👍", result)
        self.assertNotIn("💻", result)
        self.assertFalse(bool(EMOJI_PATTERN.search(result)))

    def test_no_em_dash_in_cleaning(self):
        text_with_dash = "Architecture logicielle \u2014 version 2.0"
        cleaned = strip_emojis(text_with_dash)
        self.assertNotIn("\u2014", cleaned)

    def test_generated_content_zero_emojis(self):
        reddit_rep = generate_reddit_reply("Mon nouveau SaaS en Python", "Voici mon projet solo", "developpeurs")
        self.assertFalse(bool(EMOJI_PATTERN.search(reddit_rep)))
        self.assertGreater(len(reddit_rep), 10)

        tweet_rep = generate_twitter_reply("On vient de ship la v1 !", "random_dev")
        self.assertFalse(bool(EMOJI_PATTERN.search(tweet_rep)))
        self.assertGreater(len(tweet_rep), 10)

        tweet_post = generate_twitter_post()
        self.assertFalse(bool(EMOJI_PATTERN.search(tweet_post)))

        title, body = generate_reddit_post()
        self.assertFalse(bool(EMOJI_PATTERN.search(title)))
        self.assertFalse(bool(EMOJI_PATTERN.search(body)))

    def test_database_seen_and_actions(self):
        plat = "reddit"
        item_id = "t3_test123"

        self.assertFalse(database.is_item_seen(plat, item_id))
        database.mark_item_seen(plat, item_id, author="dev_guy", title="Test Post", url="https://reddit.com/r/test")
        self.assertTrue(database.is_item_seen(plat, item_id))

        count_before = database.get_action_count_today(plat)
        database.record_action(plat, "reply", item_id, "Reponse pertinente de test")
        count_after = database.get_action_count_today(plat)
        self.assertEqual(count_after, count_before + 1)

        recent = database.get_recent_actions(limit=5)
        self.assertGreater(len(recent), 0)
        self.assertEqual(recent[0]["target_id"], item_id)

if __name__ == "__main__":
    unittest.main()
