"""The expression vocabulary shared by the nodes and gallery API."""

import re

CUSTOM_ID = re.compile(r"^custom_[0-9a-f]{32}$")

EMOTIONS = [
    ("neutral", "Нейтральное", "neutral expression, relaxed face, closed mouth"),
    ("smile", "Улыбка", "gentle smile, happy expression"),
    ("joy", "Радость", "bright smile, joyful expression, sparkling eyes"),
    ("laugh", "Смех", "laughing, open mouth smile, eyes squinting with joy"),
    ("sad", "Грусть", "sad expression, downturned mouth, sorrowful eyes"),
    ("cry", "Слёзы", "crying, tears on cheeks, sad expression"),
    ("angry", "Злость", "angry expression, furrowed brows, glaring"),
    ("furious", "Ярость", "furious expression, clenched teeth, deeply furrowed brows"),
    ("surprised", "Удивление", "surprised expression, wide eyes, open mouth"),
    ("shocked", "Шок", "shocked expression, raised eyebrows, wide open eyes and mouth"),
    ("fear", "Страх", "frightened expression, worried wide eyes, tense mouth"),
    ("worried", "Тревога", "worried expression, knitted brows, nervous eyes"),
    ("shy", "Смущение", "shy expression, blushing cheeks, averted eyes, small smile"),
    ("confident", "Уверенность", "confident expression, composed smile, direct gaze"),
    ("smirk", "Усмешка", "smirk, one corner of mouth raised, mischievous expression"),
    ("wink", "Подмигивание", "winking, one eye closed, playful smile"),
    ("thinking", "Задумчивость", "thoughtful expression, eyes looking to the side, closed mouth"),
    ("confused", "Растерянность", "confused expression, one eyebrow raised, puzzled look"),
    ("disgust", "Отвращение", "disgusted expression, wrinkled nose, curled upper lip"),
    ("sleepy", "Сонливость", "sleepy expression, half-closed eyes, relaxed mouth"),
]
EMOTION_MAP = {key: {"id": key, "label": label, "prompt": prompt} for key, label, prompt in EMOTIONS}
# Keep the original cache identity when the selectable library grows.
CACHE_EMOTION_MAP = EMOTION_MAP.copy()
CATEGORIES = {"sfw": "SFW", "nsfw": "NSFW"}
SUBCATEGORIES = {
    "sfw": {"neutral": "Neutral", "smile": "Smile", "affection": "Affection", "smirk": "Smirk", "playful": "Playful",
            "blush": "Blush", "sadness": "Sadness", "anger": "Anger", "surprise": "Surprise", "worry": "Worry", "custom": "Custom"},
    "nsfw": {"ahegao": "Ahegao", "torogao": "Torogao", "ohogao": "Ohogao", "ohhoai": "Ohhoai",
             "ikigao": "Ikigao", "aroused": "Aroused", "seductive": "Seductive smile", "custom": "Custom"},
}
# Organize related facial expressions without changing their prompts or cache IDs.
SUBCATEGORY_MEMBERS = {
    "sfw": {
        "neutral": "neutral thinking keeping_calm sleepy".split(),
        "smile": "smile joy laugh peaceful_happiness suppressed_smile".split(),
        "affection": "relaxed_smile gentle_invitation loving_gaze dreamy_gaze".split(),
        "smirk": "confident smirk confident_flirt sly_smile proud_blush mischievous_smirk unexpected_confidence".split(),
        "playful": "wink playful_gaze teasing_grin".split(),
        "blush": "shy sudden_blush hidden_blush timid_smile awkward_smile upturned_blush happy_blush".split(),
        "sadness": "sad cry embarrassed_tears".split(),
        "anger": "angry furious disgust embarrassed_indignation embarrassed_irritation".split(),
        "surprise": "surprised shocked confused exaggerated_surprise overwhelmed dizzy_face lost_expression".split(),
        "worry": "fear worried bitten_lip nervous_wait".split(),
    },
    "nsfw": {
        "ahegao": "ahegao ahegao_rolled ahegao_tears ahegao_hearts ahegao_closed".split(),
        "torogao": "torogao torogao_side torogao_tears afterglow blank_blush".split(),
        "ohogao": "ohogao upturned_pucker kiss_face proud_pucker".split(),
        "ohhoai": "ohhoai heart_dazed wide_eyes_tongue nose_scrunch_tongue".split(),
        "ikigao": "ikigao clenched_blush closed_round_mouth wavy_tears".split(),
        "aroused": "in_heat aroused dilated_blush teary_pleading".split(),
        "seductive": "naughty_face seductive_smile lip_lick tongue_corner lip_bite_wink sharp_grin".split(),
    },
}
SUBCATEGORY_BY_EMOTION = {emotion: subcategory for groups in SUBCATEGORY_MEMBERS.values() for subcategory, members in groups.items() for emotion in members}
LEGACY_CATEGORIES = frozenset(["basic", "flirt", "embarrassment", "tenderness", "romance", "comedy", "tension", "confidence", "custom"])


def normalize_category(category):
    if not isinstance(category, str):
        raise ValueError("Выберите категорию эмоции")
    if category in LEGACY_CATEGORIES:
        return "sfw"
    if category not in CATEGORIES:
        raise ValueError("Выберите категорию эмоции")
    return category


def normalize_subcategory(category, subcategory=None):
    if subcategory is None or subcategory == "":
        return "custom"
    if not isinstance(subcategory, str) or subcategory not in SUBCATEGORIES[category]:
        raise ValueError("Choose a subcategory within the selected category")
    return subcategory


ADDITIONAL_EMOTIONS = {
    "nsfw": [
        ("ahegao", "Ахегао (Ahegao)", "ahegao, cross-eyed, tongue out, blush"),
        ("torogao", "Торогао (Torogao)", "torogao, half-closed eyes, blush, parted lips"),
        ("ohogao", "Охогао (Ohogao)", "ohogao, cross-eyed, puckered lips, blush"),
        ("ohhoai", "Оххоаи (Ohhoai)", "ohhoai, one eye half-closed, one eye open, heart-shaped pupil, tongue out"),
        ("ikigao", "Икигао (Ikigao)", "ikigao, closed eyes, open mouth, blush"),
        ("acmegao", "Акмегао (Acmegao)", "acmegao, closed eyes, parted lips, full-face blush"),
        ("yogarigao", "Йогаригао (Yogarigao)", "yogarigao, half-closed eyes, parted lips, blush"),
        ("afterglow", "Afterglow", "afterglow, half-closed eyes, light smile, blush"),
        ("in_heat", "In heat", "in heat, half-closed eyes, full-face blush"),
        ("aroused", "Aroused", "aroused, blush, parted lips, looking at viewer"),
        ("naughty_face", "Naughty face", "naughty face, smirk, narrowed eyes"),
        ("nsfw_seductive_smile", "Seductive smile", "seductive smile, half-closed eyes, looking at viewer"),
        ("ahegao_rolled", "Ахегао · закатившиеся глаза", "ahegao, rolled-back eyes, wide open mouth, tongue out, full-face blush"),
        ("ahegao_tears", "Ахегао · слёзы и улыбка", "ahegao, cross-eyed, tears, toothy grin, tongue out, blush"),
        ("ahegao_hearts", "Ахегао · сердечки в зрачках", "ahegao, heart-shaped pupils, wide-eyed, open mouth, tongue out, blush"),
        ("ahegao_closed", "Ахегао · зажмуренные глаза", "ahegao, tightly closed eyes, raised eyebrows, wide open mouth, tongue out, blush"),
        ("torogao_side", "Торогао · взгляд в сторону", "torogao, half-closed eyes, looking to the side, faint smile, blush"),
        ("torogao_tears", "Торогао · влажные глаза", "torogao, teary-eyed, drooping eyelids, closed mouth, blush"),
        ("upturned_pucker", "Взгляд вверх и вытянутые губы", "upturned eyes, puckered lips, raised eyebrows, full-face blush"),
        ("kiss_face", "Воздушный поцелуй", "closed eyes, puckered lips, relaxed eyebrows, light blush"),
        ("lip_lick", "Облизывание верхней губы", "licking upper lip, narrowed eyes, mischievous smile, blush"),
        ("tongue_corner", "Язык у уголка рта", "tongue at corner of mouth, sidelong glance, asymmetrical smirk, blush"),
        ("clenched_blush", "Стиснутые зубы и румянец", "clenched teeth, tightly closed eyes, tense eyebrows, full-face blush"),
        ("teary_pleading", "Слёзный умоляющий взгляд", "teary-eyed, raised inner eyebrows, looking at viewer, open mouth, blush"),
        ("blank_blush", "Пустой взгляд с румянцем", "empty eyes, straight eyebrows, closed mouth, blank expression, full-face blush"),
        ("dilated_blush", "Расширенные зрачки", "dilated pupils, wide-eyed, parted lips, raised eyebrows, blush"),
        ("heart_dazed", "Сердечки и открытый рот", "heart-shaped pupils, dazed, drooping eyebrows, open mouth, full-face blush"),
        ("closed_round_mouth", "Закрытые глаза и округлённый рот", "closed eyes, round mouth, relaxed eyebrows, full-face blush"),
        ("wavy_tears", "Дрожащие губы и слёзы", "teary-eyed, wavy mouth, furrowed brow, full-face blush"),
        ("lip_bite_wink", "Подмигивание с прикушенной губой", "winking, one eye open, biting lower lip, raised eyebrow, blush"),
        ("nose_scrunch_tongue", "Сморщенный нос и язык", "scrunched nose, squinting eyes, tongue out, blush"),
        ("proud_pucker", "Надменный взгляд и вытянутые губы", "chin raised, looking down at viewer, narrowed eyes, puckered lips, blush"),
        ("wide_eyes_tongue", "Удивлённый взгляд с языком", "wide-eyed, raised eyebrows, tongue out, open mouth, blush"),
        ("sharp_grin", "Хищная улыбка", "sharp teeth, wide grin, narrowed eyes, lowered eyebrows, blush"),
    ],
    "flirt": [
        ("playful_gaze", "Игривый взгляд", "playful smile, half-closed eyes, looking at viewer"),
        ("seductive_smile", "Соблазнительная улыбка", "seductive smile, bedroom eyes, blush"),
        ("confident_flirt", "Самоуверенный флирт", "smug, smirk, narrowed eyes"),
        ("shy_flirt", "Застенчивый флирт", "shy, light blush, looking at viewer"),
        ("sly_smile", "Лукавая улыбка", "smirk, head tilt, half-closed eyes"),
        ("gentle_invitation", "Нежное приглашение", "gentle smile, parted lips, relaxed eyes"),
    ],
    "embarrassment": [
        ("sudden_blush", "Внезапное смущение", "flustered, blush, wide-eyed"),
        ("hidden_blush", "Попытка скрыть смущение", "blush, pout, looking away"),
        ("nervous_anticipation", "Нервное предвкушение", "nervous smile, blush, parted lips"),
        ("timid_smile", "Робкая улыбка", "shy smile, light blush, downcast eyes"),
        ("embarrassed_indignation", "Смущённое возмущение", "angry, embarrassed, blush, furrowed brow"),
        ("deep_confusion", "Сильная растерянность", "deep blush, nervous, wide-eyed"),
    ],
    "tenderness": [
        ("relaxed_smile", "Расслабленная улыбка", "content, gentle smile, half-closed eyes"),
        ("peaceful_happiness", "Безмятежное счастье", "closed eyes, relaxed eyebrows, slight smile"),
        ("happy_blush", "Счастливое смущение", "happy, blush, closed eyes, smile"),
        ("dreamy_gaze", "Мечтательный взгляд", "dreamy, half-closed eyes, slight smile"),
        ("quiet_contentment", "Тихая радость", "pleased, relaxed eyes, parted lips"),
        ("vulnerable_smile", "Эмоциональная уязвимость", "blush, downcast eyes, slight smile"),
    ],
    "romance": [
        ("soft_gaze", "Томный взгляд", "bedroom eyes, half-closed eyes, blush"),
        ("loving_gaze", "Влюблённый взгляд", "heart-shaped pupils, blush, smile"),
        ("teasing_grin", "Задорная провокация", "teasing, smug, tongue out"),
        ("awkward_smile", "Неловкая улыбка", "embarrassed, looking away, nervous smile"),
        ("warm_affection", "Тёплая привязанность", "soft smile, relaxed eyes, looking at viewer"),
        ("sleepy_tenderness", "Сонная нежность", "sleepy, half-closed eyes, gentle smile"),
    ],
    "comedy": [
        ("dazed_gaze", "Затуманенный взгляд", "dazed, half-closed eyes, blush"),
        ("lost_expression", "Потерянное выражение", "unfocused eyes, parted lips, blush"),
        ("intense_nervousness", "Сильное волнение", "deep blush, wide-eyed, sweat"),
        ("dizzy_face", "Головокружение", "dizzy, spiral eyes, wavy mouth"),
        ("blushing_surprise", "Удивление с румянцем", "shocked, deep blush, parted lips"),
        ("exaggerated_surprise", "Преувеличенное удивление", "wide-eyed, round mouth, full-face blush"),
    ],
    "tension": [
        ("bitten_lip", "Прикушенная губа", "biting own lip, blush, narrowed eyes"),
        ("suppressed_smile", "Подавленная улыбка", "closed mouth, blush, half-closed eyes"),
        ("embarrassed_irritation", "Смущённое раздражение", "annoyed, flustered, full-face blush"),
        ("keeping_calm", "Попытка сохранить спокойствие", "serious, half-closed eyes, blush"),
        ("nervous_wait", "Нервное ожидание", "nervous, parted lips, sweat"),
        ("upturned_blush", "Смущённый взгляд снизу", "upturned eyes, blush, parted lips"),
        ("hidden_worry", "Скрытое волнение", "looking away, blush, biting own lip"),
        ("embarrassed_tears", "Смущение со слезами", "embarrassed, teary-eyed, full-face blush"),
    ],
    "confidence": [
        ("proud_blush", "Самодовольная улыбка", "doyagao, smug, blush"),
        ("inviting_gaze", "Призывающий взгляд", "seductive smile, looking at viewer, narrowed eyes"),
        ("mischievous_smirk", "Озорная усмешка", "smirk, raised eyebrow, blush"),
        ("assured_flirt", "Уверенный флирт", "seductive smile, half-closed eyes, closed mouth"),
        ("unexpected_confidence", "Неожиданная самоуверенность", "smug, narrowed eyes, parted lips"),
        ("restrained_emotion", "Сдерживаемая эмоция", "biting own lip, blush, furrowed brow"),
        ("nervous_grin", "Нервная улыбка", "nervous smile, sweat, blush"),
        ("overwhelmed", "Ошеломление", "dazed, wide-eyed, parted lips"),
    ],
}
EMOTION_MAP = {key: {**item, "category": "basic"} for key, item in EMOTION_MAP.items()}
for category, expressions in ADDITIONAL_EMOTIONS.items():
    for key, label, prompt in expressions:
        EMOTION_MAP[key] = {"id": key, "label": label, "prompt": prompt, "category": category}

# Retain old IDs for saved workflows and direct access to cached images.
RETIRED_EMOTIONS = {
    "shy_flirt": "shy", "deep_confusion": "sudden_blush",
    "vulnerable_smile": "timid_smile", "quiet_contentment": "gentle_invitation",
    "warm_affection": "smile", "sleepy_tenderness": "relaxed_smile",
    "soft_gaze": "in_heat", "dazed_gaze": "torogao",
    "intense_nervousness": "sudden_blush", "blushing_surprise": "exaggerated_surprise",
    "nervous_anticipation": "nervous_wait", "nervous_grin": "nervous_wait",
    "hidden_worry": "bitten_lip", "restrained_emotion": "bitten_lip",
    "assured_flirt": "seductive_smile", "inviting_gaze": "seductive_smile",
    "nsfw_seductive_smile": "seductive_smile", "acmegao": "ikigao", "yogarigao": "torogao",
}
EMOTION_MAP["seductive_smile"]["category"] = "nsfw"
ENGLISH_LABELS = {
    "neutral": "Neutral", "smile": "Smile", "joy": "Joy", "laugh": "Laughter",
    "sad": "Sadness", "cry": "Tears", "angry": "Anger", "furious": "Rage",
    "surprised": "Surprise", "shocked": "Shock", "fear": "Fear", "worried": "Worry",
    "shy": "Shyness", "confident": "Confidence", "smirk": "Smirk", "wink": "Wink",
    "thinking": "Thoughtful", "confused": "Confusion", "disgust": "Disgust", "sleepy": "Sleepiness",
    "ahegao": "Ahegao", "torogao": "Torogao", "ohogao": "Ohogao", "ohhoai": "Ohhoai", "ikigao": "Ikigao",
    "ahegao_rolled": "Ahegao · rolled-back eyes", "ahegao_tears": "Ahegao · tears and grin",
    "ahegao_hearts": "Ahegao · heart pupils", "ahegao_closed": "Ahegao · eyes squeezed shut",
    "torogao_side": "Torogao · sidelong glance", "torogao_tears": "Torogao · watery eyes",
    "upturned_pucker": "Upturned eyes and puckered lips", "kiss_face": "Blowing a kiss",
    "lip_lick": "Licking upper lip", "tongue_corner": "Tongue at mouth corner",
    "clenched_blush": "Clenched teeth and blush", "teary_pleading": "Teary pleading gaze",
    "blank_blush": "Blank stare with blush", "dilated_blush": "Dilated pupils",
    "heart_dazed": "Heart pupils and open mouth", "closed_round_mouth": "Closed eyes and round mouth",
    "wavy_tears": "Trembling lips and tears", "lip_bite_wink": "Wink with lip bite",
    "nose_scrunch_tongue": "Scrunched nose and tongue", "proud_pucker": "Haughty gaze and puckered lips",
    "wide_eyes_tongue": "Surprised gaze with tongue", "sharp_grin": "Predatory grin",
    "in_heat": "In heat", "naughty_face": "Naughty face", "seductive_smile": "Seductive smile",
}
CATEGORY_LABELS_EN = CATEGORIES.copy()
for key, definition in EMOTION_MAP.items():
    definition["category"] = normalize_category(definition["category"])
    definition["subcategory"] = SUBCATEGORY_BY_EMOTION.get(key, SUBCATEGORY_BY_EMOTION.get(RETIRED_EMOTIONS.get(key), "custom"))
    definition["label_en"] = ENGLISH_LABELS.get(key, key.replace("_", " ").capitalize())
ACTIVE_EMOTION_MAP = {key: item for key, item in EMOTION_MAP.items() if key not in RETIRED_EMOTIONS}


def custom_definitions(values):
    if not isinstance(values, dict):
        raise ValueError("Некорректная библиотека своих эмоций")
    for key, item in values.items():
        if not isinstance(key, str) or not CUSTOM_ID.fullmatch(key) or not isinstance(item, dict) or item.get("id") != key:
            raise ValueError("Некорректный ID своей эмоции")
        if not isinstance(item.get("label"), str) or not 1 <= len(item["label"].strip()) <= 80:
            raise ValueError("Некорректное название своей эмоции")
        if not isinstance(item.get("prompt"), str) or not 1 <= len(item["prompt"].strip()) <= 4000:
            raise ValueError("Некорректный промпт своей эмоции")
        normalize_subcategory(normalize_category(item.get("category", "sfw")), item.get("subcategory"))
    return {key: {**item, "category": normalize_category(item.get("category", "sfw")),
                 "subcategory": normalize_subcategory(normalize_category(item.get("category", "sfw")), item.get("subcategory"))} for key, item in values.items()}


def expression_prompt(base_prompt, trigger_words, emotion, definition=None):
    definition = definition or EMOTION_MAP.get(emotion)
    if not definition or definition.get("id") != emotion:
        raise ValueError("Неизвестная эмоция")
    expression = definition.get("prompt")
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 4000:
        raise ValueError("Введите промпт выражения лица (до 4000 символов)")
    return ", ".join(part.strip(" ,\n") for part in (trigger_words, base_prompt, expression) if part.strip(" ,\n"))
