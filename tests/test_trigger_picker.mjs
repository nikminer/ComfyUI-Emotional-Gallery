import assert from "node:assert/strict";
import { splitTriggerTags, toggleTriggerTags } from "../web/triggers.js";

assert.deepEqual(splitTriggerTags("makise kurisu, red hair, RED HAIR, (purple eyes, blue eyes:1.2)"), ["makise kurisu", "red hair", "(purple eyes, blue eyes:1.2)"]);
assert.equal(toggleTriggerTags("character, long hair, red hair", "long hair"), "character, red hair");
assert.equal(toggleTriggerTags("character", "character, long hair"), "character, long hair");
assert.equal(toggleTriggerTags("character, long hair, blush", "character, long hair"), "blush");
assert.equal(toggleTriggerTags("", "character, character"), "character");
assert.equal(toggleTriggerTags("(long hair:1.2), purple eyes", "purple eyes"), "(long hair:1.2)");
console.log("Trigger tag and group toggle checks passed.");
