import assert from "node:assert/strict";

// The interface must not read browser language or a previously stored selection.
Object.defineProperty(globalThis, "navigator", { configurable: true, get() { throw new Error("Language detection is forbidden"); } });
Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("Language preferences must not be read"); } });
const locale = await import("../web/locale.js");
assert.equal(locale.t("Выражения персонажа"), "Character expressions");
assert.equal(locale.t("◉ Эмоции"), "◉ Expressions");
assert.equal(locale.t("81 встроенных · своих: 2"), "81 built-in · 2 custom");
assert.equal(locale.t("Добавлено в очередь: 32. Результаты появятся автоматически."), "Queued: 32. Results will appear automatically.");
locale.registerLabels([{label: "Базовые эмоции", label_en: "Basic emotions"}, {label: "Ахегао (Ahegao)", label_en: "Ahegao"}]);
assert.equal(locale.t("Ахегао (Ahegao)"), "Ahegao");
assert.equal(locale.t("Догенерировать категорию: Базовые эмоции"), "Generate missing in category: Basic emotions");
assert.equal(locale.t("ahegao, cross-eyed, tongue out, blush"), "ahegao, cross-eyed, tongue out, blush");
assert.equal(locale.t("Мой персонаж.safetensors"), "Мой персонаж.safetensors");
assert.equal(locale.t(locale.t("Нет превью")), "No preview");
assert.equal(locale.setLanguage, undefined);
assert.equal(locale.language, undefined);
console.log("English interface checks passed; no language detection or language selector API.");
