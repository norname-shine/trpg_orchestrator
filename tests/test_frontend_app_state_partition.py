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
        "rawAssets",
        "rawGallery",
        "renderedRawAssets",
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
        "rawAssets",
        "rawGallery",
        "modulePayloadCache",
        "renderedRawAssets",
        "galleryFilter",
        "galleryFilterIds",
        "renderedMapKey",
        "currentMapAsset",
        "writebackReview",
        "currentPressurePack",
        "storyProgressPayload",
        "storyProgressChapter",
        "storyProgressNode",
        "rawInventoryState",
        "rawInventoryItems",
        "inventoryEvents",
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
        "state.gallery.rawGallery = {}",
        "state.gallery.rawAssets = []",
        "state.gallery.renderedRawAssets = []",
        "state.gallery.selectedGalleryKey = \"\"",
        "state.gallery.transientGalleryAsset = null",
        "state.map.renderedMapKey = \"\"",
        "state.map.currentMapAsset = null",
        "state.story.currentPressurePack = {}",
        "state.story.storyProgressPayload = {}",
        "state.story.storyProgressChapter = {}",
        "state.story.storyProgressNode = {}",
        "state.character.rawInventoryState = {}",
        "state.character.rawInventoryItems = []",
        "state.character.inventoryEvents = []",
        "state.character.latestDossierPayload = null",
    ):
        assert expected in body


def test_main_frontend_entry_functions_exist():
    source = app_source()

    for name in ("refresh", "renderStatus", "renderFrontendState", "renderOutput"):
        assert f"function {name}(" in source or f"async function {name}(" in source


def test_gallery_filters_load_from_raw_gallery_without_scene_fallback():
    source = app_source()
    fallback_block = source.split("const FALLBACK_ASSET_CONTRACT = {", 1)[1].split("};", 1)[0]

    assert "/api/asset-contract" in function_body(source, "loadAssetContract")
    assert "/api/extensions/gallery" in function_body(source, "loadRawGallery")
    assert "raw.assets" in function_body(source, "loadRawGallery")
    assert "rawGalleryFilters" in function_body(source, "renderGalleryFilters")
    assert "galleryFiltersFromAssetContract" not in function_body(source, "renderGalleryFilters")
    for category in ('id: "prop"', 'id: "item"', 'id: "character"', 'id: "map"', 'id: "cg"'):
        assert category in fallback_block
    assert 'id: "scene"' not in fallback_block
    assert "galleryFiltersFromTaxonomy" not in source


def test_gallery_rendering_uses_raw_gallery_assets_only():
    source = app_source()
    render_body = function_body(source, "renderGallery")
    load_body = function_body(source, "loadRawGallery")
    open_body = function_body(source, "openGalleryOverlay")
    hydrate_body = function_body(source, "hydrateLazyFrontendModules")

    assert "rawGalleryAssets()" in render_body
    assert "cachedGalleryAssets" not in render_body
    assert "mergeGalleryAssets" not in render_body
    assert "/api/extensions/gallery" in load_body
    assert "/api/module/gallery" not in open_body
    assert 'name !== "gallery"' in hydrate_body


def test_raw_gallery_asset_fields_are_preserved_for_rendering():
    source = app_source()
    bodies = "\n".join(
        function_body(source, name)
        for name in (
            "renderGallery",
            "renderGalleryFilters",
            "protocolRawGalleryAsset",
            "rawGalleryAssets",
            "galleryAssetMatchesFilter",
            "galleryMapAssetFromEntry",
        )
    )

    assert "asset.category || asset.type" in bodies
    assert "raw_asset: asset" in bodies
    assert "rawGalleryAssetMediaUrl" in bodies
    assert "gallery_category" in bodies
    assert "display_zone" in bodies
    for forbidden in (
        ".metadata",
        "metadata.",
        "entity_key",
        "visible_in_gallery",
        "runtime_role",
        "portrait_asset_kind",
        "normalizeGalleryKind",
        "fixedGalleryKind",
        "normalizeAssetIdentity",
        "asset.role",
        "title.includes",
        "key.includes",
    ):
        assert forbidden not in bodies


def test_gallery_visibility_and_map_candidate_logic_follow_new_contract():
    source = app_source()
    match_body = function_body(source, "galleryAssetMatchesFilter")
    map_body = function_body(source, "isRawMapAsset") + function_body(source, "bestCurrentMapAsset")

    assert 'value === "all") return true' in match_body
    assert "return category === value" in match_body
    assert 'type === "map"' in map_body
    assert 'zone === "map"' in map_body
    assert "protocolRawGalleryAsset(rawMap)" in map_body
    assert "scene" not in map_body
    assert "metadata" not in map_body


def test_inventory_loads_from_extension_endpoint():
    source = app_source()
    refresh_body = function_body(source, "refresh")
    load_body = function_body(source, "loadRawInventory")
    hydrate_body = function_body(source, "hydrateLazyFrontendModules")

    assert "loadRawInventory(nextCampaign)" in refresh_body
    assert "/api/extensions/inventory" in load_body
    assert "rawState.items" in load_body
    assert "rawEvents.events" in load_body
    assert "/api/module/inventory" not in source
    assert "latestInventoryPayload" not in source
    assert 'name === "inventory"' not in hydrate_body


def test_inventory_rendering_uses_raw_inventory_items_only():
    source = app_source()
    body = function_body(source, "protocolInventoryRows")
    raw_body = function_body(source, "protocolRawInventoryItem")

    assert "state.character.rawInventoryItems" in body
    assert "frontendState.inventory" not in body
    assert "itemRows(campaignState)" not in body
    assert "item.item_id" in raw_body
    assert "item.title" in raw_body
    assert "item.state" in raw_body
    assert "item.payload" in raw_body
    assert "source_item_id" in raw_body
    assert "raw_item: item" in raw_body
    for forbidden in ("title.includes", "category.includes", "detail.includes", "slugify(", "dedupeInventoryRows"):
        assert forbidden not in body + raw_body


def test_inventory_empty_state_and_duplicate_titles_are_preserved():
    source = app_source()
    side_body = function_body(source, "renderSidePanel")
    raw_body = function_body(source, "protocolInventoryRows") + function_body(source, "protocolRawInventoryItem")

    assert "暂无物品" in side_body or "鏆傛棤鐗╁搧" in side_body
    assert 'state.ui.sideTab === "items" ? rows : rows.slice(-5)' in side_body
    assert ".map(protocolRawInventoryItem).filter(Boolean)" in raw_body
    assert "new Map" not in raw_body
    assert "byKey" not in raw_body
