"""Regression checks for editable metadata, migration, and harness filtering."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configuration import load_metadata, load_program_config, save_ui_state
from tree_builder import Tree, load_templates


class MetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.metadata = self.root / "metadata.yml"
        self.config = self.root / "config.yml"
        self.legacy = self.root / "template_config.json"
        self.snippets = self.root / "snippets"
        self.snippets.mkdir()
        (self.snippets / "shared.md").write_text(
            "---\nharness: [alpha, beta]\nllm: [one, two]\nlanguage: [python]\n---\nShared body\n"
        )

    def load(self) -> dict[str, Any]:
        return load_metadata(self.metadata, self.legacy, load_templates(self.snippets))

    def test_json_migration_preserves_editor_selections_and_expansion(self) -> None:
        legacy = {
            "editor": "codium --wait",
            "templates": {"shared": True},
            "ui_state": {"expanded_paths": ["alpha", "alpha/one"]},
        }
        self.legacy.write_text(json.dumps(legacy))
        self.assertEqual(load_program_config(self.config, self.legacy), {"editor": "codium --wait"})
        data = self.load()
        self.assertEqual(data["templates"], legacy["templates"])
        self.assertEqual(data["ui_state"], legacy["ui_state"])
        self.config.write_text("editor: vim\n")
        self.assertEqual(load_program_config(self.config, self.legacy)["editor"], "vim")
        self.assertEqual(json.loads(self.legacy.read_text()), legacy)

    def test_discovery_is_additive_and_keeps_manual_access_and_comments(self) -> None:
        self.metadata.write_text(
            "# Keep my notes\nproviders:\n  custom: [one] # My provider\n"
            "harnesses:\n  alpha:\n    models: [] # Explicitly no models\n"
            "  beta:\n    models: [one]\n"
        )
        data = self.load()
        self.assertEqual(data["providers"]["custom"], ["one"])
        self.assertEqual(data["providers"]["default provider"], ["two"])
        self.assertEqual(data["harnesses"]["alpha"]["models"], [])
        self.assertEqual(data["harnesses"]["beta"]["models"], ["one"])
        (self.snippets / "new.md").write_text(
            "---\nharness: [alpha, gamma]\nllm: [three]\n---\nNew body\n"
        )
        data = self.load()
        self.assertEqual(data["providers"]["default provider"], ["two", "three"])
        self.assertEqual(data["harnesses"]["alpha"]["models"], [])
        self.assertEqual(data["harnesses"]["gamma"]["models"], ["three"])
        before = self.metadata.read_text()
        self.load()
        self.assertEqual(self.metadata.read_text(), before)
        self.assertIn("# Keep my notes", before)
        self.assertIn("# My provider", before)
        self.assertIn("# Explicitly no models", before)

    def test_moving_models_to_named_providers_does_not_rediscover_them(self) -> None:
        self.metadata.write_text(
            "providers:\n  vendor: [one, two]\n"
            "harnesses:\n  alpha:\n    models: [one]\n  beta:\n    models: [two]\n"
        )
        self.assertNotIn("default provider", self.load()["providers"])

    def test_ui_save_keeps_manual_edits_made_while_picker_is_open(self) -> None:
        self.load()
        self.metadata.write_text(
            "# External edit\nproviders:\n  vendor: [one, two]\n"
            "harnesses:\n  alpha:\n    models: [one]\n  beta:\n    models: []\n"
        )
        data = save_ui_state(
            self.metadata, self.legacy, load_templates(self.snippets),
            {"shared": True}, ["alpha"],
        )
        self.assertEqual(data["harnesses"]["beta"]["models"], [])
        self.assertEqual(data["providers"], {"vendor": ["one", "two"]})
        self.assertTrue(data["templates"]["shared"])
        self.assertEqual(data["ui_state"]["expanded_paths"], ["alpha"])
        self.assertIn("# External edit", self.metadata.read_text())

    def test_filtering_excludes_disallowed_combinations_but_keeps_generic_snippets(self) -> None:
        (self.snippets / "generic.md").write_text(
            "---\nharness: [alpha]\nllm: []\n---\nGeneric body\n"
        )
        tree = Tree(load_templates(self.snippets), {"alpha": [], "beta": ["two"]})
        paths = {node.path for node in tree.all_nodes()}
        self.assertIn("alpha/generic", paths)
        self.assertIn("beta/two/python/shared", paths)
        self.assertNotIn("alpha/one", paths)
        self.assertNotIn("alpha/two", paths)
        self.assertNotIn("beta/one", paths)
        selected: dict[str, bool] = {}
        tree.root.toggle_selection(selected)
        self.assertEqual(selected, {"shared": True, "generic": True})

    def test_invalid_yaml_or_access_lists_are_not_overwritten(self) -> None:
        for invalid in (
            "harnesses: [broken",
            "harnesses:\n  alpha:\n    models: one\n",
            "providers:\n  vendor: one\n",
        ):
            with self.subTest(invalid=invalid):
                self.metadata.write_text(invalid)
                with self.assertRaises(RuntimeError):
                    self.load()
                self.assertEqual(self.metadata.read_text(), invalid)


if __name__ == "__main__":
    unittest.main()
