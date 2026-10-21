const translations = new Map(Object.entries({
    "Галерея эмоций персонажа": "Character expression gallery", "Выражения персонажа": "Character expressions",
    "Закрыть галерею": "Close gallery", "Персонаж и генерация": "Character and generation",
    "Тип модели": "Model type", "LoRA персонажа": "Character LoRA", "Выберите LoRA…": "Choose a LoRA…",
    "Выбрать LoRA персонажа": "Choose character LoRA", "Имя персонажа, Anima, папка…": "Character name, Anima, folder…",
    "Поиск LoRA": "Search LoRAs", "Найденные LoRA": "Matching LoRAs",
    "Обновить список моделей и LoRA": "Refresh models and LoRAs",
    "Введите слова активации из описания LoRA.": "Enter trigger words from the LoRA description.",
    "Сила MODEL": "MODEL strength", "Сила CLIP": "CLIP strength", "Базовый промпт": "Base prompt",
    "Негативный промпт": "Negative prompt", "Ширина": "Width", "Высота": "Height", "Шаги": "Steps",
    "Seed (одинаковый для всех эмоций)": "Seed (same for every expression)",
    "Сохранённые галереи этой LoRA": "Saved galleries for this LoRA", "Создать галерею": "Create gallery",
    "Удалить набор": "Delete set", "Убрать выбранный набор из списка; его можно восстановить": "Remove this set; it can be restored",
    "+ Своя эмоция": "+ Custom expression", "Добавить свою эмоцию": "Add custom expression", "Новая эмоция": "New expression",
    "Название эмоции": "Expression name", "Например: Скепсис": "For example: Skepticism", "Промпт эмоции": "Expression prompt",
    "Категория эмоции": "Expression category", "Добавить эмоцию": "Add expression", "Отмена": "Cancel",
    "Опишите выражение лица, желательно на английском. Оно добавится к промпту персонажа и сохранится для всех LoRA.": "Describe the facial expression, preferably in English. It will be added to the character prompt and saved for all LoRAs.",
    "Выбранное выражение лица": "Selected facial expression", "В workflow": "Apply to workflow", "Как изображение": "Use as image",
    "Копировать эмоцию": "Copy expression", "Перегенерировать": "Regenerate", "Сгенерировать эмоцию": "Generate expression",
    "Остановить оставшиеся": "Cancel pending jobs", "Восстановить удалённый набор": "Restore deleted set",
    "Догенерировать категорию": "Generate missing in category", "Нет превью": "No preview", "В кеше": "Cached",
    "Генерация…": "Generating…", "В очереди": "Queued", "Ошибка · повторить": "Error · retry", "Подготовка…": "Preparing…",
    "Догенерировать набор": "Generate missing in set", "Ничего не найдено. Измените запрос.": "No matches. Try another search.",
    "Пока нет сохранённых галерей": "No saved galleries yet",
    "Своя эмоция сохранена. Нажмите «Сгенерировать эмоцию» для её превью или догенерируйте весь набор.": "Custom expression saved. Generate its preview or generate missing expressions in the set.",
    "Настройки изменены. Кнопка генерации создаст соответствующий набор; ниже показан сохранённый кеш.": "Settings changed. Create gallery uses these settings; Generate missing in group uses the saved set.",
    "Выберите модель и LoRA. Для Anima также нужны text encoder и VAE; список можно обновить.": "Choose a model and LoRA. Anima also needs a text encoder and VAE; refresh the list if needed.",
    "Кеш сохранён. Выберите выражение и примените его к workflow.": "Cache saved. Choose an expression and apply it to your workflow.",
    "Выберите LoRA, укажите trigger words и создайте галерею.": "Choose a LoRA, enter trigger words and create a gallery.",
    "Все выбранные эмоции уже готовы или находятся в очереди.": "All selected expressions are already cached or queued.",
    "Набор удалён из списка. Его можно восстановить кнопкой внизу.": "Set removed. Use the button below to restore it.",
    "Набор восстановлен вместе с кешированными изображениями.": "Set restored, including cached images.",
    "Сначала создайте или откройте галерею": "Create or open a gallery first",
    "Узел расширения недоступен. Перезапустите ComfyUI.": "Extension node unavailable. Restart ComfyUI.",
    "Выражение применено к узлу персонажа.": "Expression applied to the character node.",
    "Узел персонажа добавлен. Подключите MODEL, CLIP и positive_prompt к вашему workflow.": "Character node added. Connect MODEL, CLIP and positive_prompt to your workflow.",
    "Кешированное изображение выбрано в узле Load Cached Emotion.": "Cached image selected in the Load Cached Emotion node.",
    "Промпт скопирован.": "Expression prompt copied.",
    "Браузер запретил буфер обмена. Выделите теги эмоции и скопируйте вручную.": "Clipboard access denied. Select the expression tags and copy them manually.",
    "Открыть галерею эмоций": "Open expression gallery", "Ошибка запроса": "Request failed", "Ошибка генерации": "Generation failed",
    "Seed должен быть целым неотрицательным числом": "Seed must be a non-negative integer", "Seed превышает 64-битный диапазон": "Seed exceeds the 64-bit range",
    "Кнопка галереи эмоций": "Expression gallery launcher", "Переместить кнопку Эмоции": "Move Expressions button",
    "Перетащите за точки. Enter — закрепить или открепить; стрелки — переместить.": "Drag the dots. Enter docks or undocks; arrow keys move the button.",
    "◉ Эмоции": "◉ Expressions", "Открыть Emotional Gallery": "Open Emotional Gallery", "Закрепить Эмоции": "Dock Expressions",
    "Ошибка генерации. Проверьте совместимость модели и LoRA.": "Generation failed. Check model and LoRA compatibility.",
    "Ожидается название и промпт эмоции": "Expression name and prompt required", "Некорректный идентификатор окна ComfyUI": "Invalid ComfyUI client ID",
    "Дождитесь завершения генерации набора. Ожидающие задачи можно остановить.": "Wait for this set to finish generating. Pending jobs can be cancelled.",
    "Не удалось удалить набор": "Could not delete the set", "Удалённый набор не найден": "Deleted set not found", "Не удалось восстановить набор": "Could not restore the set",
    "Выберите известные эмоции": "Choose valid expressions", "Workflow генератора не прошёл проверку ComfyUI": "Generator workflow failed ComfyUI validation",
    "Введите название эмоции (до 80 символов)": "Enter an expression name (up to 80 characters)",
    "Введите промпт выражения лица (до 4000 символов)": "Enter a facial expression prompt (up to 4000 characters)",
    "Выберите категорию эмоции": "Choose an expression category", "Эмоция с таким названием уже существует": "An expression with this name already exists",
    "Галерея ещё не создана": "Gallery has not been created yet", "Эта эмоция ещё не сгенерирована": "This expression has not been generated yet",
    "Набор с такими настройками уже существует. Восстановление его не перезапишет.": "A set with these settings already exists. Restore will not overwrite it.",
    "Настройки должны быть объектом": "Settings must be an object", "Ожидается объект настроек": "Settings object required",
    "Выберите SD 1.5 / SDXL или Anima": "Choose SD 1.5 / SDXL or Anima", "force должен быть логическим значением": "force must be a boolean",
    "Некорректный ID галереи": "Invalid gallery ID", "Недопустимый путь галереи": "Invalid gallery path",
    "Некорректный ID удалённого набора": "Invalid deleted set ID", "Недопустимый путь удалённого набора": "Invalid deleted set path",
    "Неизвестная эмоция": "Unknown expression", "Изображение отсутствует в кеше": "Image not found in cache",
    "Некорректная библиотека своих эмоций": "Invalid custom expression library", "Некорректный ID своей эмоции": "Invalid custom expression ID",
    "Некорректное название своей эмоции": "Invalid custom expression name", "Некорректный промпт своей эмоции": "Invalid custom expression prompt",
    "Некорректная категория своей эмоции": "Invalid custom expression category",
}));
const patterns = [
    [/^У узла отсутствует поле (.+)$/, (_, field) => `Node is missing field ${field}`],
    [/^(\d+) встроенных · своих: (\d+)$/, (_, built, custom) => `${built} built-in · ${custom} custom`],
    [/^Догенерировать категорию: (.+)$/, (_, category) => `Generate missing in category: ${t(category)}`],
    [/^В библиотеке: (\d+) LoRA · нажмите для поиска$/, (_, count) => `${count} LoRAs · click to search`],
    [/^Найдено: (\d+) \/ (\d+)$/, (_, found, total) => `Found: ${found} / ${total}`],
    [/^Доступно diffusion models: (\d+)\. Выберите Anima и совместимую LoRA\. Qwen3 0\.6B и Qwen Image VAE загружаются отдельно\.$/, (_, count) => `${count} diffusion models available. Choose Anima and a compatible LoRA. Qwen3 0.6B and Qwen Image VAE load separately.`],
    [/^Доступно checkpoints: (\d+)\. LoRA должна соответствовать SD 1\.5 \/ SDXL\.$/, (_, count) => `${count} checkpoints available. LoRA must match SD 1.5 / SDXL.`],
    [/^Список обновлён: (\d+) diffusion models, (\d+) checkpoints, (\d+) LoRA\.$/, (_, models, checkpoints, loras) => `List refreshed: ${models} diffusion models, ${checkpoints} checkpoints, ${loras} LoRAs.`],
    [/^Проверьте поле (.+)$/, (_, field) => `Check field ${field}`],
    [/^В наборе (\d+) выражений\. Готовые карточки сохраняются на диске\.$/, (_, count) => `${count} expressions in this set. Generated previews are saved to disk.`],
    [/^В очереди \/ генерации: (\d+)\. Можно закрыть окно — работа продолжится\.$/, (_, count) => `Queued / generating: ${count}. You can close this window; generation will continue.`],
    [/^(\d+) эмоций с ошибкой\. (.+)$/, (_, count, message) => `${count} expressions failed. ${t(message)}`],
    [/^Добавлено в очередь: (\d+)\. Результаты появятся автоматически\.$/, (_, count) => `Queued: ${count}. Results will appear automatically.`],
    [/^Убрано из очереди: (\d+)\. Текущая генерация завершится\.$/, (_, count) => `Removed from queue: ${count}. The current generation will finish.`],
    [/^Не удалось сохранить эмоцию: (.+)$/, (_, message) => `Could not save expression: ${message}`],
    [/^Не удалось прочитать модель или записать кеш: (.+)$/, (_, message) => `Could not read model or write cache: ${message}`],
    [/^Выберите доступное значение: (.+)$/, (_, field) => `Choose an available value: ${field}`],
    [/^Некорректный текст: (.+)$/, (_, field) => `Invalid text: ${field}`],
    [/^(.+): ожидается целое число от (\d+) до (\d+)$/, (_, field, min, max) => `${field}: expected an integer from ${min} to ${max}`],
    [/^(.+): размер должен быть кратен (\d+)$/, (_, field, multiple) => `${field}: size must be a multiple of ${multiple}`],
    [/^Некорректное значение: (.+)$/, (_, field) => `Invalid value: ${field}`],
];

export function registerLabels(items) {
    for (const item of items) if (item.label_en) translations.set(item.label, item.label_en);
}
export function t(text) {
    if (typeof text !== "string") return text;
    if (translations.has(text)) return translations.get(text);
    for (const [pattern, format] of patterns) if (pattern.test(text)) return text.replace(pattern, format);
    return text;
}
export function localize(root) {
    root.lang = "en";
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        const node = walker.currentNode;
        const translated = t(node.nodeValue);
        if (translated !== node.nodeValue) node.nodeValue = translated;
    }
    for (const node of [root, ...root.querySelectorAll("*")]) {
        for (const key of ["aria-label", "title", "placeholder", "alt"]) {
            if (node.hasAttribute(key)) {
                const value = node.getAttribute(key);
                const translated = t(value);
                if (translated !== value) node.setAttribute(key, translated);
            }
        }
    }
}
