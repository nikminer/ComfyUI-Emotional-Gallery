import numpy as np
import torch
from PIL import Image

import folder_paths
from nodes import CheckpointLoaderSimple, CLIPLoader, LoraLoader, UNETLoader, VAELoader

from . import STORE
from .emotions import EMOTION_MAP, expression_prompt
from .gallery import model_identity


class EGCheckpointLoader(CheckpointLoaderSimple):
    CATEGORY = "Emotional Gallery/internal"
    DESCRIPTION = "Checkpoint loader for gallery recipes; reloads replaced model files."

    @classmethod
    def IS_CHANGED(cls, ckpt_name):
        return model_identity(folder_paths.get_full_path_or_raise("checkpoints", ckpt_name))


class EGDiffusionLoader(UNETLoader):
    CATEGORY = "Emotional Gallery/internal"

    @classmethod
    def IS_CHANGED(cls, unet_name, **kwargs):
        return model_identity(folder_paths.get_full_path_or_raise("diffusion_models", unet_name))


class EGTextEncoderLoader(CLIPLoader):
    CATEGORY = "Emotional Gallery/internal"

    @classmethod
    def IS_CHANGED(cls, clip_name, **kwargs):
        return model_identity(folder_paths.get_full_path_or_raise("text_encoders", clip_name))


class EGVAELoader(VAELoader):
    CATEGORY = "Emotional Gallery/internal"

    @classmethod
    def IS_CHANGED(cls, vae_name, **kwargs):
        return model_identity(folder_paths.get_full_path_or_raise("vae", vae_name))


class EGCharacterEmotion(LoraLoader):
    @classmethod
    def INPUT_TYPES(cls):
        inputs = LoraLoader.INPUT_TYPES()
        inputs["required"].update({
            "trigger_words": ("STRING", {"default": "", "multiline": True}),
            "base_prompt": ("STRING", {"default": "portrait, close-up face, looking at viewer, simple background", "multiline": True}),
            "emotion": ([*EMOTION_MAP, "custom"], {"default": "neutral"}),
        })
        inputs["optional"] = {"custom_expression": ("STRING", {"default": "", "multiline": True})}
        return inputs

    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    RETURN_NAMES = ("model", "clip", "positive_prompt")
    CATEGORY = "Emotional Gallery"
    FUNCTION = "apply_emotion"
    DESCRIPTION = "Load a character LoRA and choose an expression from the cached gallery. Connect positive_prompt to the positive text encoder."

    @classmethod
    def IS_CHANGED(cls, lora_name, **kwargs):
        return model_identity(folder_paths.get_full_path_or_raise("loras", lora_name))

    def apply_emotion(self, model, clip, lora_name, strength_model, strength_clip, trigger_words, base_prompt, emotion, custom_expression=""):
        definition = {"id": "custom", "prompt": custom_expression} if emotion == "custom" else None
        prompt = expression_prompt(base_prompt, trigger_words, emotion, definition)
        identity = model_identity(folder_paths.get_full_path_or_raise("loras", lora_name))
        if getattr(self, "lora_identity", None) != identity:
            self.loaded_lora = None
            self.lora_identity = identity
        model, clip = self.load_lora(model, clip, lora_name, strength_model, strength_clip)
        return model, clip, prompt


class EGCacheImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",), "profile_id": ("STRING",), "emotion": ("STRING", {"default": "neutral"})}}

    RETURN_TYPES = ()
    CATEGORY = "Emotional Gallery/internal"
    FUNCTION = "save"
    OUTPUT_NODE = True
    DESCRIPTION = "Internal output for the independent gallery generator."

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def save(self, images, profile_id, emotion):
        # Independent gallery recipes always generate exactly one sample.
        pixels = np.clip(255.0 * images[0].cpu().numpy(), 0, 255).astype(np.uint8)
        STORE.save(profile_id, emotion, Image.fromarray(pixels))
        return {"ui": {"eg_profile": [profile_id], "eg_emotion": [emotion]}}


class EGLoadCachedEmotion:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"profile_id": ("STRING", {"default": ""}), "emotion": ("STRING", {"default": "neutral"})}}

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "positive_prompt")
    CATEGORY = "Emotional Gallery"
    FUNCTION = "load"
    DESCRIPTION = "Load the actual cached preview for img2img, reference conditioning or image editing."

    @classmethod
    def IS_CHANGED(cls, profile_id, emotion):
        return str(STORE.image_path(profile_id, emotion))

    def load(self, profile_id, emotion):
        manifest = STORE.read(profile_id)
        with Image.open(STORE.image_path(profile_id, emotion)) as image:
            pixels = np.array(image.convert("RGB"), dtype=np.float32) / 255.0
        return torch.from_numpy(pixels)[None, ...], manifest["images"][emotion]["prompt"]
