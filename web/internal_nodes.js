export const galleryNodeNames = new Set([
    "EGCharacterEmotion", "EGCacheImage", "EGLoadCachedEmotion", "EGCheckpointLoader",
    "EGDiffusionLoader", "EGTextEncoderLoader", "EGVAELoader",
    "EGDualTextEncoderLoader", "EGTripleTextEncoderLoader",
]);

export function hideGalleryNodeDefinitions(definitions) {
    for (let index = definitions.length - 1; index >= 0; index--) {
        if (galleryNodeNames.has(definitions[index].name)) definitions.splice(index, 1);
    }
}

export function hideGalleryRegisteredNodes(registry) {
    for (const name of galleryNodeNames) {
        const descriptor = Object.getOwnPropertyDescriptor(registry, name);
        if (descriptor) Object.defineProperty(registry, name, { ...descriptor, enumerable: false });
    }
}
