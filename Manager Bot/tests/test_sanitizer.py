import unittest
import asyncio
from services.gemini_service import sanitize_text
from services.publisher_service import PublisherService

class TestSanitizerAndQueue(unittest.TestCase):
    def test_sanitize_replaces_em_dash(self):
        input_text = "Développement logiciel — Bonnes pratiques et outils — Version 2.0"
        result = sanitize_text(input_text)
        self.assertNotIn("—", result)
        self.assertIn("-", result)

    def test_sanitize_removes_markdown_horizontal_rules(self):
        input_text = "Section 1\n---\nSection 2\n   ---   \nSection 3"
        result = sanitize_text(input_text)
        self.assertNotIn("---", result)

    def test_sanitize_length_cap_and_signature(self):
        long_text = "Paragraphe de test très long. " * 150
        result = sanitize_text(long_text, max_len=1900)
        self.assertLessEqual(len(result), 1950)
        self.assertIn("✍️ *Généré par CTRLX AI*", result)

    def test_publisher_queue_enqueue(self):
        service = PublisherService()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(service.enqueue(123456789, content="Test message"))
            self.assertEqual(service.queue.qsize(), 1)
        finally:
            loop.close()

if __name__ == "__main__":
    unittest.main()
