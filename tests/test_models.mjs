import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { initialModelFamily, modelDefaults, preferredModelFiles } from "../web/models.js";

const source = JSON.parse(execFileSync(process.env.GALLERY_TEST_PYTHON ?? "python", ["-B", "-c", "import json, model_profiles as m; print(json.dumps({'model_profiles': m.MODEL_PROFILES, 'model_fields': m.MODEL_FIELDS}))"], { cwd: fileURLToPath(new URL("..", import.meta.url)), encoding: "utf8" }));
const config = {
    ...source,
    defaults: { width: 768, height: 768, steps: 24, cfg: 6, strength_clip: 0.8, sampler_name: "euler", scheduler: "normal", shift: 3, guidance: 3.5 },
    samplers: ["euler", "euler_ancestral", "dpmpp_2m", "res_multistep"],
    schedulers: ["normal", "simple", "karras", "sgm_uniform"],
    checkpoints: ["waiIllustriousSDXL.safetensors", "pony.safetensors", "sd3.5_medium.safetensors"],
    diffusion_models: ["anima-base.safetensors", "flux2-dev.safetensors", "flux1-kontext-dev.safetensors", "flux1-dev.safetensors", "flux1-schnell.safetensors", "qwen_image_edit.safetensors", "qwen_image.safetensors", "z_image_turbo.safetensors", "z_image_bf16.safetensors"],
    text_encoders: ["qwen_3_06b.safetensors", "qwen_3_4b.safetensors", "qwen_2.5_vl_7b.safetensors", "clip_l.safetensors", "clip_g.safetensors", "t5xxl.safetensors"],
    vaes: ["qwen_image_vae.safetensors", "subfolder\\ae.safetensors"],
};
assert.equal(initialModelFamily(config), "anima");
assert.equal(initialModelFamily({ ...config, diffusion_models: [] }), "illustrious");
assert.equal(modelDefaults(config, "illustrious").width, 1024);
assert.equal(modelDefaults(config, "sd15").width, 512);
assert.equal(modelDefaults(config, "flux_schnell").steps, 4);
assert.equal(modelDefaults(config, "z_image_turbo").steps, 8);
assert.equal(preferredModelFiles(config, "flux").unet_name, "flux1-dev.safetensors");
assert.equal(preferredModelFiles(config, "flux").clip_name2, "t5xxl.safetensors");
assert.equal(preferredModelFiles(config, "flux").vae_name, "subfolder\\ae.safetensors");
assert.equal(preferredModelFiles(config, "qwen_image").unet_name, "qwen_image.safetensors");
assert.equal(preferredModelFiles(config, "z_image").unet_name, "z_image_bf16.safetensors");
assert.equal(preferredModelFiles(config, "sd3").clip_name3, "t5xxl.safetensors");
const animaOnly = { ...config, diffusion_models: ["anima-base.safetensors"], text_encoders: ["qwen_3_06b.safetensors"] };
assert.equal(preferredModelFiles(animaOnly, "flux").unet_name, "");
assert.equal(preferredModelFiles(animaOnly, "qwen_image").clip_name, "");
assert.equal(modelDefaults({ ...config, samplers: ["euler"], schedulers: ["normal"] }, "pony").sampler_name, "euler");
assert.equal(preferredModelFiles(config, "pony", { ckpt_name: "waiIllustriousSDXL.safetensors" }).ckpt_name, "waiIllustriousSDXL.safetensors");
for (const family of Object.keys(config.model_profiles)) {
    assert.deepEqual(Object.keys(preferredModelFiles(config, family)).sort(), [...config.model_profiles[family].model_fields].sort());
}
console.log("Model profiles, defaults, required files, and missing-model checks passed.");
