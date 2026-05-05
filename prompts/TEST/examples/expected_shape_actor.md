# Expected Shape: Actor

- Output is strict JSON only.
- Blocks include one player action echo and at least one GM narration block.
- Prose is Chinese and player-facing.
- No system pipeline language appears in prose.
- `progress_writeback.beat_updates` only references provided beat IDs.
- Beat evidence is visible in `blocks`.
- Transition is `stay` unless the prose clearly reaches `c1_n2_clue`.
- No inventory payload is invented because inventory update is not authorized.
