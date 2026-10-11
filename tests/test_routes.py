import importlib
import json
import sys
import types
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image

import test_gallery

PACKAGE = test_gallery.PACKAGE


class FakeQueue:
    def __init__(self):
        self.pending = []
        self.running = []
        self.history = {}

    def put(self, item):
        self.pending.append(item)

    def get_current_queue_volatile(self):
        return list(self.running), list(self.pending)

    def get_history(self, prompt_id):
        return {prompt_id: self.history[prompt_id]} if prompt_id in self.history else {}

    def delete_queue_item(self, predicate):
        for item in self.pending:
            if predicate(item):
                self.pending.remove(item)
                return True
        return False


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fixture = test_gallery.GalleryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.store = fixture.store
        self.queue = FakeQueue()
        self.validations = []
        self.validation_error = False
        self.server = types.SimpleNamespace(routes=web.RouteTableDef(), prompt_queue=self.queue, number=0, node_replace_manager=types.SimpleNamespace(apply_replacements=lambda prompt: None))

        async def validate(prompt_id, prompt, targets):
            self.validations.append(prompt)
            return (False, {"message": "invalid"}, [], {}) if self.validation_error else (True, None, ["8"], {})

        folder_paths = types.ModuleType("folder_paths")
        folder_paths.get_filename_list = lambda category: fixture.catalogs[category]
        model_paths = {"checkpoints": fixture.checkpoint, "diffusion_models": fixture.checkpoint, "text_encoders": fixture.clip, "vae": fixture.vae, "loras": fixture.lora}
        folder_paths.get_full_path_or_raise = lambda category, name: model_paths[category]
        server_module = types.ModuleType("server")
        server_module.PromptServer = types.SimpleNamespace(instance=self.server)
        execution_module = types.ModuleType("execution")
        execution_module.validate_prompt = validate
        comfy_module = types.ModuleType("comfy")
        samplers = types.ModuleType("comfy.samplers")
        samplers.KSampler = types.SimpleNamespace(SAMPLERS=["euler"], SCHEDULERS=["normal"])
        comfy_module.samplers = samplers
        namespace = sys.modules[PACKAGE]
        namespace.STORE = self.store
        sys.modules.pop(PACKAGE + ".routes", None)
        with patch.dict(sys.modules, {"folder_paths": folder_paths, "server": server_module, "execution": execution_module, "comfy": comfy_module, "comfy.samplers": samplers}):
            self.routes = importlib.import_module(PACKAGE + ".routes")
        self.routes.register_routes()
        application = web.Application()
        application.add_routes(self.server.routes)
        self.client = TestClient(TestServer(application))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)

    async def generate(self, **extras):
        response = await self.client.post("/emotional-gallery/generate", json={"settings": self.fixture.settings, **extras})
        return response, await response.json()

    async def test_missing_only_and_no_duplicate_jobs(self):
        profile = self.fixture.profile()
        self.store.save(profile["id"], "smile", Image.new("RGB", (8, 8)))
        response, data = await self.generate()
        self.assertEqual(response.status, 200)
        self.assertEqual(data["queued"], len(test_gallery.emotions.ACTIVE_EMOTION_MAP) - 1)
        self.assertEqual(len(self.queue.pending), len(test_gallery.emotions.ACTIVE_EMOTION_MAP) - 1)
        response, data = await self.generate()
        self.assertEqual(data["queued"], 0)
        self.assertEqual(len(self.queue.pending), len(test_gallery.emotions.ACTIVE_EMOTION_MAP) - 1)

    async def test_anima_generation_uses_all_model_catalogs(self):
        response = await self.client.post("/emotional-gallery/generate", json={"settings": self.fixture.anima_settings(), "emotions": ["smile"]})
        data = await response.json()
        self.assertEqual(response.status, 200)
        self.assertEqual(data["queued"], 1)
        self.assertEqual(self.queue.pending[0][2]["1"]["class_type"], "EGDiffusionLoader")
        identity = self.store.read(data["profile"]["id"])["identity"]
        self.assertEqual(identity["text_encoder"]["path"], str(self.fixture.clip.resolve()))
        self.assertEqual(identity["vae"]["path"], str(self.fixture.vae.resolve()))

    async def test_jobs_use_requesting_window_for_execution_lifecycle(self):
        response, data = await self.generate(emotions=["smile", "angry"], client_id="gallery-window")
        self.assertEqual(response.status, 200)
        self.assertEqual(data["queued"], 2)
        self.assertEqual({item[3]["client_id"] for item in self.queue.pending}, {"gallery-window"})
        profile_id = data["profile"]["id"]
        self.queue.pending.clear()
        _, data = await self.generate(emotions=["smile"], client_id="another-window")
        self.assertEqual(data["profile"]["id"], profile_id)
        self.assertEqual(self.queue.pending[0][3]["client_id"], "another-window")

    async def test_headless_jobs_do_not_broadcast_unfinished_progress(self):
        response, data = await self.generate(emotions=["smile", "angry"])
        self.assertEqual(response.status, 200)
        clients = {item[3]["client_id"] for item in self.queue.pending}
        self.assertEqual(len(clients), 1)
        self.assertTrue(next(iter(clients)))

    async def test_invalid_client_ids_never_reach_queue(self):
        for client_id in ("", "   ", 5, {}, True, "x" * 201):
            response, _ = await self.generate(emotions=["smile"], client_id=client_id)
            self.assertEqual(response.status, 400)
        self.assertEqual(self.queue.pending, [])

    async def test_config_exposes_diffusion_models_and_all_loras(self):
        response = await self.client.get("/emotional-gallery/config")
        data = await response.json()
        self.assertEqual(data["diffusion_models"], self.fixture.catalogs["diffusion_models"])
        self.assertEqual(data["loras"], self.fixture.catalogs["loras"])
        self.assertEqual(data["text_encoders"], self.fixture.catalogs["text_encoders"])
        self.assertEqual(data["vaes"], self.fixture.catalogs["vaes"])

    async def test_curated_defaults_skip_retired_variants(self):
        response = await self.client.get("/emotional-gallery/config")
        config = await response.json()
        self.assertEqual(len(config["emotions"]), 81)
        self.assertTrue(all(item["label_en"] for item in config["emotions"] + config["categories"]))
        self.assertFalse({item["id"] for item in config["emotions"]} & test_gallery.emotions.RETIRED_EMOTIONS.keys())
        _, data = await self.generate()
        self.assertEqual(data["queued"], 81)
        self.assertFalse({item[3]["eg_emotion"] for item in self.queue.pending} & test_gallery.emotions.RETIRED_EMOTIONS.keys())

    async def test_custom_emotion_creation_generation_and_cache_reuse(self):
        original = self.fixture.profile()
        self.store.save(original["id"], "smile", Image.new("RGB", (8, 8)))
        response = await self.client.post("/emotional-gallery/emotions", json={"label": "Скепсис", "prompt": "skeptical expression"})
        data = await response.json()
        self.assertEqual(response.status, 201)
        custom = data["emotion"]
        self.assertEqual(len(data["emotions"]), len(test_gallery.emotions.ACTIVE_EMOTION_MAP) + 1)
        response, data = await self.generate(emotions=[custom["id"]])
        self.assertEqual(response.status, 200)
        self.assertEqual(data["queued"], 1)
        self.assertEqual(data["profile"]["id"], original["id"])
        recipe = self.queue.pending[0][2]
        self.assertEqual(recipe["2"]["inputs"]["custom_expression"], custom["prompt"])
        self.assertEqual(recipe["8"]["inputs"]["emotion"], custom["id"])
        self.queue.pending.clear()
        self.store.save(original["id"], custom["id"], Image.new("RGB", (8, 8)))
        _, data = await self.generate(emotions=[custom["id"], "smile"])
        self.assertEqual(data["queued"], 0)
        response = await self.client.get(f"/emotional-gallery/image/{original['id']}/{custom['id']}?thumbnail=1")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "image/webp")

    async def test_custom_emotion_invalid_requests_do_not_change_library(self):
        for values in ({"label": "", "prompt": "expression"}, {"label": "name", "prompt": ""}, {"label": test_gallery.emotions.EMOTION_MAP["smile"]["label"], "prompt": "expression"}):
            response = await self.client.post("/emotional-gallery/emotions", json=values)
            self.assertEqual(response.status, 400)
        self.assertFalse((self.store.root / "custom_emotions.json").exists())
        self.assertEqual(self.queue.pending, [])

    async def test_all_validation_happens_before_queue_mutation(self):
        self.validation_error = True
        response, _ = await self.generate()
        self.assertEqual(response.status, 400)
        self.assertEqual(len(self.queue.pending), 0)

    async def test_cancel_preserves_unrelated_and_running_jobs(self):
        _, data = await self.generate(emotions=["smile", "angry"])
        profile_id = data["profile"]["id"]
        self.queue.running.append(self.queue.pending.pop())
        self.queue.pending.append((99, "unrelated", {}, {}, [], {}))
        response = await self.client.post(f"/emotional-gallery/cancel/{profile_id}", json={})
        result = await response.json()
        self.assertEqual(result["removed"], 1)
        self.assertEqual(self.queue.pending[0][1], "unrelated")
        self.assertEqual(len(self.queue.running), 1)

    async def test_force_regenerates_only_selected_emotion(self):
        profile = self.fixture.profile()
        self.store.save(profile["id"], "smile", Image.new("RGB", (8, 8)))
        _, data = await self.generate(emotions=["smile"], force=True)
        self.assertEqual(data["queued"], 1)
        self.assertEqual(self.queue.pending[0][3]["eg_emotion"], "smile")

    async def test_failed_jobs_have_actionable_status(self):
        _, data = await self.generate(emotions=["smile"])
        item = self.queue.pending.pop()
        self.queue.history[item[1]] = {"status": {"status_str": "error", "messages": [["execution_error", {"exception_message": "Incompatible LoRA"}]]}}
        response = await self.client.get(f"/emotional-gallery/profile/{data['profile']['id']}")
        profile = await response.json()
        self.assertEqual(profile["states"]["smile"], {"status": "error", "message": "Incompatible LoRA"})
        _, data = await self.generate(emotions=["smile"])
        self.assertEqual(data["queued"], 1)

    async def test_invalid_emotions_never_reach_queue(self):
        response, _ = await self.generate(emotions=["../../outside"])
        self.assertEqual(response.status, 400)
        self.assertEqual(self.queue.pending, [])

    async def test_image_endpoint_and_missing_files(self):
        profile = self.fixture.profile()
        self.store.save(profile["id"], "smile", Image.new("RGB", (8, 8)))
        response = await self.client.get(f"/emotional-gallery/image/{profile['id']}/smile?thumbnail=1")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "image/webp")
        response = await self.client.get(f"/emotional-gallery/image/{profile['id']}/angry")
        self.assertEqual(response.status, 404)

    async def test_category_generation_queues_only_missing_selected_members(self):
        members = [key for key, item in test_gallery.emotions.ACTIVE_EMOTION_MAP.items() if item["category"] == "nsfw"]
        profile = self.fixture.profile()
        self.store.save(profile["id"], members[0], Image.new("RGB", (8, 8)))
        response, data = await self.generate(emotions=members)
        self.assertEqual(response.status, 200)
        self.assertEqual(data["queued"], len(members) - 1)
        self.assertEqual({item[3]["eg_emotion"] for item in self.queue.pending}, set(members[1:]))
        response, data = await self.generate(emotions=members)
        self.assertEqual(data["queued"], 0)

    async def test_subcategory_generation_queues_only_its_missing_variants(self):
        members = test_gallery.emotions.SUBCATEGORY_MEMBERS["nsfw"]["ahegao"]
        profile = self.fixture.profile()
        self.store.save(profile["id"], "ahegao", Image.new("RGB", (8, 8)))
        response, data = await self.generate(emotions=members)
        self.assertEqual(response.status, 200)
        self.assertEqual(data["queued"], 4)
        self.assertEqual({item[3]["eg_emotion"] for item in self.queue.pending}, set(members) - {"ahegao"})

    async def test_config_and_custom_creation_expose_nested_subcategories(self):
        config = await (await self.client.get("/emotional-gallery/config")).json()
        nsfw = next(item for item in config["categories"] if item["id"] == "nsfw")
        self.assertIn({"id": "ahegao", "label": "Ahegao"}, nsfw["subcategories"])
        response = await self.client.post("/emotional-gallery/emotions", json={"label": "Wide smile", "prompt": "wide smile", "category": "sfw", "subcategory": "smile"})
        self.assertEqual(response.status, 201)
        self.assertEqual((await response.json())["emotion"]["subcategory"], "smile")
        response = await self.client.post("/emotional-gallery/emotions", json={"label": "Wrong category", "prompt": "expression", "category": "sfw", "subcategory": "ahegao"})
        self.assertEqual(response.status, 400)
        self.assertNotIn("Wrong category", {item["label"] for item in self.store.emotions().values()})

    async def test_trigger_words_endpoint_reads_selected_lora_and_rejects_unlisted_paths(self):
        self.fixture.lora.with_suffix(".metadata.json").write_text(json.dumps({"trainedWords": ["character, long hair", "smile"]}), encoding="utf-8")
        response = await self.client.get("/emotional-gallery/triggers", params={"lora_name": self.fixture.lora.name})
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["groups"], ["character, long hair", "smile"])
        response = await self.client.get("/emotional-gallery/triggers", params={"lora_name": "../../private.safetensors"})
        self.assertEqual(response.status, 400)

    async def test_archive_and_restore_profile_endpoints(self):
        profile = self.fixture.profile()
        self.store.save(profile["id"], "smile", Image.new("RGB", (8, 8)))
        response = await self.client.post(f"/emotional-gallery/archive/{profile['id']}", json={})
        self.assertEqual(response.status, 200)
        token = (await response.json())["token"]
        response = await self.client.get(f"/emotional-gallery/profile/{profile['id']}")
        self.assertEqual(response.status, 404)
        response = await self.client.post(f"/emotional-gallery/restore/{token}", json={})
        self.assertEqual(response.status, 200)
        self.assertIn("smile", (await response.json())["profile"]["images"])
        response = await self.client.post(f"/emotional-gallery/restore/{token}", json={})
        self.assertEqual(response.status, 404)

    async def test_archive_refuses_running_or_pending_generations(self):
        _, data = await self.generate(emotions=["smile"])
        profile_id = data["profile"]["id"]
        for running in (False, True):
            if running:
                self.queue.running.append(self.queue.pending.pop())
            response = await self.client.post(f"/emotional-gallery/archive/{profile_id}", json={})
            self.assertEqual(response.status, 409)
            self.assertEqual(self.store.read(profile_id)["id"], profile_id)
            self.assertEqual(len(self.queue.running) + len(self.queue.pending), 1)


if __name__ == "__main__":
    unittest.main()
