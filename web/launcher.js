import { localize } from "./locale.js";

const POSITION_KEY = "emotional-gallery.launcher.v1";

export function mountLauncher(dockHost, openGallery) {
    const panel = document.createElement("div");
    panel.className = "eg-launcher-panel";
    panel.setAttribute("role", "toolbar");
    panel.setAttribute("aria-label", "Кнопка галереи эмоций");
    const handle = document.createElement("button");
    handle.type = "button";
    handle.className = "eg-launcher-handle";
    handle.setAttribute("aria-label", "Переместить кнопку Эмоции");
    handle.title = "Перетащите за точки. Enter — закрепить или открепить; стрелки — переместить.";
    const launch = document.createElement("button");
    launch.type = "button";
    launch.className = "eg-launcher";
    launch.textContent = "◉ Эмоции";
    launch.title = "Open ComfyUI Emotional Gallery";
    launch.addEventListener("click", openGallery);
    panel.append(handle, launch);

    // ComfyUI mounts this public legacy-menu element in its native top bar.
    const slot = document.createElement("div");
    slot.className = "eg-launcher-slot";
    slot.hidden = true;
    dockHost.append(slot);
    const hint = document.createElement("div");
    hint.className = "eg-launcher-drop";
    hint.textContent = "Закрепить Эмоции";
    const translate = () => { localize(panel); localize(hint); };
    translate();

    let state = { mode: "floating", x: Math.max(0, innerWidth - 165), y: 106 };
    try {
        const saved = JSON.parse(localStorage.getItem(POSITION_KEY));
        if (saved && ["floating", "docked"].includes(saved.mode) && Number.isFinite(saved.x) && Number.isFinite(saved.y)) state = saved;
    } catch { /* Use the initial position when storage is unavailable. */ }
    let drag = null;
    const save = () => {
        try { localStorage.setItem(POSITION_KEY, JSON.stringify(state)); } catch { /* Position storage is optional. */ }
    };
    function position(x, y) {
        state.x = Math.max(0, Math.min(x, innerWidth - panel.offsetWidth));
        state.y = Math.max(0, Math.min(y, innerHeight - panel.offsetHeight));
        panel.style.left = `${state.x}px`;
        panel.style.top = `${state.y}px`;
    }
    function floating(x, y) {
        state.mode = "floating";
        panel.classList.remove("eg-launcher-docked");
        if (panel.parentNode !== document.body) document.body.append(panel);
        position(x, y);
    }
    function dock() {
        state.mode = "docked";
        panel.classList.add("eg-launcher-docked");
        panel.style.removeProperty("left");
        panel.style.removeProperty("top");
        slot.hidden = false;
        slot.replaceChildren(panel);
    }
    function overSlot(x, y) {
        const bounds = slot.getBoundingClientRect();
        return bounds.width > 0 && bounds.height > 0 && x >= bounds.left && x <= bounds.right && y >= bounds.top && y <= bounds.bottom;
    }
    function finish(cancel = false) {
        if (!drag) return;
        const previous = drag;
        drag = null;
        panel.classList.remove("eg-launcher-dragging");
        slot.classList.remove("eg-launcher-drop-active");
        if (previous.moved) {
            if (cancel) {
                state = previous.original;
                if (state.mode === "docked") dock();
                else floating(state.x, state.y);
            } else if (overSlot(previous.x, previous.y)) dock();
            if (state.mode === "floating") { slot.replaceChildren(); slot.hidden = true; }
            save();
        }
        if (handle.hasPointerCapture(previous.id)) handle.releasePointerCapture(previous.id);
    }
    handle.addEventListener("pointerdown", event => {
        if (event.button !== 0 || drag) return;
        const bounds = panel.getBoundingClientRect();
        drag = { id: event.pointerId, original: { ...state }, startX: event.clientX, startY: event.clientY,
            offsetX: event.clientX - bounds.left, offsetY: event.clientY - bounds.top, x: event.clientX, y: event.clientY, moved: false };
        handle.setPointerCapture(event.pointerId);
        event.preventDefault();
        handle.focus({ preventScroll: true });
    });
    handle.addEventListener("pointermove", event => {
        if (!drag || event.pointerId !== drag.id) return;
        if (!drag.moved && Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) < 4) return;
        drag.moved = true;
        drag.x = event.clientX;
        drag.y = event.clientY;
        floating(event.clientX - drag.offsetX, event.clientY - drag.offsetY);
        if (hint.parentNode !== slot) slot.replaceChildren(hint);
        slot.hidden = false;
        panel.classList.add("eg-launcher-dragging");
        handle.setPointerCapture(event.pointerId);
        slot.classList.toggle("eg-launcher-drop-active", overSlot(event.clientX, event.clientY));
    });
    handle.addEventListener("pointerup", event => {
        if (drag && event.pointerId === drag.id) {
            drag.x = event.clientX; drag.y = event.clientY;
            finish();
        }
    });
    handle.addEventListener("pointercancel", () => finish(true));
    handle.addEventListener("keydown", event => {
        if (event.key === "Escape") { if (drag) { event.preventDefault(); finish(true); } return; }
        if (drag) return;
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (state.mode === "docked") { floating(state.x, state.y); slot.replaceChildren(); slot.hidden = true; }
            else dock();
        } else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
            event.preventDefault();
            const bounds = panel.getBoundingClientRect();
            const step = event.shiftKey ? 1 : 10;
            floating(bounds.left + (event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0),
                bounds.top + (event.key === "ArrowDown" ? step : event.key === "ArrowUp" ? -step : 0));
            slot.replaceChildren(); slot.hidden = true;
        } else return;
        handle.focus({ preventScroll: true });
        save();
    });
    window.addEventListener("resize", () => { if (state.mode === "floating" && !drag) { position(state.x, state.y); save(); } });
    if (state.mode === "docked") dock();
    else floating(state.x, state.y);
    return panel;
}
