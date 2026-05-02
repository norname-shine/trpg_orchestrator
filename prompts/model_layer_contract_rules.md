# Model Layer Contract Rules

This file defines responsibility boundaries among DeepSeek V4, ChatGPT, and Codex. It is a backend orchestration rule, not a campaign-specific story setting.

## Fixed Flow

1. The player enters an action in the frontend, and the backend receives the raw instruction.
2. The backend first sends the player action, current campaign memory, and long-term records to DeepSeek V4.
3. DeepSeek V4 is fixed as the director layer. It outputs only this turn's macro pressure pack and structured director decisions.
4. The backend receives V4 output and must not push V4 content directly to the player frontend.
5. The backend forwards V4's director pressure pack, the player action, and allowed visible memory to ChatGPT.
6. ChatGPT is fixed as the actor layer. It turns the V4 pressure pack into player-readable prose and structured writeback.
7. The backend closes the loop: parse ChatGPT JSON, update prose, character state, map, items, tasks, tags, gallery, asset cache, and local records.

## Responsibilities

- DeepSeek V4 is the director layer. It handles macro decisions, plot direction, pressure packs, image-trigger decisions, map-update decisions, NPC direction, and knowledge boundaries. It does not write final prose.
- ChatGPT is the actor layer. It performs the scene, dialogue, atmosphere, player-readable `blocks`, and `state_writeback` according to the V4 pressure pack. It must not override V4.
- Codex is the local engineering layer. It maintains code, APIs, frontend rendering, schemas, prompt files, parsing, encoding checks, asset cache, QA, writeback audit, and persistence. It does not participate in the real story chain.

## Non-Reversal Constraints

- Fixed order: player input -> V4 director layer -> ChatGPT actor layer -> backend closeout -> frontend refresh.
- Do not let ChatGPT generate prose first and ask V4 to infer director decisions afterward.
- Do not display V4 output as player prose.
- Do not let Codex mix into director or actor duties for debugging convenience.
- Model rules must remain in separate files so each layer can be iterated or replaced independently.
