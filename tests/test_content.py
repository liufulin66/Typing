import unittest

from typing_app.content import get_articles, normalize_text


class ContentTests(unittest.TestCase):
    def test_both_languages_have_nonempty_material(self):
        for language in ("zh", "en"):
            items = get_articles(language)
            self.assertGreaterEqual(len(items), 1)
            self.assertTrue(all(normalize_text(item["text"]) for item in items))

    def test_custom_text_preserves_content_and_normalizes_newlines(self):
        self.assertEqual(normalize_text(' <script>test</script>\r\n next '),
                         ' <script>test</script>\n next ')
        for value in (None, "", " \r\n\t"):
            with self.assertRaises(ValueError):
                normalize_text(value)
