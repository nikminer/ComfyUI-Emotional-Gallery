export function modelDefaults(config, family) {
    const defaults = { ...config.defaults, ...config.model_profiles[family].defaults, model_family: family };
    for (const [field, catalog] of [["sampler_name", "samplers"], ["scheduler", "schedulers"]]) {
        if (!config[catalog].includes(defaults[field])) defaults[field] = config[catalog][0] ?? "";
    }
    return defaults;
}

export function preferredModelFiles(config, family, current = {}) {
    const profile = config.model_profiles[family];
    const selected = {};
    for (const name of profile.model_fields) {
        const files = config[config.model_fields[name].catalog];
        const pattern = profile.patterns[name] ? new RegExp(profile.patterns[name], "i") : null;
        selected[name] = files.includes(current[name]) ? current[name] : files.find(file => pattern?.test(file)) ?? (family === "checkpoint" ? files[0] : "") ?? "";
    }
    return selected;
}

export function initialModelFamily(config) {
    for (const family of ["anima", "illustrious", "pony", "sdxl", "sd15", "flux_schnell", "flux", "sd3", "qwen_image", "z_image_turbo", "z_image"]) {
        const profile = config.model_profiles[family];
        const field = profile.source === "split" ? "unet_name" : "ckpt_name";
        const pattern = new RegExp(profile.patterns[field], "i");
        if (config[config.model_fields[field].catalog].some(file => pattern.test(file))) return family;
    }
    return "checkpoint";
}
