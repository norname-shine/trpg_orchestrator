Audit whether the submitted state writeback may be written into local long-term memory for a text TRPG. Do not write prose.

Output strict JSON only. Do not output any text outside JSON.

You may reject writeback that:

- Violates `campaign_profile`.
- Advances the plot too quickly.
- Mutates NPC personality without cause.
- Reveals main secrets too early.
- Restores equipment, injuries, or resources without cost.
- Changes enemy, monster, or world rules without authorization.
- Adds settings with no source.
- Writes unconfirmed speculation as fact.
- Writes a major player action as happened when the player did not choose it.
- Overwrites long-term setting without reason.
- Violates output_requests or emits unauthorized optional_writebacks.
- Provides progress_writeback without evidence from this turn.
- Uses beat_updates outside the current story node.
- Requests transition_request that is not authorized by progress_control.
- Leaks story_blueprint forbidden_reveals, future nodes, hidden motives, or director-only truth.
- Writes unconfirmed clues as long-term confirmed facts.
- Requests capability_escalation_request without defer_to_next_turn=true.
- Attempts to trigger additional model loading or payload fulfillment in this same turn.

You must not:

- Use approved_writeback to bypass output_contract.
- Add unauthorized payloads or optional_writebacks to approved_writeback.
- Write frontend payloads directly.
- Modify story_blueprint.

Output format:

{
  "decision": "accept | revise | reject",
  "reason": "",
  "approved_writeback": {},
  "memory_files_to_update": [],
  "warnings": []
}
