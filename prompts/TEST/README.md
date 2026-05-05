# TEST Prompt Folder

This folder contains prompt drafts for manual testing and review.

These files are not referenced by `prompt_modules.json` and are not used by the running TRPG server unless a developer copies or wires them into the formal prompt pipeline.

## Files

- `v4_campaign_setup_prompt_TEST.md`
  - V4 director prompt for campaign initialization.
  - Focus: story structure, protagonist setup, companion setup, public waiting notes, and initialization memory.
- `v4_director_turn_prompt_TEST.md`
  - V4 director prompt for normal turns.
  - Focus: pressure pack, structured progress, inventory semantics, map/visual triggers, and safe public notes.
- `chatgpt_actor_prompt_TEST.md`
  - ChatGPT actor prompt for player-facing prose.
  - Focus: immersive prose JSON, progress writeback evidence, no director override, no unauthorized payloads.

## Test Method

1. Pick one prompt file.
2. Paste it as the system/developer instruction for the target model.
3. Paste one example input from `examples/`.
4. Check the model output against the matching `expected_shape_*.md`.

Do not treat these files as production rules until the output has been reviewed.
