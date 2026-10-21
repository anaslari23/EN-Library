import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codeinenglish.migrate import migrate_source, migrate_file
from codeinenglish.provenance import split_provenance


class MigrateTests(unittest.TestCase):
    def test_legacy_instruction_migration_adds_header_and_preserves_generated_body(self):
        original = '# license\nshow "Hello"\n'
        migrated, reasons = migrate_source(original, "hello.en", "0.1")
        self.assertEqual(migrated, '# license\nen 0.1\nshow "Hello"\n')
        self.assertTrue(any("version" in reason.lower() for reason in reasons))

    def test_problem_migration_rebuilds_legacy_text_and_changes_alias(self):
        original = (
            "en 0.1\nimport codeinpython library\n"
            "# Given two numbers and a target, return the indices that add up to the target.\n"
            "# Exactly one solution exists; do not use the same element twice.\n"
            '# Example input: {"nums":[2,7],"target":9}\n# Example output: [0,1]\n'
        )
        migrated, _ = migrate_source(original, "pair.en", "0.2")
        self.assertIn("target python", migrated)
        self.assertIn("#? Given two numbers", migrated)
        self.assertIn("#? Example input:", migrated)
        self.assertNotIn("import codeinpython library", migrated)

    def test_existing_question_mark_is_preserved_as_legacy_text(self):
        original = "en 0.1\nimport codeinpython library\n#? Given two numbers and a target, return their indices.\n"
        migrated, _ = migrate_source(original, "pair.en", "0.2")
        self.assertIn("#? ? Given two numbers", migrated)

    def test_documentation_marker_in_instruction_file_is_escaped(self):
        original = "en 0.1\n#? This is documentation.\nshow 1\n"
        migrated, _ = migrate_source(original, "program.en", "0.2")
        self.assertIn("# ? This is documentation.", migrated)

    def test_dry_run_does_not_change_file_and_write_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.en"
            source.write_text('en 0.1\nshow "Hello"\n', encoding="utf-8")
            changed, diff = migrate_file(source, "0.2", write=False)
            self.assertTrue(changed)
            self.assertIn("en 0.2", diff)
            self.assertTrue(source.read_text(encoding="utf-8").startswith("en 0.1"))
            migrate_file(source, "0.2", write=True)
            self.assertTrue(source.read_text(encoding="utf-8").startswith("en 0.2"))

    def test_second_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.en"
            source.write_text("en 0.2\nshow 1\n", encoding="utf-8")
            changed, diff = migrate_file(source, "0.2", write=True)
            self.assertFalse(changed)
            self.assertEqual(diff, "")

    def test_migration_aborts_and_preserves_source_when_generated_bodies_differ(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.en"
            source.write_text('en 0.1\nshow "Hello"\n', encoding="utf-8")
            with patch("codeinenglish.migrate._generated_body", side_effect=["old", "new"]):
                with self.assertRaises(ValueError):
                    migrate_file(source, "0.2", write=True)
            self.assertEqual(source.read_text(encoding="utf-8"), 'en 0.1\nshow "Hello"\n')


if __name__ == "__main__":
    unittest.main()
