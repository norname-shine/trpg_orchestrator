# ChatGPT Visual And Image Boundary Rules

By default, do not generate images and do not output image prompts unless the user explicitly asks for image generation.

When prose needs visual texture:

- Only describe what is currently visible, audible, or touchable.
- Do not describe an unrevealed monster's full appearance early.
- Do not fix unconfirmed player appearance, weapons, or clothing details.
- You may describe locations, objects, traces, equipment state, weather, and NPC presence.

If the user asks for image generation, prose must still follow the current campaign setting and the V4 pressure pack first.

Image trigger, map update, local Canvas drawing, asset caching, and gallery rendering are not ChatGPT responsibilities. Those decisions and operations belong to the V4 director layer and the Codex local engineering layer.
