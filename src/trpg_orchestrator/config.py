from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGNS_DIR = PROJECT_ROOT / "campaigns"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTBOX_DIR = PROJECT_ROOT / "outbox"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REGISTRY_PATH = CAMPAIGNS_DIR / "campaign_registry.json"


MEMORY_FILE_NAMES = [
    "campaign_profile.json",
    "character_prompt.json",
    "campaign_direction.json",
    "npc_profiles.json",
    "monster_profiles.json",
    "style_profile.json",
    "image_profile.json",
    "player_state.json",
    "npc_memory.json",
    "world_state.json",
    "location_history.json",
    "quest_history.json",
    "enemy_or_monster_ecology.json",
    "equipment_history.json",
    "main_threads.json",
    "recent_context.json",
    "forbidden_changes.json",
]


@dataclass(frozen=True)
class CampaignPaths:
    campaign_id: str
    root: Path
    logs: Path
    backups: Path

    @classmethod
    def from_id(cls, campaign_id: str) -> "CampaignPaths":
        root = CAMPAIGNS_DIR / campaign_id
        return cls(
            campaign_id=campaign_id,
            root=root,
            logs=root / "logs",
            backups=root / "backups",
        )
