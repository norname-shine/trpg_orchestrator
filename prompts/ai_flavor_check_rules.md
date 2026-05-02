# AI Flavor Check Rules

Mechanical check items:

- Step-by-step plot summary instead of lived scene.
- Functional NPC lines that only explain the task.
- Dialogue that is too short, too hard, or reads like quotable one-liners.
- Too much narrator explanation.
- Phrases equivalent to "this shows", "this represents", or "this means".
- Frequent contrast formula such as "not A, but B".
- Choices that read like game buttons.
- The protagonist acting like a camera instead of a person under pressure.
- Monsters, enemies, or danger entering in an overly orderly way.
- Prose that is too smooth, templated, or frictionless.
- Every detail serving as obvious foreshadowing.
- Plot jumps too fast.
- NPC personality changes without cause.
- New settings with no source.
- Violation of `forbidden_changes`.
- State writeback records speculation as fact.

Handling:

- Minor issue: ask ChatGPT to rewrite the affected part.
- Severe issue: ask DeepSeek V4 to generate a correction directive, then have ChatGPT rewrite.
- Rewrite at most 2 times.
- Stop if the output still fails after 2 rewrites.
