# Changelog

## [1.0.0] - 2026-10-21

First stable release of ComfyUI Emotional Gallery: a local character-expression generator with a persistent image library.

### Features

- 131 built-in facial expressions: 99 SFW and 32 NSFW, plus custom expressions shared across character LoRAs.
- 50 additional everyday expressions, including eight pout and sulking variants, focused faces, fatigue, boredom, curiosity, and skepticism.
- Local generation profiles for Anima, Illustrious / NoobAI, Pony, SDXL, SD 1.5, Flux.1 Dev / Schnell, SD3 / SD3.5, Qwen Image, and Z-Image Base / Turbo.
- Full-image preview with Left / Right navigation, Escape to close, and expression-tag copying.
- Collapsible Character, Model files, Trigger words, Prompts, and Generation settings. Section states and sidebar visibility are remembered; Settings is positioned above the left sidebar.
- Searchable LoRA selection, trigger-word toggles from local metadata, and a draggable launcher.
- Persistent PNG images, WebP thumbnails, saved generation settings, and recoverable set deletion.
- English interface with English and Russian documentation. Implementation nodes remain hidden from the node library.
- GitHub Actions publishing to Comfy Registry for stable releases, with version validation, backend and frontend checks, and development-file exclusions.

### Fixes

- Generate missing continues the selected saved set using its stored settings and skips cached or queued expressions, even after model-file timestamps change.
- Changing generation settings switches the main action to Create gallery. Group and subcategory generation keep targeting the selected saved set.
- Existing cache identities, image files, custom-expression definitions, and legacy workflow identifiers are preserved.
- Gallery tasks use the requesting ComfyUI window's identifier for progress and completion events; cancelling pending gallery jobs preserves unrelated work.

### Install or update

Extract `comfyui-emotional-gallery-v1.0.0.zip` directly into `ComfyUI/custom_nodes/`. The archive contains the `comfyui_emotional_gallery` folder. For an existing installation, update that folder rather than installing a second copy. Git installations can use `git pull` instead.

Finish queued work, restart ComfyUI, and refresh the browser with Ctrl+F5. Saved images stay in `ComfyUI/user/emotional_gallery/` or the configured user directory. New previews can be added to an existing set with Generate missing.

### Compatibility

Python 3.10 or newer and ComfyUI with the native nodes required by the selected model profile. Matching model files and character LoRAs must already be installed. No model downloads, paid generation APIs, or additional runtime packages are included.

GGUF, Flux.2, reference-image and editing workflows, and video generation are outside this release. Expression quality depends on the selected model and LoRA.
