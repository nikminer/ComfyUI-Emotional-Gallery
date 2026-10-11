import folder_paths

from .gallery import GalleryStore

STORE = GalleryStore(folder_paths.get_user_directory() + "/emotional_gallery")

from .nodes import EGCacheImage, EGCharacterEmotion, EGCheckpointLoader, EGLoadCachedEmotion, EGDiffusionLoader, EGTextEncoderLoader, EGVAELoader
from .routes import register_routes

NODE_CLASS_MAPPINGS = {
    "EGCharacterEmotion": EGCharacterEmotion,
    "EGCacheImage": EGCacheImage,
    "EGLoadCachedEmotion": EGLoadCachedEmotion,
    "EGCheckpointLoader": EGCheckpointLoader,
    "EGDiffusionLoader": EGDiffusionLoader,
    "EGTextEncoderLoader": EGTextEncoderLoader,
    "EGVAELoader": EGVAELoader,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EGCharacterEmotion": "Character Emotion · ComfyUI Emotional Gallery",
    "EGCacheImage": "Cache Emotion · ComfyUI Emotional Gallery",
    "EGLoadCachedEmotion": "Load Cached Emotion · ComfyUI Emotional Gallery",
    "EGCheckpointLoader": "Checkpoint · ComfyUI Emotional Gallery",
}
WEB_DIRECTORY = "./web"
register_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
