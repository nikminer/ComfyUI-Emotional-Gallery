import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../web/gallery.js", import.meta.url), "utf8")
    .replace(/^import .+;\r?$/gm, "")
    .split("\napp.registerExtension(")[0];

async function generate({ changed = false, saved = true, emotions, force = false, seed = "42" } = {}) {
    let body;
    const profile = { id: "saved-profile", settings: { model_family: "anima", seed, cfg: 4 } };
    const draft = { ...profile.settings, seed: changed ? "99" : seed };
    const Gallery = vm.runInNewContext(`${source}\nEmotionGallery;`, {
        app: { registerExtension() {} }, clearTimeout,
        api: { clientId: "gallery-window", async fetchApi(url, options) {
            assert.equal(url, "/emotional-gallery/generate");
            body = options.body;
            return { ok: true, async json() { return { profile, queued: 1 }; } };
        } },
        localStorage: { setItem() {} },
    });
    const gallery = Object.assign(Object.create(Gallery.prototype), {
        profile: saved ? profile : null, busy: false, loadVersion: 0,
        inputs: Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, { value: String(value) }])),
        getSettings: () => draft, render() {}, async loadProfiles() {}, info() {},
        error(error) { throw error; }, schedulePoll() {},
    });
    await gallery.generate(emotions, force);
    return { body, request: JSON.parse(body) };
}

const group = await generate({ changed: true, emotions: ["pout", "puffed_cheeks"] });
assert.equal(group.request.profile_id, "saved-profile");
assert.equal(group.request.settings.seed, 42);
assert.deepEqual(group.request.emotions, ["pout", "puffed_cheeks"]);
assert.equal(group.request.force, false);

assert.equal((await generate()).request.profile_id, "saved-profile");
assert.equal((await generate({ changed: true, force: true })).request.profile_id, "saved-profile");
const fresh = (await generate({ changed: true })).request;
assert.equal(fresh.profile_id, undefined);
assert.equal(fresh.settings.seed, 99);
assert.equal((await generate({ saved: false, emotions: ["pout"] })).request.profile_id, undefined);
assert.ok((await generate({ seed: "18446744073709551615" })).body.includes('"seed":18446744073709551615'));
console.log("Missing expressions target the saved set; changed recipes create a new set; 64-bit seeds preserved.");
