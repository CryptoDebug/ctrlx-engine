import unittest
import os
import tempfile
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
import database
from content_engine import (
    strip_emojis, generate_reddit_reply,
    generate_reddit_post, generate_twitter_reply,
    generate_twitter_post, generate_facebook_post,
    should_and_generate_followup_reply, EMOJI_PATTERN
)

class TestSocialModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
        cls.temp_db.close()
        cls.orig_db_path = config.SOCIAL_DB_PATH
        cls.orig_dry_run = config.DRY_RUN
        config.DRY_RUN = True
        config.SOCIAL_DB_PATH = cls.temp_db.name
        database.SOCIAL_DB_PATH = cls.temp_db.name
        database.init_social_db()

    @classmethod
    def tearDownClass(cls):
        config.SOCIAL_DB_PATH = cls.orig_db_path
        config.DRY_RUN = cls.orig_dry_run
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

        fb_post = generate_facebook_post()
        self.assertFalse(bool(EMOJI_PATTERN.search(fb_post)))
        self.assertGreater(len(fb_post), 20)

    def test_french_accents_presence(self):
        accent_pattern = re.compile(r"[éèêàâîïôùûçÉÈÊÀÂÎÏÔÙÛÇ]")

        reddit_rep = generate_reddit_reply("Projet dev", "Besoin d'avis", "developpeurs")
        self.assertTrue(bool(accent_pattern.search(reddit_rep)))

        tweet_rep = generate_twitter_reply("Nouveau projet dev", "user")
        self.assertTrue(bool(accent_pattern.search(tweet_rep)))

        tweet_post = generate_twitter_post()
        self.assertTrue(bool(accent_pattern.search(tweet_post)))

        title, body = generate_reddit_post()
        self.assertTrue(bool(accent_pattern.search(title)))
        self.assertTrue(bool(accent_pattern.search(body)))

        fb_post = generate_facebook_post()
        self.assertTrue(bool(accent_pattern.search(fb_post)))

    def test_followup_detection_and_no_reply(self):
        self.assertIsNone(should_and_generate_followup_reply("merci"))
        self.assertIsNone(should_and_generate_followup_reply("Merci beaucoup !"))
        self.assertIsNone(should_and_generate_followup_reply("cool merci bcp"))
        self.assertIsNone(should_and_generate_followup_reply("ok"))
        self.assertIsNone(should_and_generate_followup_reply("pas de souci"))
        self.assertIsNone(should_and_generate_followup_reply("thanks"))
        self.assertIsNone(should_and_generate_followup_reply("parfait"))

        question_reply = should_and_generate_followup_reply("Tu utilises quelle stack pour la persistance ?")
        self.assertIsNotNone(question_reply)
        self.assertGreater(len(question_reply), 10)

        interest_reply = should_and_generate_followup_reply("Carrément chaud pour tester, c'est quoi le lien du projet ?")
        self.assertIsNotNone(interest_reply)
        self.assertGreater(len(interest_reply), 10)

    def test_database_seen_and_actions(self):
        plat = "reddit"
        item_id = "t3_test123"

        self.assertFalse(database.is_item_seen(plat, item_id))
        self.assertFalse(database.has_acted_on(plat, item_id))

        database.mark_item_seen(plat, item_id, author="dev_guy", title="Test Post", url="https://reddit.com/r/test")
        self.assertTrue(database.is_item_seen(plat, item_id))

        count_before = database.get_action_count_today(plat)
        database.record_action(plat, "reply", item_id, "Réponse pertinente de test")
        self.assertTrue(database.has_acted_on(plat, item_id))

        count_after = database.get_action_count_today(plat)
        self.assertEqual(count_after, count_before + 1)

        recent = database.get_recent_actions(limit=5)
        self.assertGreater(len(recent), 0)
        self.assertEqual(recent[0]["target_id"], item_id)

    def test_facebook_groups_database(self):
        gid = "group_test_999"
        gname = "Groupe Développeurs Web France"
        gurl = "https://www.facebook.com/groups/group_test_999/"

        self.assertTrue(database.add_facebook_group(gid, gname, gurl))
        self.assertFalse(database.add_facebook_group(gid, gname, gurl))
        self.assertGreaterEqual(database.count_facebook_groups(), 1)

        available = database.get_available_facebook_groups(limit=5)
        self.assertTrue(any(g["group_id"] == gid for g in available))

        database.mark_facebook_group_posted(gid)

    def test_facebook_bot_simulation(self):
        from facebook_bot import FacebookBot
        bot = FacebookBot()
        self.assertTrue(bot.publish_original_post())
        self.assertGreaterEqual(bot.discover_groups(), 0)
        self.assertGreaterEqual(bot.scan_and_post_cycle(), 0)

if __name__ == "__main__":
    unittest.main()
