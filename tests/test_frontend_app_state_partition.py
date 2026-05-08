import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "app.js"


def app_source():
    return APP_JS.read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    assert match, f"missing function {name}"
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    return source[start:index - 1]


def test_app_js_node_check_passes():
    completed = subprocess.run(
        ["node", "--check", str(APP_JS)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_state_declares_expected_partitions_and_helpers():
    source = app_source()

    for partition in ("campaign", "story", "assets", "gallery", "map", "character", "writeback", "job", "ui"):
        assert re.search(rf"\b{partition}\s*:\s*\{{", source)
    for helper in (
        "activeCampaignId",
        "currentFrontendState",
        "currentCampaignState",
        "currentAssets",
        "currentGalleryState",
        "currentRunProgress",
        "currentAssetCache",
        "currentModulePayloadCache",
        "currentUiState",
        "currentStoryState",
    ):
        assert f"function {helper}(" in source


def test_legacy_state_proxy_remains_available():
    source = app_source()

    assert "const LEGACY_STATE_FIELDS = {" in source
    assert "function partitionLegacyState()" in source
    assert "partitionLegacyState();" in source

    for field in (
        "campaigns",
        "activeCampaign",
        "frontendState",
        "assetCache",
        "galleryAssets",
        "currentMapAsset",
        "writebackReview",
        "characterProfileExpanded",
        "characterProfileCampaign",
        "ruleFiles",
        "selectedRule",
        "runProgress",
        "dragPanels",
        "activeReferenceDrag",
    ):
        assert re.search(rf"\b{field}\s*:\s*\[", source), f"missing legacy proxy for {field}"


def test_low_risk_state_access_uses_partitions():
    source = app_source()
    legacy_reads = (
        "activeCampaign",
        "selectedCampaign",
        "frontendState",
        "lastCampaignState",
        "assetSeed",
        "streamingPreview",
        "assetCache",
        "cachedAssets",
        "modulePayloadCache",
        "galleryAssets",
        "galleryFilter",
        "galleryFilterIds",
        "galleryTaxonomy",
        "renderedMapKey",
        "currentMapAsset",
        "writebackReview",
        "currentPressurePack",
        "storyProgressPayload",
        "storyProgressChapter",
        "storyProgressNode",
        "latestInventoryPayload",
        "latestDossierPayload",
        "runProgress",
        "sideTab",
        "activePanel",
        "autoScroll",
        "collapsedPanels",
        "dragPanels",
        "activeDragPanel",
        "characterProfileExpanded",
        "characterProfileCampaign",
        "ruleFiles",
        "selectedRule",
        "activeReferenceDrag",
        "campaigns",
    )

    for field in legacy_reads:
        assert not re.search(rf"\bstate\.{field}\b", source), f"state.{field} should use a partition"


def test_remaining_legacy_state_fields_use_partitions():
    source = app_source()

    for expected in (
        "state.character.characterProfileExpanded",
        "state.character.characterProfileCampaign",
        "state.ui.ruleFiles",
        "state.ui.selectedRule",
        "state.ui.activeReferenceDrag",
        "state.campaign.campaigns",
    ):
        assert expected in source


def test_reset_campaign_scoped_state_keeps_drag_panel_layout():
    body = function_body(app_source(), "resetCampaignScopedUiState")

    assert "dragPanels" not in body
    assert "collapsedPanels" not in body
    assert "activeDragPanel" not in body
    assert "activeReferenceDrag" not in body
    for preference in ("sideTab", "activePanel", "autoScroll"):
        assert preference not in body


def test_reset_campaign_scoped_state_clears_cross_campaign_caches():
    body = function_body(app_source(), "resetCampaignScopedUiState")

    for expected in (
        "state.assets.assetCache = {}",
        "state.assets.cachedAssets = []",
        "state.assets.visualContracts = {}",
        "state.assets.modulePayloadCache = {}",
        "state.gallery.galleryAssets = []",
        "state.gallery.selectedGalleryKey = \"\"",
        "state.gallery.transientGalleryAsset = null",
        "state.map.renderedMapKey = \"\"",
        "state.map.currentMapAsset = null",
        "state.story.currentPressurePack = {}",
        "state.story.storyProgressPayload = {}",
        "state.story.storyProgressChapter = {}",
        "state.story.storyProgressNode = {}",
        "state.character.latestInventoryPayload = null",
        "state.character.latestDossierPayload = null",
    ):
        assert expected in body


def test_main_frontend_entry_functions_exist():
    source = app_source()

    for name in ("refresh", "renderStatus", "renderFrontendState", "renderOutput"):
        assert f"function {name}(" in source or f"async function {name}(" in source
