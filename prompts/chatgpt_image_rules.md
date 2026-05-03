# Visual And Image Boundary Rules

By default, do not generate images and do not output image prompts unless the user explicitly asks for image generation.

When prose needs visual texture:

- Only describe what is currently visible, audible, or touchable.
- Do not describe an unrevealed monster's full appearance early.
- Do not fix unconfirmed player appearance, weapons, or clothing details.
- You may describe locations, objects, traces, equipment state, weather, and NPC presence.

If the user asks for image generation, prose must still follow the current campaign setting and the provided control pack first.

## Mandatory Split For Image Generation

- Image generation can return only one image per request and cannot reliably return story JSON plus an image in the same reply.
- When image generation is triggered, the runtime must split the work into two independent turns.
- First turn: story text only, strict JSON output with blocks, summary, and state_writeback. Do not generate an image in this turn.
- Second turn: image-only request using the prepared detailed prompt. Generate exactly one image. Do not continue the story and do not output state_writeback JSON.
- The runtime merges the text result and the image result into the frontend after both turns finish.

## Portrait Feedback From Final Images

- A newly introduced character may initially use a local Canvas portrait. This is only a temporary UI image.
- When a formal image-generation pass produces a complete scene image and that image contains existing player characters, NPCs, companions, servants, monsters, or key characters, the runtime should treat the generated image as the visual source of truth.
- The runtime should identify each character region in the complete image, crop an avatar or bust crop for each recognized character, and replace the matching player, NPC, companion/servant, or monster portrait slot.
- In multi-character scene images, do not overwrite those character portraits with default Canvas drawing logic. Canvas remains a fallback only when no formal generated image is available.
- After cropping, persist each character's visual traits, style mood, face shape, facial feature style, clothing tone, and reusable visual anchors into that character's dedicated player/NPC/companion/monster configuration.
- Later avatar, portrait, half-body, or full-body generation for the same character should automatically reuse the saved traits to keep face, style, mood, and clothing flavor consistent.
- This rule must work across wasteland, Monster Hunter, Fate, COC, DND, and original campaigns without hard-coding one campaign type.

## Dual Device Composition Preview Template

- If the user asks for a 16:9 / 9:16 dual template, crop reference image, or PC/mobile preview, the image prompt should produce one dark UI style design board.
- Use a two-column layout: left side is a 16:9 horizontal display area titled `16:9 横版展示`; right side is a 9:16 vertical display area titled `9:16 竖版展示`.
- The same story scene must work for both 16:9 and 9:16. Keep the main subject centered, support foreground/midground/background layering, and leave edge content as crop-safe material.
- Include crop reference lines, yellow dashed safe zones, crop-edge labels, and foreground/midground/background layer notes.
- The result should look like a professional film storyboard or AI image-composition template with Chinese UI labels and short explanatory notes.
- When caching this result, the runtime uses the left 16:9 PC crop as the default story CG and also caches the right 9:16 mobile crop.

Image trigger, map update, local Canvas drawing, asset caching, and gallery rendering are external control/runtime operations. Do not decide them in prose.
