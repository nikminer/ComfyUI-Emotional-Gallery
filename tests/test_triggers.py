import importlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

import test_gallery

triggers = importlib.import_module(test_gallery.PACKAGE + ".triggers")


class TriggerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "character.safetensors"
        self.path.write_bytes(b"unused")

    def test_lora_manager_nested_groups_and_case_insensitive_deduplication(self):
        data = {"trainedWords": [], "civitai": {"trainedWords": ["character", "Character", "character, long hair, red hair"]}}
        self.path.with_suffix(".metadata.json").write_text(json.dumps(data), encoding="utf-8")
        result = triggers.read_trigger_words(self.path)
        self.assertEqual(result["groups"], ["character", "character, long hair, red hair"])

    def test_manually_curated_words_take_priority_over_alternate_outfit_groups(self):
        data = {"trainedWords": ["character, long hair"], "civitai": {"trainedWords": ["maid outfit", "uniform"]}}
        self.path.with_suffix(".metadata.json").write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(triggers.read_trigger_words(self.path)["groups"], ["character, long hair"])

    def test_marked_description_supports_html_and_plain_text_without_using_unmarked_prose(self):
        data = {"description": "<h3>Trigger words</h3><p><code>character, purple eyes</code></p><p>Other description</p>"}
        self.assertEqual(triggers.extract_groups(data), ["character, purple eyes"])
        self.assertEqual(triggers.extract_groups({"notes": "Trigger words: `character, smile`"}), ["character, smile"])
        self.assertEqual(triggers.extract_groups({"description": "This model has purple eyes."}), [])

    def test_safetensors_header_reads_explicit_activation_metadata_only(self):
        header = json.dumps({"__metadata__": {"modelspec.trigger_phrase": "character, blue eyes", "ss_tag_frequency": "{\"other\":100}"}}).encode()
        self.path.write_bytes(struct.pack("<Q", len(header)) + header + b"not_read_tensor_data")
        self.assertEqual(triggers.read_trigger_words(self.path)["groups"], ["character, blue eyes"])

    def test_bad_sidecar_falls_back_and_bad_header_is_bounded(self):
        self.path.with_suffix(".metadata.json").write_text("{invalid", encoding="utf-8")
        self.path.with_suffix(".info.json").write_text(json.dumps({"trainedWords": [{"word": "character"}]}), encoding="utf-8")
        result = triggers.read_trigger_words(self.path)
        self.assertEqual(result["groups"], ["character"])
        self.assertTrue(result["warnings"])
        self.path.with_suffix(".info.json").unlink()
        self.path.write_bytes(struct.pack("<Q", 2**63))
        self.assertEqual(triggers.read_trigger_words(self.path)["groups"], [])
