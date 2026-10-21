import unittest

from codeinenglish.contract import read_contract


class SourceContractTests(unittest.TestCase):
    def codes(self, contract):
        return [diagnostic.code for diagnostic in contract.diagnostics]

    def test_legacy_instruction_is_preserved_and_warns(self):
        contract = read_contract("set total to 5.\n", "legacy.en")
        self.assertEqual(contract.version, None)
        self.assertEqual(contract.form, "instructions")
        self.assertEqual([line.text for line in contract.lines], ["set total to 5."])
        self.assertEqual(self.codes(contract), ["EN-W401"])

    def test_legacy_problem_comment_column_offset_includes_removed_space(self):
        contract = read_contract("en 0.1\ntarget python\n   # find the maximum\n", "legacy-problem.en")
        self.assertEqual(contract.form, "problem")
        self.assertEqual(contract.lines[0].text, "find the maximum")
        self.assertEqual(contract.lines[0].col_offset, 5)

    def test_version_header_after_ordinary_comment_is_allowed(self):
        contract = read_contract("# license\nen 0.2\ntarget python\n#? find two numbers\n", "pair.en")
        self.assertTrue(contract.ok)
        self.assertEqual(contract.version, (0, 2))
        self.assertEqual(contract.form, "problem")
        self.assertEqual(contract.target, "python")
        self.assertEqual([(line.line, line.text, line.col_offset) for line in contract.lines], [(4, "find two numbers", 3)])

    def test_legacy_marker_is_not_a_marker_and_is_warned(self):
        contract = read_contract("import codeinpython library\n#? find two numbers\n", "legacy-marker.en")
        self.assertIsNone(contract.version)
        self.assertEqual(contract.form, "problem")
        self.assertEqual(contract.lines[0].text, "? find two numbers")
        self.assertIn("EN-W403", self.codes(contract))

    def test_header_inside_comment_request_or_string_is_ignored(self):
        comment = read_contract("en 0.2\n# en 0.2\nset text to \"en 0.2\".\n", "comment.en")
        request = read_contract("en 0.2\n#? find the text en 0.2\n", "request.en")
        self.assertEqual(self.codes(comment), [])
        self.assertEqual(self.codes(request), [])

    def test_misplaced_header_is_diagnosed(self):
        contract = read_contract("set total to 5.\nen 0.2\n", "late.en")
        self.assertIn("EN-E101", self.codes(contract))
        self.assertFalse(contract.ok)

    def test_duplicate_headers_are_diagnosed(self):
        contract = read_contract("en 0.2\nen 0.2\nset total to 5.\n", "duplicate.en")
        self.assertIn("EN-E104", self.codes(contract))

    def test_unknown_version_is_diagnosed(self):
        contract = read_contract("en 9.9\nset total to 5.\n", "future.en")
        self.assertIn("EN-E103", self.codes(contract))

    def test_invalid_version_is_diagnosed(self):
        contract = read_contract("en nope\nset total to 5.\n", "invalid.en")
        self.assertIn("EN-E102", self.codes(contract))

    def test_problem_marker_preserves_blank_lines_and_source_columns(self):
        source = "en 0.2\n   #? first line\n\t#?\n\t#? third line\n"
        contract = read_contract(source, "positions.en")
        self.assertTrue(contract.ok)
        self.assertEqual([(line.line, line.text, line.col_offset) for line in contract.lines], [
            (2, "first line", 6), (3, "", 3), (4, "third line", 4)
        ])

    def test_entirely_empty_request_block_is_diagnosed(self):
        contract = read_contract("en 0.2\n#?\n#?   \n", "empty.en")
        self.assertIn("EN-E303", self.codes(contract))

    def test_blank_request_line_inside_nonempty_block_is_allowed(self):
        contract = read_contract("en 0.2\n#? text\n#?\n", "not-empty.en")
        self.assertTrue(contract.ok)
        self.assertEqual([line.text for line in contract.lines], ["text", ""])

    def test_two_request_blocks_are_diagnosed(self):
        contract = read_contract("en 0.2\n#? one\n\n#? two\n", "blocks.en")
        self.assertIn("EN-E301", self.codes(contract))

    def test_request_and_instructions_cannot_be_mixed(self):
        contract = read_contract("en 0.2\n#? one\nset total to 5.\n", "mixed.en")
        self.assertIn("EN-E302", self.codes(contract))

    def test_no_content_is_diagnosed(self):
        contract = read_contract("en 0.2\n# ordinary documentation\n", "empty-source.en")
        self.assertIn("EN-E305", self.codes(contract))

    def test_request_like_documentation_before_instructions_is_not_warned(self):
        contract = read_contract(
            "en 0.2\n# Find two numbers that add up to the target.\nset total to 5.\n",
            "instructions.en",
        )
        self.assertEqual(contract.form, "instructions")
        self.assertNotIn("EN-W402", self.codes(contract))

    def test_request_like_documentation_without_instructions_is_warned(self):
        contract = read_contract("en 0.2\n# Find two numbers that add up to the target.\n", "docs.en")
        self.assertIn("EN-W402", self.codes(contract))

    def test_repeated_and_conflicting_targets_have_distinct_codes(self):
        repeated = read_contract("en 0.2\ntarget python\ntarget python\nset total to 5.\n", "repeat.en")
        conflict = read_contract("en 0.2\ntarget python\ntarget javascript\nset total to 5.\n", "conflict.en")
        self.assertIn("EN-E205", self.codes(repeated))
        self.assertIn("EN-E201", self.codes(conflict))

    def test_target_casefolding_is_legacy_only(self):
        legacy = read_contract("en 0.1\ntarget JavaScript\nset total to 5.\n", "legacy-target.en")
        current = read_contract("en 0.2\ntarget JavaScript\nset total to 5.\n", "current-target.en")
        self.assertEqual(legacy.target, "javascript")
        self.assertIn("EN-E202", self.codes(current))

    def test_alias_is_rejected_only_in_02(self):
        old = read_contract("en 0.1\nimport codeinpython library\nset total to 5.\n", "old-alias.en")
        current = read_contract("en 0.2\nimport codeinpython library\nset total to 5.\n", "new-alias.en")
        self.assertTrue(old.ok)
        self.assertIn("EN-E203", self.codes(current))


if __name__ == "__main__":
    unittest.main()
