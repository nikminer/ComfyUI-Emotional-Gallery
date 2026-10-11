"""Disk cache and independent checkpoint / Anima generation recipes."""

import hashlib
import json
import math
import os
import re
import threading
import time
import uuid
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from .emotions import ACTIVE_EMOTION_MAP, CACHE_EMOTION_MAP, EMOTION_MAP, RETIRED_EMOTIONS, custom_definitions, expression_prompt, normalize_category, normalize_subcategory

DEFAULTS = {
    "model_family": "checkpoint", "unet_name": "", "clip_name": "", "vae_name": "", "shift": 3.0,
    "ckpt_name": "", "lora_name": "", "strength_model": 0.8, "strength_clip": 0.8,
    "trigger_words": "", "base_prompt": "portrait, close-up face, looking at viewer, simple background, detailed face",
    "negative_prompt": "low quality, blurry, deformed, bad anatomy, extra limbs, text, watermark",
    "width": 768, "height": 768, "steps": 24, "cfg": 6.0, "seed": 42,
    "sampler_name": "euler", "scheduler": "normal",
}
ANIMA_DEFAULTS = {"width": 768, "height": 768, "steps": 30, "cfg": 4.0,
                  "sampler_name": "euler_ancestral", "scheduler": "simple", "strength_clip": 0.0}
ANIMA_KEYS = ("unet_name", "clip_name", "vae_name", "shift")
PROFILE_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def model_identity(path):
    # A replacement at the same filename must invalidate its previews.
    resolved = Path(path).resolve()
    stat = resolved.stat()
    return {"path": str(resolved), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns}


def normalize_settings(values, catalogs):
    if not isinstance(values, dict):
        raise ValueError("Настройки должны быть объектом")
    settings = {key: values.get(key, default) for key, default in DEFAULTS.items()}
    if settings["model_family"] not in ("checkpoint", "anima"):
        raise ValueError("Выберите SD 1.5 / SDXL или Anima")
    model_options = (("unet_name", "diffusion_models"), ("clip_name", "text_encoders"), ("vae_name", "vaes")) if settings["model_family"] == "anima" else (("ckpt_name", "checkpoints"),)
    for key, catalog in (*model_options, ("lora_name", "loras"), ("sampler_name", "samplers"), ("scheduler", "schedulers")):
        if not isinstance(settings[key], str) or settings[key] not in catalogs[catalog]:
            raise ValueError(f"Выберите доступное значение: {key}")
    # Exclude hidden, unused model fields from the cache key.
    if settings["model_family"] == "checkpoint":
        for key in ("model_family", *ANIMA_KEYS):
            settings.pop(key)
    else:
        settings.pop("ckpt_name")
    for key in ("trigger_words", "base_prompt", "negative_prompt"):
        if not isinstance(settings[key], str) or len(settings[key]) > 20000:
            raise ValueError(f"Некорректный текст: {key}")
    limits = {"width": (64, 16384), "height": (64, 16384), "steps": (1, 10000), "seed": (0, 2**64 - 1)}
    for key, (minimum, maximum) in limits.items():
        value = settings[key]
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError(f"{key}: ожидается целое число от {minimum} до {maximum}")
    for key in ("width", "height"):
        multiple = 16 if settings.get("model_family") == "anima" else 8
        if settings[key] % multiple:
            raise ValueError(f"{key}: размер должен быть кратен {multiple}")
    float_limits = [("cfg", 0, 100), ("strength_model", -100, 100), ("strength_clip", -100, 100)]
    if settings.get("model_family") == "anima":
        float_limits.append(("shift", 0, 100))
    for key, minimum, maximum in float_limits:
        value = settings[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"Некорректное значение: {key}")
        settings[key] = float(value)
    return settings


def build_prompt(settings, profile_id, emotion, definition=None):
    """One batch of one image; ComfyUI owns sampling and model memory."""
    prompt = {
        "2": {"class_type": "EGCharacterEmotion", "inputs": {
            "model": ["1", 0], "clip": ["1", 1], "lora_name": settings["lora_name"],
            "strength_model": settings["strength_model"], "strength_clip": settings["strength_clip"],
            "trigger_words": settings["trigger_words"], "base_prompt": settings["base_prompt"], "emotion": emotion,
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 1], "text": ["2", 2]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 1], "text": settings["negative_prompt"]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": settings["width"], "height": settings["height"], "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": settings["seed"], "steps": settings["steps"], "cfg": settings["cfg"],
            "sampler_name": settings["sampler_name"], "scheduler": settings["scheduler"], "denoise": 1.0,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "EGCacheImage", "inputs": {"images": ["7", 0], "profile_id": profile_id, "emotion": emotion}},
    }
    if settings.get("model_family") == "anima":
        prompt["1"] = {"class_type": "EGDiffusionLoader", "inputs": {"unet_name": settings["unet_name"], "weight_dtype": "default"}}
        prompt["9"] = {"class_type": "EGTextEncoderLoader", "inputs": {"clip_name": settings["clip_name"], "type": "stable_diffusion"}}
        prompt["10"] = {"class_type": "EGVAELoader", "inputs": {"vae_name": settings["vae_name"]}}
        prompt["11"] = {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["2", 0], "shift": settings["shift"]}}
        prompt["2"]["inputs"]["clip"] = ["9", 0]
        prompt["5"]["class_type"] = "EmptySD3LatentImage"
        prompt["6"]["inputs"]["model"] = ["11", 0]
        prompt["7"]["inputs"]["vae"] = ["10", 0]
    else:
        prompt["1"] = {"class_type": "EGCheckpointLoader", "inputs": {"ckpt_name": settings["ckpt_name"]}}
    if emotion not in EMOTION_MAP:
        expression_prompt("", "", emotion, definition)
        prompt["2"]["inputs"]["emotion"] = "custom"
        prompt["2"]["inputs"]["custom_expression"] = definition["prompt"]
    return prompt


class GalleryStore:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.RLock()

    def emotions(self):
        with self.lock:
            path = self.root / "custom_emotions.json"
            custom = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            return {**ACTIVE_EMOTION_MAP, **custom_definitions(custom)}

    def add_emotion(self, label, prompt, category="sfw", subcategory=None):
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80:
            raise ValueError("Введите название эмоции (до 80 символов)")
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000:
            raise ValueError("Введите промпт выражения лица (до 4000 символов)")
        category = normalize_category(category)
        subcategory = normalize_subcategory(category, subcategory)
        with self.lock:
            definitions = self.emotions()
            if any(item["label"].casefold() == label.strip().casefold() for item in definitions.values()):
                raise ValueError("Эмоция с таким названием уже существует")
            emotion_id = "custom_" + uuid.uuid4().hex
            definition = {"id": emotion_id, "label": label.strip(), "prompt": prompt.strip(), "custom": True, "category": category, "subcategory": subcategory}
            custom = {key: item for key, item in definitions.items() if key not in EMOTION_MAP}
            custom[emotion_id] = definition
            self.root.mkdir(parents=True, exist_ok=True)
            temporary = self.root / f"custom-emotions-{uuid.uuid4().hex}.tmp"
            temporary.write_text(json.dumps(custom, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self.root / "custom_emotions.json")
            return definition

    def profile_emotions(self, manifest):
        # Saved definitions keep a cached image and its prompt in agreement.
        return {**EMOTION_MAP, **self.emotions(), **custom_definitions(manifest.get("emotions", {}))}

    def directory(self, profile_id):
        if not isinstance(profile_id, str) or not PROFILE_PATTERN.fullmatch(profile_id):
            raise ValueError("Некорректный ID галереи")
        path = (self.root / profile_id).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Недопустимый путь галереи")
        return path

    def read(self, profile_id):
        with self.lock:
            path = self.directory(profile_id) / "manifest.json"
            if not path.is_file():
                raise FileNotFoundError("Галерея ещё не создана")
            return json.loads(path.read_text(encoding="utf-8"))

    def trash_directory(self, token):
        if not isinstance(token, str) or not PROFILE_PATTERN.fullmatch(token):
            raise ValueError("Некорректный ID удалённого набора")
        path = (self.root / ".trash" / token).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Недопустимый путь удалённого набора")
        return path

    def archive(self, profile_id):
        with self.lock:
            self.read(profile_id)
            token = uuid.uuid4().hex
            destination = self.trash_directory(token)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(self.directory(profile_id), destination)
            return {"token": token, "profile_id": profile_id}

    def restore(self, token):
        with self.lock:
            source = self.trash_directory(token)
            manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
            destination = self.directory(manifest["id"])
            if destination.exists():
                raise FileExistsError("Набор с такими настройками уже существует. Восстановление его не перезапишет.")
            os.replace(source, destination)
            return manifest

    def write(self, manifest):
        directory = self.directory(manifest["id"])
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / f"manifest-{uuid.uuid4().hex}.tmp"
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, directory / "manifest.json")

    def ensure_profile(self, settings, checkpoint_path, lora_path, *, clip_path=None, vae_path=None):
        identity = {"version": 1, "settings": settings, "checkpoint": model_identity(checkpoint_path), "lora": model_identity(lora_path), "emotions": CACHE_EMOTION_MAP}
        if settings.get("model_family") == "anima":
            identity["version"] = 2
            identity["diffusion_model"] = identity.pop("checkpoint")
            identity["text_encoder"] = model_identity(clip_path)
            identity["vae"] = model_identity(vae_path)
        profile_id = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]
        with self.lock:
            if not (self.directory(profile_id) / "manifest.json").exists():
                self.write({"id": profile_id, "settings": settings, "identity": identity, "created_at": time.time(), "updated_at": time.time(), "images": {}})
            manifest = self.read(profile_id)
            custom = {key: item for key, item in self.emotions().items() if key not in EMOTION_MAP}
            if custom:
                snapshots = manifest.setdefault("emotions", {})
                missing = {key: item for key, item in custom.items() if key not in snapshots}
                if missing:
                    snapshots.update(missing)
                    self.write(manifest)
            return manifest

    def profiles(self, lora_name):
        with self.lock:
            manifests = []
            for path in self.root.glob("*/manifest.json"):
                try:
                    manifest = self.read(path.parent.name)
                except (ValueError, OSError):
                    continue
                if manifest["settings"]["lora_name"] == lora_name:
                    manifests.append(self.public(manifest))
            return sorted(manifests, key=lambda item: item["updated_at"], reverse=True)

    def image_path(self, profile_id, emotion, thumbnail=False):
        manifest = self.read(profile_id)
        if emotion not in self.profile_emotions(manifest):
            raise ValueError("Неизвестная эмоция")
        entry = manifest["images"].get(emotion)
        if not entry:
            raise FileNotFoundError("Эта эмоция ещё не сгенерирована")
        path = (self.directory(profile_id) / entry["thumbnail" if thumbnail else "filename"]).resolve()
        if not path.is_relative_to(self.directory(profile_id)) or not path.is_file():
            raise FileNotFoundError("Изображение отсутствует в кеше")
        return path

    def public(self, manifest):
        result = {key: manifest[key] for key in ("id", "settings", "created_at", "updated_at")}
        result["settings"] = {**manifest["settings"], "seed": str(manifest["settings"]["seed"])}
        result["emotions"] = [item for key, item in self.profile_emotions(manifest).items() if key not in RETIRED_EMOTIONS]
        result["images"] = {}
        for emotion, entry in manifest["images"].items():
            if emotion in RETIRED_EMOTIONS:
                continue
            try:
                self.image_path(manifest["id"], emotion)
                self.image_path(manifest["id"], emotion, True)
            except (ValueError, OSError):
                continue
            result["images"][emotion] = {"version": entry["version"], "prompt": entry["prompt"]}
        return result

    def save(self, profile_id, emotion, image):
        with self.lock:
            manifest = self.read(profile_id)
            definition = self.profile_emotions(manifest).get(emotion)
            if not definition:
                raise ValueError("Неизвестная эмоция")
            if emotion not in EMOTION_MAP:
                manifest.setdefault("emotions", {})[emotion] = definition
            directory = self.directory(profile_id)
            version = uuid.uuid4().hex
            filename = f"{emotion}-{version}.png"
            thumbnail = f"{emotion}-{version}.webp"
            settings = manifest["settings"]
            prompt = expression_prompt(settings["base_prompt"], settings["trigger_words"], emotion, definition)
            metadata = PngInfo()
            metadata.add_text("emotional_gallery", json.dumps({"settings": settings, "emotion": emotion, "emotion_definition": definition, "positive_prompt": prompt}, ensure_ascii=False))
            image.save(directory / filename, pnginfo=metadata)
            small = image.copy()
            small.thumbnail((320, 320), Image.Resampling.LANCZOS)
            small.save(directory / thumbnail, "WEBP", quality=85)
            previous = manifest["images"].get(emotion)
            manifest["images"][emotion] = {"filename": filename, "thumbnail": thumbnail, "version": version, "prompt": prompt}
            manifest["updated_at"] = time.time()
            self.write(manifest)
            if previous:
                for key in ("filename", "thumbnail"):
                    old = (directory / previous[key]).resolve()
                    if old.is_relative_to(directory) and old.is_file():
                        old.unlink()
            return manifest["images"][emotion]
