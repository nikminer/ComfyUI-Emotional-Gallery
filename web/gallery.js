import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { mountLauncher } from "./launcher.js";
import { registerLabels, localize, t } from "./locale.js";
import { TriggerPicker } from "./triggers.js";
import { initialModelFamily, modelDefaults, preferredModelFiles } from "./models.js";
import { galleryNodeNames, hideGalleryNodeDefinitions, hideGalleryRegisteredNodes } from "./internal_nodes.js";

const ROOT = "/emotional-gallery";
const STORAGE_KEY = "emotional-gallery.settings.v2";
const GROUP_KEY = "emotional-gallery.group.v1";
const SUBGROUP_KEY = "emotional-gallery.subgroups.v1";
const DELETED_KEY = "emotional-gallery.deleted.v1";
let gallery;

async function request(path, body) {
    const response = await api.fetchApi(ROOT + path, body === undefined ? {} : {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) {
        const details = data.node_errors ? Object.values(data.node_errors).flatMap(node => node.errors ?? []).map(error => error.details).join("; ") : "";
        throw new Error([t(data.error || "Ошибка запроса"), details].filter(Boolean).join(": "));
    }
    return data;
}

function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function button(text, className, action) {
    const node = element("button", className, text);
    node.type = "button";
    node.addEventListener("click", action);
    return node;
}

function imageUrl(profile, emotion, thumbnail = false) {
    const path = `${ROOT}/image/${encodeURIComponent(profile.id)}/${encodeURIComponent(emotion)}?v=${profile.images[emotion]?.version ?? ""}${thumbnail ? "&thumbnail=1" : ""}`;
    return api.apiURL(path);
}

function emotionLabel(emotion) {
    return emotion.label_en || t(emotion.label);
}

class EmotionGallery {
    constructor(config) {
        this.config = config;
        registerLabels([...config.categories, ...config.emotions]);
        this.profile = null;
        this.selected = "neutral";
        this.inputs = {};
        this.cards = new Map();
        this.categories = new Map();
        this.groupScroll = new Map();
        this.subgroupState = {};
        try { const saved = JSON.parse(localStorage.getItem(SUBGROUP_KEY) || "{}"); if (saved && typeof saved === "object" && !Array.isArray(saved)) this.subgroupState = saved; } catch { /* Use initial groups. */ }
        this.selectedGroup = "sfw";
        this.deleted = null;
        try { const saved = localStorage.getItem(GROUP_KEY); if (["sfw", "nsfw"].includes(saved)) this.selectedGroup = saved; } catch { /* Use SFW. */ }
        this.selected = config.emotions.find(emotion => emotion.category === this.selectedGroup)?.id ?? "neutral";
        try { this.deleted = JSON.parse(localStorage.getItem(DELETED_KEY) || "null"); } catch { /* No deleted set. */ }
        this.busy = false;
        this.timer = null;
        this.loadVersion = 0;
        this.dialog = element("dialog", "eg-window");
        this.dialog.setAttribute("aria-label", "Галерея эмоций персонажа");
        const header = element("header", "eg-header");
        const heading = element("div");
        heading.append(element("div", "eg-eyebrow", "COMFYUI EMOTIONAL GALLERY"), element("h2", "", "Выражения персонажа"));
        this.counter = element("span", "eg-counter", `0 / ${config.emotions.length}`);
        header.append(heading, this.counter, button("×", "eg-close", () => this.dialog.close()));
        header.lastChild.setAttribute("aria-label", "Закрыть галерею");
        const body = element("div", "eg-body");
        const settings = element("aside", "eg-settings");
        settings.append(element("h3", "", "Персонаж и генерация"));
        this.field(settings, "Model profile", "model_family", "select", Object.entries(config.model_profiles).map(([value, profile]) => ({ value, label: profile.label })));
        this.inputs.model_family.addEventListener("change", () => {
            const family = this.inputs.model_family.value;
            const defaults = modelDefaults(this.config, family);
            for (const name of ["width", "height", "steps", "cfg", "sampler_name", "scheduler", "strength_clip", "shift", "guidance"]) this.inputs[name].value = defaults[name];
            for (const [name, value] of Object.entries(preferredModelFiles(this.config, family))) this.inputs[name].value = value;
            this.updateModelFields();
            this.render();
        });
        for (const [name, field] of Object.entries(config.model_fields)) this.field(settings, field.label, name, "select", config[field.catalog]);
        this.field(settings, "Shift", "shift", "number", null, { min: 0, max: 100, step: 0.1 });
        this.field(settings, "Guidance", "guidance", "number", null, { min: 0, max: 100, step: 0.1 });
        // Keep the native value store for settings and workflow integration.
        this.field(settings, "LoRA персонажа", "lora_name", "select", config.loras);
        this.inputs.lora_name.closest("label").hidden = true;
        this.loraPicker = element("div", "eg-field eg-lora-picker");
        this.loraPicker.append(element("span", "", "LoRA персонажа"));
        this.loraButton = button("Выберите LoRA…", "eg-lora-button", () => this.toggleLoraPicker());
        this.loraButton.setAttribute("aria-label", "Выбрать LoRA персонажа");
        this.loraButton.setAttribute("aria-haspopup", "listbox");
        this.loraButton.setAttribute("aria-expanded", "false");
        this.loraPanel = element("div", "eg-lora-panel");
        this.loraPanel.hidden = true;
        this.loraSearch = element("input");
        this.loraSearch.type = "search";
        this.loraSearch.placeholder = "Имя персонажа, Anima, папка…";
        this.loraSearch.setAttribute("aria-label", "Поиск LoRA");
        this.loraSearch.setAttribute("role", "combobox");
        this.loraSearch.setAttribute("aria-autocomplete", "list");
        this.loraSearch.setAttribute("aria-expanded", "false");
        this.loraSearch.setAttribute("aria-controls", "eg-lora-results");
        this.loraSearch.addEventListener("input", () => this.filterLoras());
        this.loraSearch.addEventListener("keydown", event => {
            if (event.key === "Escape") {
                event.preventDefault(); event.stopPropagation(); this.closeLoraPicker(true);
            } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                this.highlightLora(this.loraIndex + (event.key === "ArrowDown" ? 1 : -1));
            } else if (event.key === "Enter") {
                event.preventDefault();
                const name = this.loraMatches[this.loraIndex];
                if (name) this.chooseLora(name);
            }
        });
        this.loraResults = element("div", "eg-lora-results");
        this.loraResults.id = "eg-lora-results";
        this.loraResults.setAttribute("role", "listbox");
        this.loraResults.setAttribute("aria-label", "Найденные LoRA");
        this.loraResultCount = element("p", "eg-lora-result-count");
        this.loraResultCount.setAttribute("role", "status");
        this.loraPanel.append(this.loraSearch, this.loraResultCount, this.loraResults);
        this.loraPicker.append(this.loraButton, this.loraPanel);
        this.loraPicker.addEventListener("focusout", event => {
            if (!this.loraPicker.contains(event.relatedTarget)) this.closeLoraPicker();
        });
        this.loraButton.addEventListener("keydown", event => {
            if (event.key === "ArrowDown") { event.preventDefault(); this.toggleLoraPicker(true); }
        });
        settings.append(this.loraPicker);
        this.loraCount = element("p", "eg-hint");
        settings.append(this.loraCount, button("Обновить список моделей и LoRA", "eg-text-button", () => this.refreshCatalogs()));
        this.modelHint = element("p", "eg-hint eg-model-hint");
        settings.append(this.modelHint);
        const changeLora = () => {
            this.inputs.lora_name.title = this.inputs.lora_name.value;
            if (this.inputs.lora_name.value === this.loadedLora) return;
            this.loadedLora = this.inputs.lora_name.value;
            this.inputs.trigger_words.value = "";
            this.triggerPicker.load(this.loadedLora, true);
            this.profile = null;
            this.render();
            this.loadProfiles(true).catch(error => this.error(error));
        };
        this.inputs.lora_name.addEventListener("change", changeLora);
        this.field(settings, "Trigger words", "trigger_words", "textarea");
        this.triggerPicker = new TriggerPicker(this.inputs.trigger_words,
            name => request(`/triggers?lora_name=${encodeURIComponent(name)}`), () => this.renderNote());
        const strengths = element("div", "eg-pair");
        this.field(strengths, "Сила MODEL", "strength_model", "number", null, { min: -100, max: 100, step: 0.05 });
        this.field(strengths, "Сила CLIP", "strength_clip", "number", null, { min: -100, max: 100, step: 0.05 });
        settings.append(strengths);
        this.field(settings, "Базовый промпт", "base_prompt", "textarea");
        this.field(settings, "Негативный промпт", "negative_prompt", "textarea");
        const sizes = element("div", "eg-pair");
        this.field(sizes, "Ширина", "width", "number", null, { min: 64, max: 16384, step: 8 });
        this.field(sizes, "Высота", "height", "number", null, { min: 64, max: 16384, step: 8 });
        settings.append(sizes);
        const sampling = element("div", "eg-pair");
        this.field(sampling, "Шаги", "steps", "number", null, { min: 1, max: 10000, step: 1 });
        this.field(sampling, "CFG", "cfg", "number", null, { min: 0, max: 100, step: 0.5 });
        settings.append(sampling);
        this.field(settings, "Sampler", "sampler_name", "select", config.samplers);
        this.field(settings, "Scheduler", "scheduler", "select", config.schedulers);
        // Decimal seed text avoids silently rounding ComfyUI's 64-bit seeds.
        this.field(settings, "Seed (одинаковый для всех эмоций)", "seed", "text");
        this.inputs.seed.inputMode = "numeric";
        const content = element("section", "eg-content");
        const toolbar = element("div", "eg-toolbar");
        this.profiles = element("select", "eg-profiles");
        this.profiles.setAttribute("aria-label", "Сохранённые галереи этой LoRA");
        this.profiles.addEventListener("change", () => this.openProfile(this.profiles.value, true).catch(error => this.error(error)));
        this.generateButton = button("Создать галерею", "eg-primary", () => this.generate());
        this.deleteButton = button("Удалить набор", "eg-danger", () => this.deleteProfile());
        this.deleteButton.title = "Убрать выбранный набор из списка; его можно восстановить";
        toolbar.append(this.profiles, this.generateButton, this.deleteButton);
        this.note = element("p", "eg-note");
        const emotionToolbar = element("div", "eg-emotion-toolbar");
        this.emotionSummary = element("span");
        this.addEmotionButton = button("+ Своя эмоция", "eg-secondary", () => this.showEmotionEditor());
        emotionToolbar.append(this.emotionSummary, this.addEmotionButton);
        this.emotionEditor = element("form", "eg-emotion-editor");
        this.emotionEditor.hidden = true;
        this.emotionEditor.setAttribute("aria-label", "Добавить свою эмоцию");
        this.emotionEditor.append(element("strong", "", "Новая эмоция"));
        const labelField = element("label", "eg-field");
        labelField.append(element("span", "", "Название эмоции"));
        this.emotionLabel = element("input");
        this.emotionLabel.type = "text";
        this.emotionLabel.required = true;
        this.emotionLabel.maxLength = 80;
        this.emotionLabel.placeholder = "Например: Скепсис";
        labelField.append(this.emotionLabel);
        const promptField = element("label", "eg-field");
        promptField.append(element("span", "", "Промпт эмоции"));
        this.emotionPrompt = element("textarea");
        this.emotionPrompt.required = true;
        this.emotionPrompt.maxLength = 4000;
        this.emotionPrompt.placeholder = "skeptical expression, one eyebrow raised, pursed lips";
        promptField.append(this.emotionPrompt);
        const categoryField = element("label", "eg-field");
        categoryField.append(element("span", "", "Категория эмоции"));
        this.emotionCategory = element("select");
        this.emotionCategory.setAttribute("aria-label", "Категория эмоции");
        this.fillOptions(this.emotionCategory, config.categories.map(category => ({ value: category.id, label: category.label })));
        this.emotionCategory.value = "sfw";
        categoryField.append(this.emotionCategory);
        const subcategoryField = element("label", "eg-field");
        subcategoryField.append(element("span", "", "Expression subcategory"));
        this.emotionSubcategory = element("select");
        this.emotionSubcategory.setAttribute("aria-label", "Expression subcategory");
        subcategoryField.append(this.emotionSubcategory);
        this.emotionCategory.addEventListener("change", () => this.updateSubcategoryOptions());
        this.updateSubcategoryOptions();
        const editorActions = element("div", "eg-actions");
        this.saveEmotionButton = element("button", "eg-primary", "Добавить эмоцию");
        this.saveEmotionButton.type = "submit";
        editorActions.append(this.saveEmotionButton, button("Отмена", "eg-text-button", () => { this.hideEmotionEditor(); this.addEmotionButton.focus(); }));
        this.emotionError = element("p", "eg-editor-error");
        this.emotionError.setAttribute("role", "alert");
        this.emotionEditor.append(labelField, promptField, categoryField, subcategoryField, element("p", "eg-hint", "Опишите выражение лица, желательно на английском. Оно добавится к промпту персонажа и сохранится для всех LoRA."), editorActions, this.emotionError);
        this.emotionEditor.addEventListener("submit", event => { event.preventDefault(); this.saveEmotion(); });
        this.grid = element("div", "eg-grid");
        this.groupTabs = element("div", "eg-group-tabs");
        this.groupTabs.setAttribute("role", "tablist");
        this.groupTabs.setAttribute("aria-label", "Expression groups");
        this.groupControls = element("div", "eg-group-controls");
        this.groupControls.setAttribute("role", "toolbar");
        this.groupControls.setAttribute("aria-label", "Expression group controls");
        this.syncEmotions(config.emotions);
        const selected = element("div", "eg-selected");
        this.selectedPanel = selected;
        this.preview = element("img", "eg-preview");
        this.preview.alt = "Выбранное выражение лица";
        this.preview.hidden = true;
        const details = element("div", "eg-selected-details");
        this.selectionTitle = element("strong", "", "Нейтральное");
        this.promptText = element("p", "eg-expression");
        const actions = element("div", "eg-actions");
        this.copyButton = button("Копировать эмоцию", "eg-secondary", () => this.copy());
        actions.append(this.copyButton);
        details.append(this.selectionTitle, this.promptText, actions);
        selected.append(this.preview, details);
        this.message = element("div", "eg-message");
        this.message.setAttribute("role", "status");
        this.message.setAttribute("aria-live", "polite");
        this.cancelButton = button("Остановить оставшиеся", "eg-text-button", () => this.cancel());
        this.cancelButton.hidden = true;
        const footer = element("div", "eg-footer");
        this.restoreButton = button("Восстановить удалённый набор", "eg-text-button", () => this.restoreProfile());
        footer.append(this.message, this.cancelButton, this.restoreButton);
        content.append(toolbar, this.note, emotionToolbar, this.emotionEditor, this.groupTabs, this.groupControls, this.grid, selected, footer);
        body.append(settings, content);
        this.dialog.append(header, body);
        document.body.append(this.dialog);
        this.dialog.addEventListener("close", () => { this.closeLoraPicker(); clearTimeout(this.timer); this.timer = null; this.loadVersion++; });
        this.dialog.addEventListener("pointerdown", event => { if (!this.loraPicker.contains(event.target)) this.closeLoraPicker(); });
        this.dialog.addEventListener("click", event => { if (event.target === this.dialog) this.dialog.close(); });
        let restored = {};
        try { restored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); } catch { /* Ignore obsolete local settings. */ }
        const family = restored.model_family && config.model_profiles[restored.model_family] ? restored.model_family : Object.hasOwn(restored, "ckpt_name") ? "checkpoint" : initialModelFamily(config);
        this.setSettings({ ...modelDefaults(config, family), ...preferredModelFiles(config, family),
            lora_name: config.loras.find(name => family === "anima" ? /anima/i.test(name) : /illu/i.test(name)) || config.loras[0] || "", ...restored, model_family: family });
        this.repairSelections();
        this.render();
        this.triggerPicker.load(this.inputs.lora_name.value, !Object.hasOwn(restored, "trigger_words"));
    }

    field(parent, label, name, type, options, attributes = {}) {
        const wrapper = element(name === "trigger_words" ? "div" : "label", "eg-field");
        const caption = element(name === "trigger_words" ? "label" : "span", "", label);
        wrapper.append(caption);
        const input = element(type === "select" || type === "textarea" ? type : "input");
        input.name = name;
        input.setAttribute("aria-label", label);
        if (name === "trigger_words") {
            input.id = "eg-trigger-words";
            caption.htmlFor = input.id;
        }
        if (input.tagName === "INPUT") input.type = type;
        if (options) this.fillOptions(input, options);
        Object.assign(input, attributes);
        input.addEventListener("input", () => name === "model_family" || name === "lora_name" || Object.hasOwn(this.config.model_fields, name) ? this.render() : this.renderNote());
        wrapper.append(input);
        parent.append(wrapper);
        this.inputs[name] = input;
    }

    syncEmotions(emotions) {
        this.config.emotions = emotions;
        registerLabels(emotions);
        for (const category of this.config.categories) {
            if (this.categories.has(category.id)) continue;
            const section = element("div", "eg-category");
            section.id = `eg-group-${category.id}`;
            section.setAttribute("role", "tabpanel");
            section.setAttribute("aria-labelledby", `eg-tab-${category.id}`);
            const tab = button("", "eg-group-tab", () => this.setGroup(category.id));
            tab.id = `eg-tab-${category.id}`;
            tab.setAttribute("role", "tab");
            tab.setAttribute("aria-controls", section.id);
            tab.append(element("span", "", category.label));
            const count = element("span", "eg-category-count");
            tab.append(count);
            tab.addEventListener("keydown", event => {
                if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
                event.preventDefault();
                const id = event.key === "Home" ? "sfw" : event.key === "End" ? "nsfw" : category.id === "sfw" ? "nsfw" : "sfw";
                this.setGroup(id); this.categories.get(id).tab.focus();
            });
            const actions = element("div", "eg-category-actions");
            const folds = element("div", "eg-subcategory-folds");
            folds.append(button("Expand all", "eg-text-button", () => this.foldSubgroups(category.id, true)), button("Collapse all", "eg-text-button", () => this.foldSubgroups(category.id, false)));
            const generate = button("Generate missing in group", "eg-text-button", () => this.generate(this.config.emotions.filter(emotion => (emotion.category ?? "sfw") === category.id).map(emotion => emotion.id)));
            generate.setAttribute("aria-label", `Generate missing in group: ${category.label}`);
            actions.append(folds, generate);
            const subgroups = new Map();
            for (const [index, subgroup] of (category.subcategories ?? [{id: "custom", label: "Custom"}]).entries()) {
                const key = `${category.id}.${subgroup.id}`;
                const details = element("details", "eg-subcategory");
                details.open = typeof this.subgroupState[key] === "boolean" ? this.subgroupState[key] : index === 0;
                const summary = element("summary", "eg-subcategory-summary");
                summary.append(element("span", "", subgroup.label));
                const subcount = element("span", "eg-category-count");
                summary.append(subcount);
                const subactions = element("div", "eg-category-actions");
                const subgenerate = button("Generate missing", "eg-text-button", () => this.generate(this.subgroupEmotions(category.id, subgroup.id).map(emotion => emotion.id)));
                subgenerate.setAttribute("aria-label", `Generate missing: ${category.label} / ${subgroup.label}`);
                subactions.append(subgenerate);
                const cards = element("div", "eg-category-grid");
                details.append(summary, subactions, cards);
                details.addEventListener("toggle", () => {
                    this.subgroupState[key] = details.open;
                    try { localStorage.setItem(SUBGROUP_KEY, JSON.stringify(this.subgroupState)); } catch { /* Folds remain usable. */ }
                });
                subgroups.set(subgroup.id, { details, cards, count: subcount, generate: subgenerate });
                section.append(details);
            }
            this.categories.set(category.id, { section, subgroups, count, generate, tab, actions });
            this.groupTabs.append(tab);
            this.groupControls.append(actions);
            this.grid.append(section);
        }
        const ids = new Set(emotions.map(emotion => emotion.id));
        for (const [id, item] of this.cards) {
            if (!ids.has(id)) { item.card.remove(); this.cards.delete(id); }
        }
        for (const emotion of emotions) {
            const category = this.categories.get(emotion.category ?? "sfw");
            const subgroup = category.subgroups.get(emotion.subcategory ?? "custom") ?? category.subgroups.get("custom");
            const caption = emotionLabel(emotion);
            if (this.cards.has(emotion.id)) {
                const card = this.cards.get(emotion.id).card;
                card.setAttribute("aria-label", caption);
                card.querySelector(".eg-label").textContent = caption;
                if (card.parentNode !== subgroup.cards) subgroup.cards.append(card);
                continue;
            }
            const card = button("", "eg-card", () => this.select(emotion.id));
            card.setAttribute("aria-label", caption);
            card.classList.toggle("eg-card-custom", !!emotion.custom);
            const media = element("div", "eg-media");
            const placeholder = element("span", "eg-placeholder", "◌");
            media.append(placeholder);
            const label = element("span", "eg-label", caption);
            const status = element("span", "eg-card-status", "Нет превью");
            card.append(media, label, status);
            this.cards.set(emotion.id, { card, media, placeholder, status, version: null, image: null });
            subgroup.cards.append(card);
        }
        for (const [categoryId, category] of this.categories) {
            for (const [subgroupId, subgroup] of category.subgroups) subgroup.details.hidden = !this.subgroupEmotions(categoryId, subgroupId).length;
        }
        this.setGroup(this.selectedGroup, false);
        const customCount = emotions.filter(emotion => emotion.custom).length;
        this.emotionSummary.textContent = `${emotions.length - customCount} встроенных · своих: ${customCount}`;
        localize(this.dialog);
    }

    showEmotionEditor() {
        this.emotionEditor.hidden = false;
        this.grid.hidden = true;
        this.groupTabs.hidden = true;
        this.groupControls.hidden = true;
        this.selectedPanel.hidden = true;
        this.emotionError.textContent = "";
        this.emotionLabel.focus();
    }

    updateSubcategoryOptions() {
        const category = this.config.categories.find(item => item.id === this.emotionCategory.value);
        this.fillOptions(this.emotionSubcategory, (category?.subcategories ?? [{id: "custom", label: "Custom"}]).map(item => ({value: item.id, label: item.label})));
        this.emotionSubcategory.value = "custom";
    }

    subgroupEmotions(category, subgroup) {
        return this.config.emotions.filter(emotion => (emotion.category ?? "sfw") === category && (emotion.subcategory ?? "custom") === subgroup);
    }

    foldSubgroups(category, open) {
        for (const subgroup of this.categories.get(category)?.subgroups.values() ?? []) if (!subgroup.details.hidden) subgroup.details.open = open;
        this.grid.scrollTop = 0;
        this.groupScroll.set(category, 0);
    }

    revealExpression(emotionId) {
        const emotion = this.config.emotions.find(item => item.id === emotionId);
        if (!emotion) return;
        this.setGroup(emotion.category ?? "sfw", false);
        const subgroups = this.categories.get(emotion.category ?? "sfw")?.subgroups;
        const subgroup = subgroups?.get(emotion.subcategory ?? "custom") ?? subgroups?.get("custom");
        if (subgroup) subgroup.details.open = true;
    }

    hideEmotionEditor() {
        this.emotionEditor.hidden = true;
        this.grid.hidden = false;
        this.groupTabs.hidden = false;
        this.groupControls.hidden = false;
        this.selectedPanel.hidden = false;
    }

    async saveEmotion() {
        if (this.saveEmotionButton.disabled) return;
        this.saveEmotionButton.disabled = true;
        clearTimeout(this.timer);
        this.loadVersion++;
        this.emotionError.textContent = "";
        try {
            const data = await request("/emotions", { label: this.emotionLabel.value.trim(), prompt: this.emotionPrompt.value.trim(), category: this.emotionCategory.value, subcategory: this.emotionSubcategory.value });
            const definitions = new Map(data.emotions.map(emotion => [emotion.id, emotion]));
            for (const emotion of this.profile?.emotions ?? []) definitions.set(emotion.id, emotion);
            this.syncEmotions(Array.from(definitions.values()));
            this.selected = data.emotion.id;
            this.emotionEditor.reset();
            this.emotionCategory.value = "sfw";
            this.updateSubcategoryOptions();
            this.hideEmotionEditor();
            this.setGroup(data.emotion.category ?? "sfw");
            this.revealExpression(this.selected);
            this.render();
            this.cards.get(this.selected).card.scrollIntoView({ block: "nearest" });
            this.info("Custom expression saved. Generate missing previews in its subcategory or the full set.");
        } catch (error) { this.emotionError.textContent = error.message; }
        finally { this.saveEmotionButton.disabled = false; this.schedulePoll(); localize(this.dialog); }
    }

    setSettings(settings) {
        if (!(settings.lora_name ?? "").toLocaleLowerCase().includes(this.loraSearch.value.trim().toLocaleLowerCase())) this.loraSearch.value = "";
        this.fillOptions(this.inputs.lora_name, this.config.loras);
        const defaults = modelDefaults(this.config, settings.model_family ?? "checkpoint");
        for (const [name, input] of Object.entries(this.inputs)) input.value = settings[name] ?? defaults[name];
        this.inputs.model_family.value = settings.model_family ?? "checkpoint";
        this.updateModelFields();
        this.filterLoras();
        if (this.triggerPicker.lora && this.triggerPicker.lora !== this.inputs.lora_name.value) this.triggerPicker.load(this.inputs.lora_name.value, false);
        else this.triggerPicker.sync();
    }

    setGroup(id, persist = true) {
        if (!this.categories.has(id)) return;
        const changed = this.selectedGroup !== id;
        if (changed) this.groupScroll.set(this.selectedGroup, this.grid.scrollTop);
        this.selectedGroup = id;
        for (const [key, category] of this.categories) {
            category.section.hidden = key !== id;
            category.actions.hidden = key !== id;
            category.tab.setAttribute("aria-selected", String(key === id));
            category.tab.tabIndex = key === id ? 0 : -1;
        }
        if (changed) this.grid.scrollTop = this.groupScroll.get(id) ?? 0;
        if (persist) {
            const selected = this.config.emotions.find(emotion => emotion.id === this.selected);
            if (selected?.category !== id) this.selected = this.config.emotions.find(emotion => emotion.category === id)?.id ?? this.selected;
            if (this.selectionTitle) this.render();
            localize(this.dialog);
            try { localStorage.setItem(GROUP_KEY, id); } catch { /* Group selection remains usable. */ }
        }
    }

    fillOptions(input, options) {
        const selected = input.value;
        input.replaceChildren();
        if (Object.hasOwn(this.config.model_fields, input.name)) {
            const empty = element("option", "", "Choose a model file…");
            empty.value = "";
            input.append(empty);
        }
        for (const item of options) {
            const value = typeof item === "string" ? item : item.value;
            const option = element("option", "", typeof item === "string" ? value.split(/[\\/]/).pop() : item.label);
            option.value = value;
            option.title = value;
            input.append(option);
        }
        if (Array.from(input.options).some(option => option.value === selected)) input.value = selected;
    }

    filterLoras() {
        const terms = this.loraSearch.value.toLocaleLowerCase().split(/[\s\\/_-]+/).filter(Boolean);
        const selected = this.inputs.lora_name.value;
        this.loraMatches = this.config.loras.filter(name => {
            const text = name.toLocaleLowerCase().replace(/[\\/_-]+/g, " ");
            return terms.every(term => text.includes(term));
        });
        this.loraButton.textContent = selected ? selected.split(/[\\/]/).pop() : "Выберите LoRA…";
        this.loraButton.title = selected;
        this.loraCount.textContent = `В библиотеке: ${this.config.loras.length} LoRA · нажмите для поиска`;
        this.loraResultCount.textContent = this.loraMatches.length ? `Найдено: ${this.loraMatches.length} / ${this.config.loras.length}` : "Ничего не найдено. Измените запрос.";
        this.loraResults.replaceChildren();
        this.loraMatches.forEach((name, index) => {
            const parts = name.split(/[\\/]/);
            const option = button("", "eg-lora-option", () => this.chooseLora(name));
            option.id = `eg-lora-option-${index}`;
            option.setAttribute("role", "option");
            option.setAttribute("aria-selected", String(name === selected));
            option.tabIndex = -1;
            option.title = name;
            option.append(element("span", "eg-lora-name", parts.pop()), element("span", "eg-lora-path", parts.join(" / ")));
            this.loraResults.append(option);
        });
        const index = terms.length ? 0 : this.loraMatches.indexOf(selected);
        this.highlightLora(Math.max(0, index));
        localize(this.dialog);
    }

    highlightLora(index) {
        this.loraIndex = Math.max(0, Math.min(index, this.loraMatches.length - 1));
        for (const [position, option] of Array.from(this.loraResults.children).entries()) option.classList.toggle("eg-lora-highlight", position === this.loraIndex);
        const active = this.loraResults.children[this.loraIndex];
        if (active) {
            this.loraSearch.setAttribute("aria-activedescendant", active.id);
            if (!this.loraPanel.hidden) active.scrollIntoView({ block: "nearest" });
        } else this.loraSearch.removeAttribute("aria-activedescendant");
    }

    toggleLoraPicker(open = this.loraPanel.hidden) {
        if (!open) { this.closeLoraPicker(true); return; }
        this.loraSearch.value = "";
        this.loraPanel.hidden = false;
        this.loraButton.setAttribute("aria-expanded", "true");
        this.loraSearch.setAttribute("aria-expanded", "true");
        this.filterLoras();
        this.loraSearch.focus();
    }

    closeLoraPicker(focus = false) {
        this.loraPanel.hidden = true;
        this.loraButton.setAttribute("aria-expanded", "false");
        this.loraSearch.setAttribute("aria-expanded", "false");
        if (focus) this.loraButton.focus();
    }

    chooseLora(name) {
        this.inputs.lora_name.value = name;
        this.filterLoras();
        this.closeLoraPicker(true);
        this.inputs.lora_name.dispatchEvent(new Event("change", { bubbles: true }));
    }

    repairSelections() {
        const current = Object.fromEntries(Object.keys(this.config.model_fields).map(name => [name, this.inputs[name].value]));
        for (const [name, value] of Object.entries(preferredModelFiles(this.config, this.inputs.model_family.value, current))) this.inputs[name].value = value;
        if (!this.config.loras.includes(this.inputs.lora_name.value)) this.inputs.lora_name.value = this.config.loras[0] || "";
        this.filterLoras();
    }

    updateModelFields() {
        const profile = this.config.model_profiles[this.inputs.model_family.value];
        for (const [name, field] of Object.entries(this.config.model_fields)) {
            const wrapper = this.inputs[name].closest("label");
            wrapper.hidden = !profile.model_fields.includes(name);
            const label = profile.labels?.[name] ?? field.label;
            wrapper.querySelector("span").textContent = label;
            this.inputs[name].setAttribute("aria-label", label);
        }
        for (const name of ["shift", "guidance"]) this.inputs[name].closest("label").hidden = !Object.hasOwn(profile.defaults, name);
        for (const name of ["width", "height"]) this.inputs[name].step = profile.source === "checkpoint" ? 8 : 16;
        this.modelHint.textContent = profile.hint;
    }

    async refreshCatalogs() {
        try {
            const settings = this.getSettings();
            this.config = await request("/config");
            registerLabels([...this.config.categories, ...this.config.emotions]);
            this.syncEmotions(this.config.emotions);
            for (const [name, field] of Object.entries(this.config.model_fields)) this.fillOptions(this.inputs[name], this.config[field.catalog]);
            for (const [name, catalog] of Object.entries({ lora_name: "loras", sampler_name: "samplers", scheduler: "schedulers" })) this.fillOptions(this.inputs[name], this.config[catalog]);
            this.setSettings(settings);
            this.repairSelections();
            this.render();
            this.info(`Список обновлён: ${this.config.diffusion_models.length} diffusion models, ${this.config.checkpoints.length} checkpoints, ${this.config.loras.length} LoRA.`);
        } catch (error) { this.error(error); }
    }

    getSettings() {
        const settings = {};
        const profile = this.config.model_profiles[this.inputs.model_family.value];
        for (const [name, input] of Object.entries(this.inputs)) {
            if (Object.hasOwn(this.config.model_fields, name) && !profile.model_fields.includes(name)) continue;
            if (["shift", "guidance"].includes(name) && !Object.hasOwn(profile.defaults, name)) continue;
            if (input.type === "number" && !input.checkValidity()) throw new Error(`Проверьте поле ${name}`);
            settings[name] = input.type === "number" ? Number(input.value) : input.value;
        }
        if (!/^\d+$/.test(settings.seed)) throw new Error("Seed должен быть целым неотрицательным числом");
        const seed = BigInt(settings.seed);
        // JSON numbers are parsed exactly by Python; use a decimal literal in generate().
        if (seed > 18446744073709551615n) throw new Error("Seed превышает 64-битный диапазон");
        return settings;
    }

    async open() {
        if (!this.dialog.open) this.dialog.showModal();
        await this.loadProfiles(true);
    }

    async loadProfiles(restore = false, preferredId = null) {
        const version = ++this.loadVersion;
        clearTimeout(this.timer);
        const loraName = this.inputs.lora_name.value;
        this.loadedLora = loraName;
        const result = await request(`/profiles?lora_name=${encodeURIComponent(loraName)}`);
        if (version !== this.loadVersion || !this.dialog.open) return;
        this.profiles.replaceChildren();
        for (const profile of result.profiles) {
            const date = new Date(profile.created_at * 1000).toLocaleDateString("en-US");
            const option = element("option", "", `${Object.keys(profile.images).length}/${profile.emotions.length} · seed ${profile.settings.seed} · ${date}`);
            option.value = profile.id;
            this.profiles.append(option);
        }
        if (!result.profiles.length) {
            const option = element("option", "", "Пока нет сохранённых галерей"); option.value = ""; this.profiles.append(option);
            this.profile = null;
            this.render();
            return;
        }
        const selected = result.profiles.find(profile => profile.id === preferredId) || result.profiles[0];
        this.profiles.value = selected.id;
        await this.openProfile(selected.id, restore);
    }

    async openProfile(profileId, restore = false) {
        if (!profileId) return;
        const version = ++this.loadVersion;
        clearTimeout(this.timer);
        const profile = await request(`/profile/${encodeURIComponent(profileId)}`);
        if (version !== this.loadVersion || !this.dialog.open) return;
        this.profile = profile;
        this.syncEmotions(profile.emotions);
        if (restore) this.setSettings(profile.settings);
        this.render();
        this.schedulePoll();
    }

    schedulePoll() {
        clearTimeout(this.timer);
        if (!this.dialog.open || !this.profile) return;
        // Also catches jobs started in another browser or after this window closed.
        this.timer = setTimeout(() => this.openProfile(this.profile.id).catch(error => { this.error(error); this.schedulePoll(); }), this.profile.active ? 1200 : 5000);
    }

    renderNote() {
        this.note.hidden = !this.profile;
        if (!this.profile) {
            this.note.textContent = `В наборе ${this.config.emotions.length} выражений. Готовые карточки сохраняются на диске.`;
            localize(this.dialog);
            return;
        }
        const settings = this.profile.settings;
        const family = settings.model_family ?? "checkpoint";
        const changed = this.inputs.model_family.value !== family || Object.entries(settings).some(([key, value]) => this.inputs[key] && String(value) !== this.inputs[key].value);
        const model = (settings.unet_name ?? settings.ckpt_name).split(/[\\/]/).pop();
        this.note.textContent = changed ? "Настройки изменены. Кнопка генерации создаст соответствующий набор; ниже показан сохранённый кеш." : `${model} · ${settings.width} × ${settings.height} · seed ${settings.seed}`;
        localize(this.dialog);
    }

    render() {
        const profile = this.profile;
        this.counter.textContent = `${Object.keys(profile?.images ?? {}).length} / ${this.config.emotions.length}`;
        if (profile && this.profiles.value === profile.id) {
            this.profiles.selectedOptions[0].textContent = `${Object.keys(profile.images).length}/${this.config.emotions.length} · seed ${profile.settings.seed} · ${new Date(profile.created_at * 1000).toLocaleDateString("en-US")}`;
        }
        const required = [...this.config.model_profiles[this.inputs.model_family.value].model_fields, "lora_name"];
        const missingModels = required.some(name => !this.inputs[name].value);
        this.generateButton.disabled = this.busy || missingModels;
        this.deleteButton.disabled = this.busy || !profile || !!profile.active;
        this.restoreButton.hidden = !this.deleted;
        this.restoreButton.disabled = this.busy;
        this.generateButton.textContent = this.busy ? "Подготовка…" : profile ? "Догенерировать набор" : "Создать галерею";
        this.cancelButton.hidden = !profile?.active;
        const labels = { missing: "Нет превью", ready: "В кеше", running: "Генерация…", pending: "В очереди", error: "Ошибка · повторить" };
        for (const emotion of this.config.emotions) {
            const item = this.cards.get(emotion.id);
            const entry = profile?.images[emotion.id];
            const state = profile?.states[emotion.id] ?? { status: entry ? "ready" : "missing" };
            item.card.classList.toggle("eg-active", emotion.id === this.selected);
            item.card.classList.toggle("eg-generating", state.status === "running");
            item.card.setAttribute("aria-pressed", String(emotion.id === this.selected));
            item.card.title = state.message || emotion.prompt;
            item.status.textContent = labels[state.status];
            item.status.dataset.status = state.status;
            const version = entry ? `${profile.id}-${entry.version}` : null;
            if (item.version !== version) {
                item.version = version;
                item.media.replaceChildren();
                if (entry) {
                    item.image = element("img");
                    item.image.src = imageUrl(profile, emotion.id, true);
                    item.image.alt = emotionLabel(emotion);
                    item.image.loading = "lazy";
                    item.media.append(item.image);
                } else {
                    item.image = null;
                    item.media.append(item.placeholder);
                }
            }
        }
        for (const [id, category] of this.categories) {
            const expressions = this.config.emotions.filter(emotion => (emotion.category ?? "sfw") === id);
            const ready = expressions.filter(emotion => profile?.images[emotion.id]).length;
            category.count.textContent = `${ready} / ${expressions.length}`;
            category.generate.disabled = this.busy || missingModels;
            for (const [subgroupId, subgroup] of category.subgroups) {
                const members = this.subgroupEmotions(id, subgroupId);
                subgroup.count.textContent = `${members.filter(emotion => profile?.images[emotion.id]).length} / ${members.length}`;
                subgroup.generate.disabled = this.busy || missingModels;
            }
        }
        this.renderNote();
        this.renderSelection();
        if (missingModels) this.error(new Error("Выберите модель и LoRA. Для Anima также нужны text encoder и VAE; список можно обновить."));
        else if (profile?.active && !this.busy) this.info(`В очереди / генерации: ${profile.active}. Можно закрыть окно — работа продолжится.`);
        else if (profile && !this.busy) {
            const failures = Object.values(profile.states).filter(state => state.status === "error");
            if (failures.length) this.error(new Error(`${failures.length} эмоций с ошибкой. ${failures[0].message}`));
            else this.info("Cache saved. Select an expression and copy its tags.");
        }
        else if (!this.busy) this.info("Выберите LoRA, укажите trigger words и создайте галерею.");
        localize(this.dialog);
    }

    renderSelection() {
        const emotion = this.config.emotions.find(item => item.id === this.selected) ?? this.config.emotions[0];
        this.selected = emotion.id;
        this.selectionTitle.textContent = emotionLabel(emotion);
        this.promptText.textContent = emotion.prompt;
        this.preview.hidden = !this.profile?.images[emotion.id];
        if (!this.preview.hidden) {
            const url = imageUrl(this.profile, emotion.id, true);
            if (this.preview.getAttribute("src") !== url) this.preview.src = url;
        } else this.preview.removeAttribute("src");
    }

    select(emotion) { this.selected = emotion; this.render(); }
    info(text) { this.message.textContent = text; this.message.classList.remove("eg-error"); localize(this.dialog); }
    error(error) { this.message.textContent = error.message; this.message.classList.add("eg-error"); localize(this.dialog); }

    async generate(emotions = undefined, force = false) {
        if (this.busy) return;
        this.busy = true;
        clearTimeout(this.timer);
        this.loadVersion++;
        let failure;
        this.render();
        try {
            const settings = force && this.profile ? { ...this.profile.settings, seed: String(this.profile.settings.seed) } : this.getSettings();
            const seed = settings.seed;
            const body = JSON.stringify({ client_id: api.clientId, settings: { ...settings, seed: "__EG_SEED__" }, emotions, force }).replace('"__EG_SEED__"', seed);
            const response = await api.fetchApi(`${ROOT}/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body });
            const data = await response.json();
            if (!response.ok) {
                const details = Object.values(data.node_errors ?? {}).flatMap(node => node.errors ?? []).map(error => error.details).join("; ");
                throw new Error([t(data.error || "Ошибка генерации"), details].filter(Boolean).join(": "));
            }
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
            this.profile = data.profile;
            // Do not discard changed form settings when regenerating a cached tile.
            await this.loadProfiles(false, data.profile.id);
            this.info(data.queued ? `Добавлено в очередь: ${data.queued}. Результаты появятся автоматически.` : "Все выбранные эмоции уже готовы или находятся в очереди.");
        } catch (error) { failure = error; }
        finally {
            this.busy = false;
            this.render();
            if (failure) this.error(failure);
            this.schedulePoll();
        }
    }

    async cancel() {
        if (!this.profile) return;
        try {
            const data = await request(`/cancel/${this.profile.id}`, {});
            this.profile = data.profile;
            this.render();
            this.info(`Убрано из очереди: ${data.removed}. Текущая генерация завершится.`);
        } catch (error) { this.error(error); }
    }

    async deleteProfile() {
        if (this.busy || !this.profile || this.profile.active) return;
        this.busy = true;
        clearTimeout(this.timer);
        this.loadVersion++;
        this.render();
        let failure;
        try {
            this.deleted = await request(`/archive/${this.profile.id}`, {});
            localStorage.setItem(DELETED_KEY, JSON.stringify(this.deleted));
            this.profile = null;
            await this.loadProfiles(true);
        } catch (error) { failure = error; }
        finally {
            this.busy = false;
            this.render();
            if (failure) this.error(failure);
            else this.info("Набор удалён из списка. Его можно восстановить кнопкой внизу.");
            this.schedulePoll();
        }
    }

    async restoreProfile() {
        if (this.busy || !this.deleted) return;
        this.busy = true;
        clearTimeout(this.timer);
        this.loadVersion++;
        this.render();
        let failure;
        try {
            const data = await request(`/restore/${this.deleted.token}`, {});
            this.setSettings(data.profile.settings);
            this.profile = data.profile;
            this.deleted = null;
            localStorage.removeItem(DELETED_KEY);
            await this.loadProfiles(true, data.profile.id);
        } catch (error) { failure = error; }
        finally {
            this.busy = false;
            this.render();
            if (failure) this.error(failure);
            else this.info("Набор восстановлен вместе с кешированными изображениями.");
            this.schedulePoll();
        }
    }

    async copy() {
        try { await navigator.clipboard.writeText(this.promptText.textContent); this.info("Промпт скопирован."); }
        catch { this.error(new Error("Браузер запретил буфер обмена. Выделите теги эмоции и скопируйте вручную.")); }
    }
}

async function openGallery() {
    try {
        if (!gallery) gallery = new EmotionGallery(await request("/config"));
        await gallery.open();
    } catch (error) {
        if (gallery?.dialog.open) gallery.error(error);
        else app.extensionManager.toast.add({ severity: "error", summary: "ComfyUI Emotional Gallery", detail: t(error.message), life: 8000 });
    }
}

app.registerExtension({
    name: "EmotionalGallery.Expressions",
    async setup() {
        hideGalleryRegisteredNodes(globalThis.LiteGraph.registered_node_types);
        const stylesheet = element("link");
        stylesheet.rel = "stylesheet";
        stylesheet.href = new URL("./gallery.css", import.meta.url).href;
        await new Promise(resolve => {
            stylesheet.onload = resolve;
            stylesheet.onerror = resolve;
            document.head.append(stylesheet);
        });
        mountLauncher(app.menu.element, () => openGallery());
    },
    beforeRegisterVueAppNodeDefs(nodeDefs) {
        hideGalleryNodeDefinitions(nodeDefs);
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (galleryNodeNames.has(nodeData.name)) nodeType.skip_list = true;
    },
});
