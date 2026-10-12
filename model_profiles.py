"""Local text-to-image model profiles and their required files."""

MODEL_FIELDS = {
    "ckpt_name": {"catalog": "checkpoints", "label": "Checkpoint"},
    "unet_name": {"catalog": "diffusion_models", "label": "Diffusion model"},
    "clip_name": {"catalog": "text_encoders", "label": "Text encoder"},
    "clip_name2": {"catalog": "text_encoders", "label": "Text encoder 2"},
    "clip_name3": {"catalog": "text_encoders", "label": "Text encoder 3"},
    "vae_name": {"catalog": "vaes", "label": "VAE"},
}

CHECKPOINT_FIELDS = ["ckpt_name"]
SPLIT_FIELDS = ["unet_name", "clip_name", "vae_name"]
SDXL_DEFAULTS = {"width": 1024, "height": 1024, "steps": 28, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "strength_clip": 0.8}

MODEL_PROFILES = {
    "anima": {
        "label": "Anima", "source": "split", "model_fields": SPLIT_FIELDS, "encoder_type": "stable_diffusion",
        "defaults": {"width": 768, "height": 768, "steps": 30, "cfg": 4.0, "sampler_name": "euler_ancestral", "scheduler": "simple", "strength_clip": 0.0, "shift": 3.0},
        "labels": {"clip_name": "Text encoder (Qwen3 0.6B)", "vae_name": "VAE (Qwen Image)"},
        "patterns": {"unet_name": "anima", "clip_name": "qwen.*(?:0[._]?6b|06b)", "vae_name": "qwen.*vae"},
        "hint": "Choose Anima, a Qwen3 0.6B encoder, Qwen Image VAE, and an Anima character LoRA.",
    },
    "illustrious": {
        "label": "Illustrious / NoobAI", "source": "checkpoint", "model_fields": CHECKPOINT_FIELDS,
        "defaults": SDXL_DEFAULTS, "patterns": {"ckpt_name": "illustrious|noob|illust"},
        "hint": "Choose an Illustrious or compatible SDXL checkpoint and a matching character LoRA. Use the LoRA's trigger words.",
    },
    "pony": {
        "label": "Pony", "source": "checkpoint", "model_fields": CHECKPOINT_FIELDS,
        "defaults": {**SDXL_DEFAULTS, "cfg": 6.0}, "patterns": {"ckpt_name": "pony"},
        "hint": "Choose a Pony checkpoint and a Pony-compatible character LoRA. Add the quality tags recommended by the checkpoint to your base prompt.",
    },
    "sdxl": {
        "label": "SDXL", "source": "checkpoint", "model_fields": CHECKPOINT_FIELDS,
        "defaults": SDXL_DEFAULTS, "patterns": {"ckpt_name": "sdxl|xl"},
        "hint": "Choose an SDXL checkpoint with its text encoders and VAE included, and a matching SDXL character LoRA.",
    },
    "sd15": {
        "label": "SD 1.5", "source": "checkpoint", "model_fields": CHECKPOINT_FIELDS,
        "defaults": {"width": 512, "height": 512, "steps": 24, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "strength_clip": 0.8},
        "patterns": {"ckpt_name": "sd.?1[._]?5|v1[._-]?5"},
        "hint": "Choose an SD 1.5 checkpoint and an SD 1.5 character LoRA. 512 × 512 is the starting resolution.",
    },
    "flux": {
        "label": "Flux.1 Dev", "source": "split", "model_fields": ["unet_name", "clip_name", "clip_name2", "vae_name"], "encoder_type": "flux",
        "defaults": {"width": 1024, "height": 1024, "steps": 20, "cfg": 1.0, "guidance": 3.5, "sampler_name": "euler", "scheduler": "simple", "strength_clip": 0.0},
        "labels": {"clip_name": "Text encoder (CLIP-L)", "clip_name2": "Text encoder (T5-XXL)", "vae_name": "VAE (Flux.1 / ae)"},
        "patterns": {"unet_name": "flux[._-]?1(?!.*(?:kontext|fill|canny|depth)).*dev", "clip_name": "clip[._-]?l", "clip_name2": "t5.*xxl", "vae_name": "(?:^|[/\\\\])ae[.]|flux.*vae"},
        "hint": "Choose Flux.1 Dev, CLIP-L, T5-XXL, Flux.1 VAE, and a Flux.1 LoRA. Guidance is separate from CFG; CFG 1 disables negative-prompt guidance.",
    },
    "flux_schnell": {
        "label": "Flux.1 Schnell", "source": "split", "model_fields": ["unet_name", "clip_name", "clip_name2", "vae_name"], "encoder_type": "flux",
        "defaults": {"width": 1024, "height": 1024, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "strength_clip": 0.0},
        "labels": {"clip_name": "Text encoder (CLIP-L)", "clip_name2": "Text encoder (T5-XXL)", "vae_name": "VAE (Flux.1 / ae)"},
        "patterns": {"unet_name": "flux.*schnell", "clip_name": "clip[._-]?l", "clip_name2": "t5.*xxl", "vae_name": "(?:^|[/\\\\])ae[.]|flux.*vae"},
        "hint": "Choose Flux.1 Schnell, CLIP-L, T5-XXL, Flux.1 VAE, and a compatible LoRA. Start with 4 steps and CFG 1; there is no guidance embedding.",
    },
    "sd3": {
        "label": "SD3 / SD3.5", "source": "sd3_checkpoint", "model_fields": ["ckpt_name", "clip_name", "clip_name2", "clip_name3"],
        "defaults": {"width": 1024, "height": 1024, "steps": 28, "cfg": 4.5, "sampler_name": "euler", "scheduler": "sgm_uniform", "strength_clip": 0.0, "shift": 3.0},
        "labels": {"clip_name": "Text encoder (CLIP-L)", "clip_name2": "Text encoder (CLIP-G)", "clip_name3": "Text encoder (T5-XXL)"},
        "patterns": {"ckpt_name": "sd[._-]?3", "clip_name": "clip[._-]?l", "clip_name2": "clip[._-]?g", "clip_name3": "t5.*xxl"},
        "hint": "Choose an SD3 / SD3.5 checkpoint containing the VAE, separate CLIP-L, CLIP-G and T5-XXL encoders, and a matching LoRA.",
    },
    "qwen_image": {
        "label": "Qwen Image", "source": "split", "model_fields": SPLIT_FIELDS, "encoder_type": "qwen_image",
        "defaults": {"width": 1024, "height": 1024, "steps": 30, "cfg": 4.0, "sampler_name": "euler", "scheduler": "simple", "strength_clip": 0.0, "shift": 3.1},
        "labels": {"clip_name": "Text encoder (Qwen2.5-VL 7B)", "vae_name": "VAE (Qwen Image)"},
        "patterns": {"unet_name": "qwen(?!.*(?:edit|layered|2[._-]?1)).*image", "clip_name": "qwen.*2[._]?5.*vl.*7b", "vae_name": "qwen.*vae"},
        "hint": "Choose a Qwen Image text-to-image model, Qwen2.5-VL 7B encoder, Qwen Image VAE, and a Qwen Image LoRA. Edit models use a different workflow.",
    },
    "z_image": {
        "label": "Z-Image Base", "source": "split", "model_fields": SPLIT_FIELDS, "encoder_type": "lumina2",
        "defaults": {"width": 1024, "height": 1024, "steps": 25, "cfg": 4.0, "sampler_name": "res_multistep", "scheduler": "simple", "strength_clip": 0.0, "shift": 3.0},
        "labels": {"clip_name": "Text encoder (Qwen3 4B)", "vae_name": "VAE (Flux.1 / ae)"},
        "patterns": {"unet_name": "z[._-]?image(?!.*(?:turbo|omni|edit))", "clip_name": "qwen.*3.*4b", "vae_name": "(?:^|[/\\\\])ae[.]|flux.*vae"},
        "hint": "Choose Z-Image Base, Qwen3 4B, Flux.1 VAE, and a Z-Image LoRA. Base supports negative-prompt guidance.",
    },
    "z_image_turbo": {
        "label": "Z-Image Turbo", "source": "split", "model_fields": SPLIT_FIELDS, "encoder_type": "lumina2",
        "defaults": {"width": 1024, "height": 1024, "steps": 8, "cfg": 1.0, "sampler_name": "res_multistep", "scheduler": "simple", "strength_clip": 0.0, "shift": 3.0},
        "labels": {"clip_name": "Text encoder (Qwen3 4B)", "vae_name": "VAE (Flux.1 / ae)"},
        "patterns": {"unet_name": "z[._-]?image.*turbo", "clip_name": "qwen.*3.*4b", "vae_name": "(?:^|[/\\\\])ae[.]|flux.*vae"},
        "hint": "Choose Z-Image Turbo, Qwen3 4B, Flux.1 VAE, and a compatible LoRA. Start with 8 steps and CFG 1; negative-prompt guidance is disabled at CFG 1.",
    },
    "checkpoint": {
        "label": "SD 1.5 / SDXL (saved settings)", "source": "checkpoint", "model_fields": CHECKPOINT_FIELDS,
        "defaults": {}, "patterns": {}, "hint": "Choose an SD 1.5 or SDXL checkpoint and a matching character LoRA. This profile preserves earlier gallery settings.",
    },
}
