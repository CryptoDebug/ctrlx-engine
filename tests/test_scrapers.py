import unittest
from scrapers.utils import strip_html
from scrapers.feed_scraper import RADAR_SOURCES
from scrapers.github_scraper import TECH_RELEASES_SOURCES
from services.feeds_service import check_for_breaking_event

class TestScrapers(unittest.TestCase):
    def test_strip_html_basic(self):
        html_input = "<p>Bonjour <strong>le monde</strong> &amp; bienvenue !</p>"
        expected = "Bonjour le monde & bienvenue !"
        self.assertEqual(strip_html(html_input), expected)

    def test_strip_html_complex(self):
        html_input = '<div class="test"><a href="https://example.com">Lien</a><br/><span>Texte</span></div>'
        expected = "Lien Texte"
        self.assertEqual(strip_html(html_input), expected)

    def test_strip_html_empty_and_whitespace(self):
        self.assertEqual(strip_html(""), "")
        self.assertEqual(strip_html(None), "")
        self.assertEqual(strip_html("   <p>   </p>   "), "")

    def test_radar_sources_configuration(self):
        self.assertGreater(len(RADAR_SOURCES), 0)
        for src in RADAR_SOURCES:
            self.assertIn("domain", src)
            self.assertIn("url", src)
            self.assertIn("name", src)
            self.assertTrue(src["url"].startswith("http"))

    def test_tech_releases_sources_configuration(self):
        self.assertGreater(len(TECH_RELEASES_SOURCES), 0)
        for src in TECH_RELEASES_SOURCES:
            self.assertIn("name", src)
            self.assertIn("url", src)
            self.assertTrue(src["url"].endswith(".atom"))

    def test_breaking_event_detection(self):
        self.assertTrue(check_for_breaking_event("Alerte", "Un zero-day exploited in the wild est en cours"))
        self.assertTrue(check_for_breaking_event("CVE-2026", "Faille CVSS 10.0 critique découverte"))
        self.assertFalse(check_for_breaking_event("Mise à jour standard", "Correction de bugs mineurs sur la v1.2"))

if __name__ == "__main__":
    unittest.main()
