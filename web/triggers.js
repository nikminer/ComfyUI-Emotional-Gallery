const STORAGE_KEY = "emotional-gallery.triggers.v1";

export function splitTriggerTags(text) {
    const words = [];
    let depth = 0, start = 0;
    for (let i = 0; i < text.length; i++) {
        if ("([{".includes(text[i])) depth++;
        else if (")]}".includes(text[i])) depth = Math.max(0, depth - 1);
        else if ((text[i] === "," || text[i] === "\n") && !depth) { words.push(text.slice(start, i).trim()); start = i + 1; }
    }
    words.push(text.slice(start).trim());
    const seen = new Set();
    return words.filter(word => { const key = word.toLowerCase(); if (!word || seen.has(key)) return false; seen.add(key); return true; });
}

export function toggleTriggerTags(text, group) {
    const active = splitTriggerTags(text), words = splitTriggerTags(group);
    const selected = new Set(active.map(word => word.toLowerCase()));
    if (words.every(word => selected.has(word.toLowerCase()))) {
        const removing = new Set(words.map(word => word.toLowerCase()));
        return active.filter(word => !removing.has(word.toLowerCase())).join(", ");
    }
    return splitTriggerTags([...active, ...words].join(", ")).join(", ");
}

function button(text, action) {
    const node = document.createElement("button");
    node.type = "button"; node.textContent = text;
    node.addEventListener("click", action);
    return node;
}

export class TriggerPicker {
    constructor(input, loadMetadata, onChange) {
        this.input = input; this.loadMetadata = loadMetadata; this.onChange = onChange;
        this.groups = []; this.extra = []; this.lora = ""; this.revision = 0; this.request = 0;
        this.saved = {};
        try { const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); if (saved && typeof saved === "object" && !Array.isArray(saved)) this.saved = saved; } catch { /* No saved toggles. */ }
        this.panel = document.createElement("div"); this.panel.className = "eg-triggers";
        const tools = document.createElement("div"); tools.className = "eg-trigger-tools";
        const mode = document.createElement("label");
        this.groupMode = document.createElement("input"); this.groupMode.type = "checkbox";
        mode.append(this.groupMode, document.createTextNode("Group mode"));
        this.groupMode.addEventListener("change", () => { this.persist(); this.render(); });
        tools.append(button("All on", () => this.update(splitTriggerTags([...this.groups, ...this.extra].join(", ")).join(", "))),
            button("All off", () => this.update("")), mode, button("Reload tags", () => this.load(this.lora, false)));
        this.chips = document.createElement("div"); this.chips.className = "eg-trigger-chips"; this.chips.setAttribute("aria-label", "Trigger word toggles");
        this.status = document.createElement("p"); this.status.className = "eg-hint"; this.status.setAttribute("role", "status");
        this.panel.append(tools, this.chips, this.status);
        input.before(this.panel);
        input.placeholder = "Add or edit trigger words here…";
        input.addEventListener("input", () => { this.sync(); this.persist(); });
    }

    persist() {
        if (!this.lora) return;
        this.saved[this.lora] = { text: this.input.value, groupMode: this.groupMode.checked };
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(this.saved)); } catch { /* Toggles still work without storage. */ }
    }

    sync() {
        this.revision++;
        this.extra = splitTriggerTags([...this.extra, this.input.value].join(", "));
        this.render();
    }

    update(text) {
        this.input.value = text;
        this.input.dispatchEvent(new Event("input", {bubbles: true}));
        this.onChange();
    }

    async load(lora, autoFill = false) {
        const ticket = ++this.request;
        const changed = this.lora !== lora;
        this.lora = lora;
        if (changed) {
            this.groups = []; this.extra = [];
            const saved = this.saved[lora];
            this.groupMode.checked = !!saved?.groupMode;
            if (autoFill && saved && typeof saved.text === "string") this.update(saved.text);
        }
        this.sync();
        const revision = this.revision;
        this.status.textContent = "Loading local trigger words…";
        try {
            const metadata = await this.loadMetadata(lora);
            if (ticket !== this.request || this.lora !== lora) return;
            this.groups = metadata.groups;
            if (autoFill && this.revision === revision && !this.input.value.trim() && !this.saved[lora] && this.groups.length) this.update(this.groups[0]);
            this.status.textContent = this.groups.length ? `Local metadata: ${this.groups.length} groups. Click tags to include or exclude them.` : "No local trigger words found. Add them manually below.";
            if (metadata.warnings?.length) this.status.textContent += ` ${metadata.warnings[0]}`;
            this.render();
        } catch (error) {
            if (ticket !== this.request) return;
            this.status.textContent = `${error.message}. You can edit trigger words manually.`;
            this.render();
        }
    }

    render() {
        const active = new Set(splitTriggerTags(this.input.value).map(word => word.toLowerCase()));
        const units = this.groupMode.checked ? [...this.groups, ...this.extra.filter(word => !this.groups.some(group => splitTriggerTags(group).some(tag => tag.toLowerCase() === word.toLowerCase())))] : splitTriggerTags([...this.groups, ...this.extra].join(", "));
        this.chips.replaceChildren();
        for (const unit of [...new Set(units)].slice(0, 500)) {
            const chip = button(unit, () => this.update(toggleTriggerTags(this.input.value, unit)));
            chip.className = "eg-trigger-chip";
            chip.title = unit;
            chip.setAttribute("aria-pressed", String(splitTriggerTags(unit).every(word => active.has(word.toLowerCase()))));
            this.chips.append(chip);
        }
    }
}
