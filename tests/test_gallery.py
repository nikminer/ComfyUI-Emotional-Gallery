import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

PACKAGE = "emotional_gallery_test"
namespace = types.ModuleType(PACKAGE)
namespace.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[PACKAGE] = namespace
gallery = importlib.import_module(PACKAGE + ".gallery")
emotions = importlib.import_module(PACKAGE + ".emotions")


class GalleryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.checkpoint = self.root / "checkpoint.safetensors"
        self.lora = self.root / "character.safetensors"
        self.checkpoint.write_bytes(b"checkpoint")
        self.lora.write_bytes(b"lora")
        self.clip = self.root / "qwen.safetensors"
        self.vae = self.root / "vae.safetensors"
        self.clip.write_bytes(b"clip")
        self.vae.write_bytes(b"vae")
        self.store = gallery.GalleryStore(self.root / "cache")
        self.catalogs = {"checkpoints": [self.checkpoint.name], "diffusion_models": [self.checkpoint.name], "text_encoders": [self.clip.name], "vaes": [self.vae.name], "vae": [self.vae.name], "loras": [self.lora.name], "samplers": ["euler"], "schedulers": ["normal"]}
        self.settings = gallery.normalize_settings({"ckpt_name": self.checkpoint.name, "lora_name": self.lora.name}, self.catalogs)

    def profile(self, settings=None):
        return self.store.ensure_profile(settings or self.settings, self.checkpoint, self.lora)

    def anima_settings(self):
        return gallery.normalize_settings({**self.settings, "model_family": "anima", "unet_name": self.checkpoint.name, "clip_name": self.clip.name, "vae_name": self.vae.name}, self.catalogs)

    def test_anima_recipe_loads_separate_models_and_16_channel_latent(self):
        settings = self.anima_settings()
        prompt = gallery.build_prompt(settings, "a" * 32, "smile")
        self.assertNotIn("ckpt_name", settings)
        self.assertEqual(prompt["1"]["class_type"], "EGDiffusionLoader")
        self.assertEqual(prompt["9"]["inputs"], {"clip_name": self.clip.name, "type": "stable_diffusion"})
        self.assertEqual(prompt["2"]["inputs"]["clip"], ["9", 0])
        self.assertEqual(prompt["5"]["class_type"], "EmptySD3LatentImage")
        self.assertEqual(prompt["6"]["inputs"]["model"], ["11", 0])
        self.assertEqual(prompt["11"]["inputs"]["shift"], 3.0)
        self.assertEqual(prompt["7"]["inputs"]["vae"], ["10", 0])

    def test_anima_needs_encoder_and_vae_but_no_checkpoint(self):
        settings = self.anima_settings()
        catalogs = {**self.catalogs, "checkpoints": []}
        self.assertEqual(gallery.normalize_settings(settings, catalogs), settings)
        for changes in ({"clip_name": "missing"}, {"vae_name": "missing"}, {"unet_name": "../missing"}, {"shift": float("nan")}, {"width": 520}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                gallery.normalize_settings({**settings, **changes}, catalogs)

    def test_anima_model_files_and_shift_invalidate_cache(self):
        settings = self.anima_settings()
        def profile(values=settings):
            return self.store.ensure_profile(values, self.checkpoint, self.lora, clip_path=self.clip, vae_path=self.vae)
        original = profile()
        self.assertNotEqual(original["id"], profile({**settings, "shift": 4.0})["id"])
        for path in (self.clip, self.vae, self.checkpoint, self.lora):
            previous = profile()
            path.write_bytes(b"replaced " + path.read_bytes())
            self.assertNotEqual(previous["id"], profile()["id"])

    def test_checkpoint_cache_keeps_original_key_after_upgrade(self):
        original = self.profile()
        normalized = gallery.normalize_settings({**self.settings, "model_family": "checkpoint", "unet_name": "unused", "shift": 6.0}, self.catalogs)
        self.assertEqual(normalized, self.settings)
        self.assertEqual(original["id"], self.profile(normalized)["id"])

    def family_settings(self, family):
        profile = gallery.MODEL_PROFILES[family]
        values = {**self.settings, "model_family": family, "width": 1024, "height": 1024}
        for key in profile["model_fields"]:
            values[key] = self.catalogs[gallery.MODEL_FIELDS[key]["catalog"]][0]
        return gallery.normalize_settings(values, self.catalogs)

    def test_all_profiles_require_only_their_model_files(self):
        for family, profile in gallery.MODEL_PROFILES.items():
            with self.subTest(family=family):
                settings = self.family_settings(family)
                self.assertEqual(set(settings) & set(gallery.MODEL_FIELDS), set(profile["model_fields"]))
                for key in ("shift", "guidance"):
                    self.assertEqual(key in settings, key in profile["defaults"])
                for key in profile["model_fields"]:
                    with self.assertRaises(ValueError):
                        gallery.normalize_settings({**settings, key: "../missing.safetensors"}, self.catalogs)
        for family in ("unsupported", [], None):
            with self.assertRaises(ValueError):
                gallery.normalize_settings({**self.settings, "model_family": family}, self.catalogs)

    def test_named_checkpoint_profiles_use_native_sd_latents(self):
        for family in ("illustrious", "pony", "sdxl", "sd15"):
            prompt = gallery.build_prompt(self.family_settings(family), "a" * 32, "neutral")
            self.assertEqual(prompt["1"]["class_type"], "EGCheckpointLoader")
            self.assertEqual(prompt["5"]["class_type"], "EmptyLatentImage")
            self.assertEqual(prompt["7"]["inputs"]["vae"], ["1", 2])
            self.assertNotIn("9", prompt)

    def test_flux_guidance_and_schnell_recipes_are_distinct(self):
        dev = self.family_settings("flux")
        dev["guidance"] = 4.0
        prompt = gallery.build_prompt(dev, "a" * 32, "smile")
        self.assertEqual(prompt["9"]["class_type"], "EGDualTextEncoderLoader")
        self.assertEqual(prompt["9"]["inputs"]["type"], "flux")
        self.assertEqual(prompt["5"]["class_type"], "EmptySD3LatentImage")
        self.assertEqual(prompt["12"]["inputs"], {"conditioning": ["3", 0], "guidance": 4.0})
        self.assertEqual(prompt["6"]["inputs"]["positive"], ["12", 0])
        schnell = gallery.build_prompt(self.family_settings("flux_schnell"), "a" * 32, "smile")
        self.assertNotIn("12", schnell)
        self.assertEqual(schnell["6"]["inputs"]["positive"], ["3", 0])

    def test_qwen_and_z_image_use_the_correct_encoder_and_shift(self):
        for family, encoder in (("qwen_image", "qwen_image"), ("z_image", "lumina2"), ("z_image_turbo", "lumina2")):
            settings = self.family_settings(family)
            prompt = gallery.build_prompt(settings, "a" * 32, "neutral")
            self.assertEqual(prompt["9"]["inputs"]["type"], encoder)
            self.assertEqual(prompt["5"]["class_type"], "EmptySD3LatentImage")
            self.assertEqual(prompt["11"]["class_type"], "ModelSamplingAuraFlow")
            self.assertEqual(prompt["11"]["inputs"]["shift"], settings["shift"])

    def test_sd3_loads_three_encoders_and_checkpoint_vae(self):
        prompt = gallery.build_prompt(self.family_settings("sd3"), "a" * 32, "neutral")
        self.assertEqual(prompt["1"]["class_type"], "EGCheckpointLoader")
        self.assertEqual(prompt["9"]["class_type"], "EGTripleTextEncoderLoader")
        self.assertEqual(set(prompt["9"]["inputs"]), {"clip_name1", "clip_name2", "clip_name3"})
        self.assertEqual(prompt["11"]["class_type"], "ModelSamplingSD3")
        self.assertEqual(prompt["7"]["inputs"]["vae"], ["1", 2])

    def test_every_extra_encoder_participates_in_cache_identity(self):
        second = self.root / "second.safetensors"
        third = self.root / "third.safetensors"
        second.write_bytes(b"second")
        third.write_bytes(b"third")
        for family in ("flux", "sd3"):
            settings = self.family_settings(family)
            extras = (second,) if family == "flux" else (second, third)
            options = {"clip_path": self.clip, "extra_clip_paths": extras}
            if family == "flux":
                options["vae_path"] = self.vae
            original = self.store.ensure_profile(settings, self.checkpoint, self.lora, **options)
            for path in extras:
                path.write_bytes(path.read_bytes() + b"replacement")
                updated = self.store.ensure_profile(settings, self.checkpoint, self.lora, **options)
                self.assertNotEqual(original["id"], updated["id"])
                original = updated

    def test_recipe_stays_identical_except_expression(self):
        profile = self.profile()
        first = gallery.build_prompt(self.settings, profile["id"], "smile")
        second = gallery.build_prompt(self.settings, profile["id"], "angry")
        self.assertEqual(first["6"]["inputs"], second["6"]["inputs"])
        self.assertNotEqual(first["2"]["inputs"]["emotion"], second["2"]["inputs"]["emotion"])
        self.assertEqual(first["3"]["inputs"]["text"], ["2", 2])
        self.assertEqual(first["8"]["inputs"]["profile_id"], profile["id"])
        self.assertEqual(first["5"]["inputs"]["batch_size"], 1)

    def test_cache_survives_store_recreation(self):
        profile = self.profile()
        self.store.save(profile["id"], "smile", Image.new("RGB", (640, 512), "pink"))
        reopened = gallery.GalleryStore(self.store.root)
        self.assertEqual(len(reopened.profiles(self.lora.name)), 1)
        image_path = reopened.image_path(profile["id"], "smile")
        with Image.open(image_path) as image:
            self.assertEqual(image.size, (640, 512))
            metadata = json.loads(image.info["emotional_gallery"])
            self.assertEqual(metadata["emotion"], "smile")
        with Image.open(reopened.image_path(profile["id"], "smile", True)) as image:
            self.assertLessEqual(max(image.size), 320)

    def test_settings_create_separate_profiles(self):
        original = self.profile()
        for key, value in (("cfg", 7.5), ("seed", 111), ("trigger_words", "character"), ("width", 512), ("strength_clip", 0.7), ("negative_prompt", "different")):
            with self.subTest(key=key):
                self.assertNotEqual(original["id"], self.profile({**self.settings, key: value})["id"])
        self.assertEqual(original["id"], self.profile()["id"])

    def test_custom_library_persists_without_invalidating_existing_cache(self):
        original = self.profile()
        image = self.store.save(original["id"], "smile", Image.new("RGB", (8, 8)))
        custom = self.store.add_emotion("  Скепсис  ", "  skeptical expression  ")
        reopened = gallery.GalleryStore(self.store.root)
        self.assertEqual(reopened.emotions()[custom["id"]]["label"], "Скепсис")
        self.assertEqual(custom["prompt"], "skeptical expression")
        updated = self.profile()
        self.assertEqual(updated["id"], original["id"])
        self.assertEqual(updated["images"]["smile"]["version"], image["version"])
        self.assertEqual(updated["emotions"][custom["id"]], custom)
        self.assertEqual(len(reopened.public(updated)["emotions"]), len(emotions.ACTIVE_EMOTION_MAP) + 1)

    def test_custom_recipe_and_cache_keep_expression_snapshot(self):
        custom = self.store.add_emotion("Скепсис", "skeptical expression, one eyebrow raised")
        profile = self.profile()
        recipe = gallery.build_prompt(self.settings, profile["id"], custom["id"], custom)
        self.assertEqual(recipe["2"]["inputs"]["emotion"], "custom")
        self.assertEqual(recipe["2"]["inputs"]["custom_expression"], custom["prompt"])
        self.assertEqual(recipe["8"]["inputs"]["emotion"], custom["id"])
        self.store.save(profile["id"], custom["id"], Image.new("RGB", (8, 8)))
        (self.store.root / "custom_emotions.json").write_text("{}", encoding="utf-8")
        with Image.open(self.store.image_path(profile["id"], custom["id"])) as image:
            metadata = json.loads(image.info["emotional_gallery"])
            self.assertEqual(metadata["emotion_definition"], custom)
            self.assertIn(custom["prompt"], metadata["positive_prompt"])
        public = self.store.public(self.store.read(profile["id"]))
        self.assertIn(custom, public["emotions"])
        self.assertIn(custom["id"], public["images"])

    def test_custom_library_rejects_invalid_text_and_duplicate_names(self):
        for label, prompt in (("", "expression"), ("name", ""), ("x" * 81, "expression"), ("name", "x" * 4001), (None, "expression")):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.store.add_emotion(label, prompt)
        self.store.add_emotion("Скепсис", "skeptical expression")
        for label in ("  СКЕПСИС  ", emotions.EMOTION_MAP["smile"]["label"]):
            with self.assertRaises(ValueError):
                self.store.add_emotion(label, "expression")

    def test_custom_registry_cannot_inject_path_ids(self):
        self.store.root.mkdir()
        invalid = {"../../outside": {"id": "../../outside", "label": "name", "prompt": "expression"}}
        (self.store.root / "custom_emotions.json").write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.emotions()

    def test_expanded_library_preserves_original_cache_identity(self):
        profile = self.profile()
        legacy = {key: {"id": key, "label": label, "prompt": prompt} for key, label, prompt in emotions.EMOTIONS}
        self.assertEqual(profile["identity"]["emotions"], legacy)
        self.assertEqual(len(emotions.ACTIVE_EMOTION_MAP), 81)
        self.assertEqual(len({item["label"] for item in emotions.ACTIVE_EMOTION_MAP.values()}), 81)
        self.assertTrue(all(item["category"] in emotions.CATEGORIES for item in emotions.ACTIVE_EMOTION_MAP.values()))

    def test_custom_category_persists_and_rejects_unknown_values(self):
        custom = self.store.add_emotion("Скепсис", "skeptical expression", "confidence")
        self.assertEqual(gallery.GalleryStore(self.store.root).emotions()[custom["id"]]["category"], "sfw")
        with self.assertRaises(ValueError):
            self.store.add_emotion("Name", "expression", "../outside")

    def test_old_custom_categories_are_presented_in_two_groups_without_rewriting_files(self):
        custom = self.store.add_emotion("Skepticism", "skeptical expression", "sfw")
        path = self.store.root / "custom_emotions.json"
        legacy = json.loads(path.read_text(encoding="utf-8"))
        legacy[custom["id"]]["category"] = "confidence"
        path.write_text(json.dumps(legacy), encoding="utf-8")
        original = path.read_bytes()
        self.assertEqual(self.store.emotions()[custom["id"]]["category"], "sfw")
        profile = self.profile()
        profile["emotions"][custom["id"]]["category"] = "custom"
        self.store.write(profile)
        self.assertEqual(next(item for item in self.store.public(profile)["emotions"] if item["id"] == custom["id"])["category"], "sfw")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(set(emotions.CATEGORIES), {"sfw", "nsfw"})
        self.assertEqual(sum(item["category"] == "sfw" for item in emotions.ACTIVE_EMOTION_MAP.values()), 49)

    def test_curated_library_has_distinct_prompts_and_english_labels(self):
        definitions = list(emotions.ACTIVE_EMOTION_MAP.values())
        fingerprints = [frozenset(tag.strip().casefold() for tag in item["prompt"].split(",")) for item in definitions]
        self.assertEqual(len(fingerprints), len(set(fingerprints)))
        self.assertEqual(sum(item["category"] == "nsfw" for item in definitions), 32)
        self.assertTrue(all(item["label_en"] and not any("А" <= char <= "я" for char in item["label_en"]) for item in definitions))
        self.assertTrue(all(target in emotions.ACTIVE_EMOTION_MAP for target in emotions.RETIRED_EMOTIONS.values()))

    def test_subcategories_cover_every_active_expression_once_in_its_direction(self):
        ids = []
        for category, subgroups in emotions.SUBCATEGORY_MEMBERS.items():
            for subgroup, members in subgroups.items():
                self.assertIn(subgroup, emotions.SUBCATEGORIES[category])
                for emotion_id in members:
                    item = emotions.ACTIVE_EMOTION_MAP[emotion_id]
                    self.assertEqual((item["category"], item["subcategory"]), (category, subgroup))
                    ids.append(emotion_id)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(emotions.ACTIVE_EMOTION_MAP))
        self.assertEqual(set(emotions.SUBCATEGORY_MEMBERS["nsfw"]["ahegao"]), {"ahegao", "ahegao_rolled", "ahegao_tears", "ahegao_hearts", "ahegao_closed"})

    def test_custom_subcategory_persists_without_resetting_cached_previews(self):
        original = self.profile()
        self.store.save(original["id"], "smile", Image.new("RGB", (8, 8)))
        image_path = self.store.image_path(original["id"], "smile")
        saved_bytes = image_path.read_bytes()
        custom = self.store.add_emotion("Wide smile", "wide smile, closed eyes", "sfw", "smile")
        self.assertEqual(gallery.GalleryStore(self.store.root).emotions()[custom["id"]]["subcategory"], "smile")
        updated = self.profile()
        self.assertEqual(updated["id"], original["id"])
        self.assertEqual(image_path.read_bytes(), saved_bytes)
        self.assertEqual(next(item for item in self.store.public(updated)["emotions"] if item["id"] == custom["id"])["subcategory"], "smile")

    def test_custom_subcategory_rejects_other_direction_and_legacy_defaults_to_custom(self):
        for category, subgroup in (("sfw", "ahegao"), ("nsfw", "neutral"), ("sfw", {}), ("sfw", "../outside")):
            with self.subTest(category=category, subgroup=subgroup), self.assertRaises(ValueError):
                self.store.add_emotion("Name", "expression", category, subgroup)
        custom = self.store.add_emotion("Skepticism", "skeptical expression")
        path = self.store.root / "custom_emotions.json"
        legacy = json.loads(path.read_text(encoding="utf-8"))
        legacy[custom["id"]].pop("subcategory")
        path.write_text(json.dumps(legacy), encoding="utf-8")
        original = path.read_bytes()
        self.assertEqual(self.store.emotions()[custom["id"]]["subcategory"], "custom")
        self.assertEqual(path.read_bytes(), original)

    def test_retired_variants_keep_cached_images_and_saved_workflows(self):
        profile = self.profile()
        retired = "nsfw_seductive_smile"
        image = self.store.save(profile["id"], retired, Image.new("RGB", (8, 8), "pink"))
        original_bytes = self.store.image_path(profile["id"], retired).read_bytes()
        reopened = gallery.GalleryStore(self.store.root)
        public = reopened.public(reopened.read(profile["id"]))
        self.assertNotIn(retired, [item["id"] for item in public["emotions"]])
        self.assertNotIn(retired, public["images"])
        self.assertEqual(reopened.image_path(profile["id"], retired).read_bytes(), original_bytes)
        self.assertEqual(reopened.read(profile["id"])["images"][retired], image)
        self.assertIn(retired, emotions.EMOTION_MAP)
        self.assertIn("seductive smile", emotions.expression_prompt("portrait", "character", retired))

    def test_deleted_profile_restores_exact_cached_images(self):
        profile = self.profile()
        self.store.save(profile["id"], "smile", Image.new("RGB", (8, 8), "pink"))
        original = self.store.image_path(profile["id"], "smile").read_bytes()
        archived = self.store.archive(profile["id"])
        self.assertEqual(self.store.profiles(self.lora.name), [])
        with self.assertRaises(FileNotFoundError):
            self.store.read(profile["id"])
        reopened = gallery.GalleryStore(self.store.root)
        restored = reopened.restore(archived["token"])
        self.assertEqual(restored["id"], profile["id"])
        self.assertEqual(reopened.image_path(profile["id"], "smile").read_bytes(), original)
        with self.assertRaises(FileNotFoundError):
            reopened.restore(archived["token"])

    def test_restore_cannot_overwrite_recreated_profile_or_escape_paths(self):
        profile = self.profile()
        archived = self.store.archive(profile["id"])
        self.profile()
        with self.assertRaises(FileExistsError):
            self.store.restore(archived["token"])
        self.assertTrue((self.store.trash_directory(archived["token"]) / "manifest.json").exists())
        for token in ("../outside", None, "a" * 31):
            with self.assertRaises(ValueError):
                self.store.restore(token)

    def test_model_replacement_invalidates_profile(self):
        original = self.profile()
        self.lora.write_bytes(b"replacement lora")
        self.assertNotEqual(original["id"], self.profile()["id"])
        original = self.profile()
        self.checkpoint.write_bytes(b"replacement checkpoint")
        self.assertNotEqual(original["id"], self.profile()["id"])

    def test_regeneration_replaces_files(self):
        profile = self.profile()
        old = self.store.save(profile["id"], "smile", Image.new("RGB", (8, 8)))
        old_path = self.store.image_path(profile["id"], "smile")
        new = self.store.save(profile["id"], "smile", Image.new("RGB", (16, 16)))
        self.assertNotEqual(old["version"], new["version"])
        self.assertFalse(old_path.exists())
        self.assertEqual(len(self.store.read(profile["id"])["images"]), 1)

    def test_deleted_cache_is_not_reported_ready(self):
        profile = self.profile()
        self.store.save(profile["id"], "smile", Image.new("RGB", (8, 8)))
        self.store.image_path(profile["id"], "smile").unlink()
        self.assertNotIn("smile", self.store.public(self.store.read(profile["id"]))["images"])

    def test_path_escape_is_rejected(self):
        for value in ("../outside", "C:\\Windows", "a" * 31, "a" * 32 + "/../", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store.directory(value)
        profile = self.profile()
        with self.assertRaises(ValueError):
            self.store.image_path(profile["id"], "../manifest.json")

    def test_manifest_image_path_cannot_escape(self):
        profile = self.profile()
        profile["images"]["smile"] = {"filename": "../../checkpoint.safetensors", "thumbnail": "../outside"}
        self.store.write(profile)
        with self.assertRaises(FileNotFoundError):
            self.store.image_path(profile["id"], "smile")

    def test_64_bit_seed_is_preserved_for_browser(self):
        settings = gallery.normalize_settings({**self.settings, "seed": 2**64 - 1}, self.catalogs)
        profile = self.profile(settings)
        self.assertEqual(self.store.public(profile)["settings"]["seed"], "18446744073709551615")
        self.assertEqual(gallery.build_prompt(settings, profile["id"], "smile")["6"]["inputs"]["seed"], 2**64 - 1)

    def test_validation_rejects_invalid_files_and_numbers(self):
        for changes in ({"lora_name": "../missing"}, {"steps": True}, {"cfg": float("nan")}, {"width": 513}, {"seed": -1}, {"steps": "24"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                gallery.normalize_settings({**self.settings, **changes}, self.catalogs)

    def test_prompt_keeps_trigger_and_expression(self):
        prompt = emotions.expression_prompt("portrait", "my_character", "wink")
        self.assertTrue(prompt.startswith("my_character, portrait, "))
        self.assertIn("winking", prompt)
        with self.assertRaises(ValueError):
            emotions.expression_prompt("portrait", "character", "missing")


if __name__ == "__main__":
    unittest.main()
