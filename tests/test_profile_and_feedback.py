import unittest
import tempfile
import os
import database

class TestProfileAndFeedback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        cls.temp_db.close()
        cls.orig_db_path = database.DB_PATH
        database.DB_PATH = cls.temp_db.name
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        database.DB_PATH = cls.orig_db_path
        if os.path.exists(cls.temp_db.name):
            try:
                os.remove(cls.temp_db.name)
            except OSError:
                pass

    def test_default_profile(self):
        profile = database.get_user_profile(999001)
        self.assertEqual(profile["user_id"], 999001)
        self.assertEqual(profile["feedback_karma"], 0)
        self.assertEqual(profile["ships_count"], 0)
        self.assertEqual(profile["domains"], "")

    def test_upsert_and_fetch_profile(self):
        user_id = 999002
        database.upsert_user_profile(
            user_id=user_id,
            domains="Web, Cloud",
            speciality="Dev Fullstack",
            skills="Python, TypeScript, Docker",
            github_url="https://github.com/testdev",
            portfolio_url="https://testdev.io",
            bio="Passionné d'open source"
        )
        profile = database.get_user_profile(user_id)
        self.assertEqual(profile["speciality"], "Dev Fullstack")
        self.assertEqual(profile["domains"], "Web, Cloud")
        self.assertEqual(profile["skills"], "Python, TypeScript, Docker")
        self.assertEqual(profile["github_url"], "https://github.com/testdev")
        self.assertEqual(profile["portfolio_url"], "https://testdev.io")
        self.assertEqual(profile["bio"], "Passionné d'open source")

        database.upsert_user_profile(
            user_id=user_id,
            domains="Web, AI",
            speciality="Lead Dev",
            skills="Python, PyTorch",
            github_url="https://github.com/testdev",
            portfolio_url="",
            bio="Machine learning and systems"
        )
        updated = database.get_user_profile(user_id)
        self.assertEqual(updated["speciality"], "Lead Dev")
        self.assertEqual(updated["domains"], "Web, AI")

    def test_record_feedback_transaction_and_timestamp(self):
        giver_id = 999101
        receiver_id = 999102
        karma_1 = database.record_feedback_transaction(
            giver_id=giver_id,
            receiver_id=receiver_id,
            message_id=123456,
            channel_id=654321,
            reason="Excellente revue UX"
        )
        self.assertEqual(karma_1, 1)

        karma_2 = database.record_feedback_transaction(
            giver_id=giver_id,
            receiver_id=receiver_id,
            message_id=123457,
            channel_id=654321,
            reason="Deuxième retour utile"
        )
        self.assertEqual(karma_2, 2)

        receiver_profile = database.get_user_profile(receiver_id)
        self.assertEqual(receiver_profile["feedback_karma"], 2)

        last_given = database.get_last_feedback_given_time(giver_id)
        self.assertGreater(last_given, 0)

    def test_increment_user_ships(self):
        builder_id = 999201
        ships_1 = database.increment_user_ships(builder_id)
        self.assertEqual(ships_1, 1)

        ships_2 = database.increment_user_ships(builder_id)
        self.assertEqual(ships_2, 2)

        profile = database.get_user_profile(builder_id)
        self.assertEqual(profile["ships_count"], 2)

    def test_leaderboards(self):
        database.record_feedback_transaction(giver_id=999301, receiver_id=999302, reason="Karma test 1")
        database.record_feedback_transaction(giver_id=999301, receiver_id=999302, reason="Karma test 2")
        database.record_feedback_transaction(giver_id=999301, receiver_id=999303, reason="Karma test 3")

        fb_board = database.get_feedback_leaderboard(limit=5)
        self.assertGreater(len(fb_board), 0)
        found_top = any(r["user_id"] == 999302 and r["feedback_karma"] >= 2 for r in fb_board)
        self.assertTrue(found_top)

        database.increment_user_ships(999401)
        database.increment_user_ships(999401)
        database.increment_user_ships(999401)
        database.increment_user_ships(999402)

        ships_board = database.get_ships_leaderboard(limit=5)
        self.assertGreater(len(ships_board), 0)
        self.assertEqual(ships_board[0]["user_id"], 999401)
        self.assertEqual(ships_board[0]["ships_count"], 3)

if __name__ == "__main__":
    unittest.main()
