import asyncio
import logging
import time
import uuid

from aiohttp import web

import comfy.samplers
import execution
import folder_paths
from server import PromptServer

from . import STORE
from .gallery import ANIMA_DEFAULTS, DEFAULTS, build_prompt, normalize_settings
from .emotions import CATEGORIES, CATEGORY_LABELS_EN, SUBCATEGORIES
from .triggers import read_trigger_words

LOGGER = logging.getLogger(__name__)


def catalogs():
    return {
        "checkpoints": folder_paths.get_filename_list("checkpoints"),
        "diffusion_models": folder_paths.get_filename_list("diffusion_models"),
        "text_encoders": folder_paths.get_filename_list("text_encoders"),
        "vaes": folder_paths.get_filename_list("vae"),
        "loras": folder_paths.get_filename_list("loras"),
        "samplers": list(comfy.samplers.KSampler.SAMPLERS),
        "schedulers": list(comfy.samplers.KSampler.SCHEDULERS),
    }


def profile_state(manifest):
    server = PromptServer.instance
    running, pending = server.prompt_queue.get_current_queue_volatile()
    running_ids = {item[1] for item in running}
    pending_ids = {item[1] for item in pending}
    result = STORE.public(manifest)
    states = {}
    for emotion in STORE.profile_emotions(manifest):
        job = manifest.get("jobs", {}).get(emotion)
        state = {"status": "ready" if emotion in result["images"] else "missing"}
        if job:
            prompt_id = job["prompt_id"]
            if prompt_id in running_ids:
                state = {"status": "running"}
            elif prompt_id in pending_ids:
                state = {"status": "pending"}
            else:
                history = server.prompt_queue.get_history(prompt_id).get(prompt_id)
                if history and (history.get("status") or {}).get("status_str") == "error":
                    messages = (history.get("status") or {}).get("messages", [])
                    message = "Ошибка генерации. Проверьте совместимость модели и LoRA."
                    for event, details in messages:
                        if event == "execution_error":
                            message = str(details.get("exception_message", message))[:2000]
                    state = {"status": "error", "message": message}
        states[emotion] = state
    result["states"] = states
    result["active"] = sum(state["status"] in ("running", "pending") for state in states.values())
    return result


def register_routes():
    routes = PromptServer.instance.routes
    generate_lock = asyncio.Lock()

    @routes.get("/emotional-gallery/config")
    async def config(request):
        return web.json_response({**catalogs(), "defaults": DEFAULTS, "anima_defaults": ANIMA_DEFAULTS, "emotions": list(STORE.emotions().values()), "categories": [{"id": key, "label": label, "label_en": CATEGORY_LABELS_EN[key], "subcategories": [{"id": subkey, "label": sublabel} for subkey, sublabel in SUBCATEGORIES[key].items()]} for key, label in CATEGORIES.items()]})

    @routes.post("/emotional-gallery/emotions")
    async def add_emotion(request):
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError("Ожидается название и промпт эмоции")
            definition = STORE.add_emotion(data.get("label"), data.get("prompt"), data.get("category", "sfw"), data.get("subcategory"))
            return web.json_response({"emotion": definition, "emotions": list(STORE.emotions().values())}, status=201)
        except (ValueError, TypeError) as error:
            return web.json_response({"error": str(error)}, status=400)
        except OSError as error:
            LOGGER.exception("Emotional Gallery custom emotion write error")
            return web.json_response({"error": f"Не удалось сохранить эмоцию: {error}"}, status=500)

    @routes.get("/emotional-gallery/triggers")
    async def triggers(request):
        name = request.query.get("lora_name", "")
        if name not in folder_paths.get_filename_list("loras"):
            return web.json_response({"error": "Choose an available LoRA"}, status=400)
        try:
            path = folder_paths.get_full_path_or_raise("loras", name)
            return web.json_response(await asyncio.to_thread(read_trigger_words, path))
        except OSError:
            LOGGER.exception("Emotional Gallery trigger metadata read error")
            return web.json_response({"error": "Could not read local LoRA metadata"}, status=500)

    @routes.get("/emotional-gallery/profiles")
    async def profiles(request):
        lora_name = request.query.get("lora_name", "")
        return web.json_response({"profiles": STORE.profiles(lora_name)})

    @routes.get("/emotional-gallery/profile/{profile_id}")
    async def profile(request):
        try:
            manifest = STORE.read(request.match_info["profile_id"])
            return web.json_response(profile_state(manifest))
        except ValueError as error:
            return web.json_response({"error": str(error)}, status=400)
        except FileNotFoundError as error:
            return web.json_response({"error": str(error)}, status=404)

    @routes.get("/emotional-gallery/image/{profile_id}/{emotion}")
    async def image(request):
        try:
            path = STORE.image_path(request.match_info["profile_id"], request.match_info["emotion"], request.query.get("thumbnail") == "1")
            return web.FileResponse(path, headers={"Cache-Control": "no-cache"})
        except ValueError as error:
            return web.json_response({"error": str(error)}, status=400)
        except FileNotFoundError as error:
            return web.json_response({"error": str(error)}, status=404)

    @routes.post("/emotional-gallery/archive/{profile_id}")
    async def archive(request):
        async with generate_lock:
            try:
                profile_id = request.match_info["profile_id"]
                if profile_state(STORE.read(profile_id))["active"]:
                    return web.json_response({"error": "Дождитесь завершения генерации набора. Ожидающие задачи можно остановить."}, status=409)
                return web.json_response(STORE.archive(profile_id))
            except ValueError as error:
                return web.json_response({"error": str(error)}, status=400)
            except FileNotFoundError as error:
                return web.json_response({"error": str(error)}, status=404)
            except OSError:
                LOGGER.exception("Emotional Gallery archive error")
                return web.json_response({"error": "Не удалось удалить набор"}, status=500)

    @routes.post("/emotional-gallery/restore/{token}")
    async def restore(request):
        async with generate_lock:
            try:
                return web.json_response({"profile": profile_state(STORE.restore(request.match_info["token"]))})
            except ValueError as error:
                return web.json_response({"error": str(error)}, status=400)
            except FileExistsError as error:
                return web.json_response({"error": str(error)}, status=409)
            except FileNotFoundError:
                return web.json_response({"error": "Удалённый набор не найден"}, status=404)
            except OSError:
                LOGGER.exception("Emotional Gallery restore error")
                return web.json_response({"error": "Не удалось восстановить набор"}, status=500)

    @routes.post("/emotional-gallery/generate")
    async def generate(request):
        async with generate_lock:
            try:
                data = await request.json()
                if not isinstance(data, dict):
                    raise ValueError("Ожидается объект настроек")
                client_id = data.get("client_id")
                if client_id is None:
                    client_id = str(uuid.uuid4())
                if not isinstance(client_id, str) or not client_id.strip() or len(client_id) > 200:
                    raise ValueError("Некорректный идентификатор окна ComfyUI")
                settings = normalize_settings(data.get("settings"), catalogs())
                if not isinstance(data.get("force", False), bool):
                    raise ValueError("force должен быть логическим значением")
                lora_path = folder_paths.get_full_path_or_raise("loras", settings["lora_name"])
                if settings.get("model_family") == "anima":
                    manifest = STORE.ensure_profile(settings,
                        folder_paths.get_full_path_or_raise("diffusion_models", settings["unet_name"]), lora_path,
                        clip_path=folder_paths.get_full_path_or_raise("text_encoders", settings["clip_name"]),
                        vae_path=folder_paths.get_full_path_or_raise("vae", settings["vae_name"]))
                else:
                    manifest = STORE.ensure_profile(settings, folder_paths.get_full_path_or_raise("checkpoints", settings["ckpt_name"]), lora_path)
                definitions = STORE.profile_emotions(manifest)
                current = profile_state(manifest)
                selected = data.get("emotions", [item["id"] for item in current["emotions"]])
                if not isinstance(selected, list) or not selected or any(not isinstance(item, str) or item not in definitions for item in selected):
                    raise ValueError("Выберите известные эмоции")
                selected = list(dict.fromkeys(selected))
                server = PromptServer.instance
                prepared = []
                for emotion in selected:
                    if current["states"][emotion]["status"] in ("pending", "running"):
                        continue
                    if not data.get("force", False) and emotion in current["images"]:
                        continue
                    prompt_id = str(uuid.uuid4())
                    prompt = build_prompt(settings, manifest["id"], emotion, definitions[emotion])
                    server.node_replace_manager.apply_replacements(prompt)
                    valid = await execution.validate_prompt(prompt_id, prompt, None)
                    if not valid[0]:
                        return web.json_response({"error": "Workflow генератора не прошёл проверку ComfyUI", "details": valid[1], "node_errors": valid[3]}, status=400)
                    prepared.append((emotion, prompt_id, prompt, valid[2]))
                # Validation yields to the worker; reread to preserve new images.
                with STORE.lock:
                    manifest = STORE.read(manifest["id"])
                    for emotion, prompt_id, _, _ in prepared:
                        manifest.setdefault("jobs", {})[emotion] = {"prompt_id": prompt_id}
                    STORE.write(manifest)
                for emotion, prompt_id, prompt, outputs in prepared:
                    extra = {"client_id": client_id, "create_time": int(time.time() * 1000), "eg_profile": manifest["id"], "eg_emotion": emotion}
                    server.prompt_queue.put((server.number, prompt_id, prompt, extra, outputs, {}))
                    server.number += 1
                return web.json_response({"profile": profile_state(STORE.read(manifest["id"])), "queued": len(prepared)})
            except (ValueError, TypeError) as error:
                return web.json_response({"error": str(error)}, status=400)
            except OSError as error:
                LOGGER.exception("Emotional Gallery cache or model file error")
                return web.json_response({"error": f"Не удалось прочитать модель или записать кеш: {error}"}, status=500)

    @routes.post("/emotional-gallery/cancel/{profile_id}")
    async def cancel(request):
        async with generate_lock:
            try:
                profile_id = request.match_info["profile_id"]
                STORE.read(profile_id)
                queue = PromptServer.instance.prompt_queue
                _, pending = queue.get_current_queue_volatile()
                removed = 0
                for item in pending:
                    if item[3].get("eg_profile") == profile_id:
                        removed += bool(queue.delete_queue_item(lambda candidate, prompt_id=item[1]: candidate[1] == prompt_id))
                return web.json_response({"removed": removed, "profile": profile_state(STORE.read(profile_id))})
            except ValueError as error:
                return web.json_response({"error": str(error)}, status=400)
            except FileNotFoundError as error:
                return web.json_response({"error": str(error)}, status=404)
