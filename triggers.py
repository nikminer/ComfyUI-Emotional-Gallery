"""Read locally saved LoRA activation words without loading model tensors."""
import json
import re
import struct
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

TRIGGER_KEYS = ("trainedWords", "trained_words", "triggerWords", "trigger_words", "activation_text", "ss_activation_text", "modelspec.trigger_phrase")
TRIGGER_LABEL = re.compile(r"(?:trigger(?:\s+words?|\s+tags?)?|activation(?:\s+words?|\s+tags?)?|trained\s+words?)\s*[:：]\s*(.+)", re.I)


def word_groups(value):
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("["):
            try:
                return word_groups(json.loads(value))
            except json.JSONDecodeError:
                pass
        return [part.strip(" `\t") for part in value.splitlines() if part.strip(" `\t")]
    if isinstance(value, list):
        return [group for item in value[:200] for group in word_groups(item)]
    if isinstance(value, dict):
        return word_groups(value.get("word", value.get("text", "")))
    return []


class DescriptionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.codes = []
        self.code = None

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "br", "div", "li", "h2", "h3", "pre"):
            self.text.append("\n")
        if tag == "code":
            context = "".join(self.text)[-250:]
            self.code = [] if re.search(r"trigger|activation|trained words", context, re.I) else None

    def handle_endtag(self, tag):
        if tag == "code" and self.code is not None:
            self.codes.append("".join(self.code))
            self.code = None
        if tag in ("p", "div", "li", "h2", "h3", "pre"):
            self.text.append("\n")

    def handle_data(self, data):
        self.text.append(data)
        if self.code is not None:
            self.code.append(data)


def description_groups(value):
    if not isinstance(value, str):
        return []
    parser = DescriptionParser()
    parser.feed(value[:200000])
    groups = list(parser.codes)
    for line in "".join(parser.text).splitlines():
        match = TRIGGER_LABEL.search(line)
        if match:
            groups.extend(word_groups(unescape(match[1])))
    return groups


def extract_groups(data):
    if not isinstance(data, dict):
        return []
    civitai = data.get("civitai", {})
    raw = data.get("raw", {})
    raw_civitai = raw.get("civitai", {}) if isinstance(raw, dict) else {}
    containers = [data, civitai, raw_civitai, data.get("__metadata__", {})]
    for container in containers:
        if not isinstance(container, dict):
            continue
        for key in TRIGGER_KEYS:
            groups = word_groups(container.get(key))
            if groups:
                return groups
    groups = []
    for container in containers:
        if isinstance(container, dict):
            model = container.get("model", {})
            for key in ("description", "modelDescription", "notes", "usage_tips"):
                groups.extend(description_groups(container.get(key)))
            if isinstance(model, dict):
                groups.extend(description_groups(model.get("description")))
    return groups


def read_trigger_words(lora_path):
    path = Path(lora_path)
    candidates = [path.with_suffix(".metadata.json"), path.with_suffix(".info.json"), Path(str(path) + ".rgthree-info.json"), path.with_suffix(".civitai.info"), path.with_suffix(".json")]
    sources = []
    groups = []
    warnings = []
    for sidecar in candidates:
        if not sidecar.is_file():
            continue
        try:
            if sidecar.stat().st_size > 4 * 1024 * 1024:
                warnings.append(f"Skipped oversized metadata: {sidecar.name}")
                continue
            found = extract_groups(json.loads(sidecar.read_text(encoding="utf-8-sig")))
        except (json.JSONDecodeError, UnicodeError):
            warnings.append(f"Invalid metadata: {sidecar.name}")
            continue
        if found:
            groups.extend(found)
            sources.append(sidecar.name)
            break
    if not groups and path.suffix.lower() == ".safetensors":
        with path.open("rb") as stream:
            length = stream.read(8)
            if len(length) == 8:
                size = struct.unpack("<Q", length)[0]
                if 0 < size <= 16 * 1024 * 1024 and size <= path.stat().st_size - 8:
                    try:
                        groups = extract_groups(json.loads(stream.read(size)))
                    except (json.JSONDecodeError, UnicodeError):
                        warnings.append("Invalid safetensors metadata header")
                    if groups:
                        sources.append("LoRA file metadata")
    seen = set()
    result = []
    for group in groups:
        group = group.strip(" ,`\n\t")
        if not group or len(group) > 20000 or group.casefold() in seen:
            continue
        seen.add(group.casefold())
        result.append(group)
        if len(result) >= 200:
            break
    return {"groups": result, "sources": sources, "warnings": warnings}
