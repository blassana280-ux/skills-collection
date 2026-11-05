import unittest

from omnibrain.frontmatter import parse_frontmatter, FrontmatterError


class FrontmatterTests(unittest.TestCase):
    def test_scalar_and_inline_list(self):
        text = '---\nname: Test Agent\nid: test-agent\ndomains: [ui, backend]\n---\n# Corps\n'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["name"], "Test Agent")
        self.assertEqual(meta["id"], "test-agent")
        self.assertEqual(meta["domains"], ["ui", "backend"])
        self.assertIn("# Corps", body)

    def test_quoted_values_and_block_list(self):
        text = (
            '---\n'
            'name: "Agent cité"\n'
            "domains:\n"
            "  - security\n"
            "  - devops\n"
            "emoji: 🛡️\n"
            '---\n'
            "body"
        )
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["name"], "Agent cité")
        self.assertEqual(meta["domains"], ["security", "devops"])
        self.assertEqual(meta["emoji"], "🛡️")
        self.assertEqual(body, "body")

    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("# Juste du Markdown")
        self.assertEqual(meta, {})
        self.assertIn("Markdown", body)

    def test_unclosed_block_raises(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("---\nname: sans fin\n")

    def test_orphan_list_item_raises(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("---\n- orphelin\n---\n")


if __name__ == "__main__":
    unittest.main()
