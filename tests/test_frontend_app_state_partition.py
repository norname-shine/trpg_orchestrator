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


def test_story_turn_signature_uses_backend_turn_id_and_deferred_shell_does_not_clear_story():
    source = app_source()
    signature_body = function_body(source, "storyTurnSignature")
    render_body = function_body(source, "renderOutput")
    hydrate_body = function_body(source, "hydrateLazyFrontendModules")

    assert "turn_id: output.turn_id || output.parsed?.turn_id || \"\"" in signature_body
    assert "if (!(output.blocks_deferred && !blocks.length))" in render_body
    assert "turn_id: data.payload.turn_id || \"\"" in hydrate_body


def test_story_output_is_gated_until_run_progress_completes():
    source = app_source()
    render_body = function_body(source, "renderOutput")
    complete_body = function_body(source, "completeRunProgress")
    begin_body = function_body(source, "beginRunProgress")
    refresh_story_body = function_body(source, "refreshStoryLogNow")

    assert "pendingStoryOutput: null" in source
    assert "state.job.runProgress.pendingStoryOutput = null" in begin_body
    assert "state.job.runProgress.phase = \"\"" in begin_body
    assert "state.job.runProgress.phaseStartedAt = Date.now()" in begin_body
    assert "shouldGateStoryOutput(output, options)" in render_body
    assert "state.job.runProgress.pendingStoryOutput = output" in render_body
    assert "state.job.runProgress.percent = 100" in complete_body
    assert "paintRunProgress(100)" in complete_body
    assert "const target = pipeline.percent >= 100 && !state.job.runProgress.completing ? 96 : pipeline.percent" in function_body(source, "updateRunProgressFromPipeline")
    assert "preCompleteWaitMs" in complete_body
    assert "MIN_RUN_PROGRESS_MS" in complete_body
    assert "RUN_PROGRESS_COMPLETE_HOLD_MS" in complete_body
    assert "finalStoryOutput = await loadLatestStoryLogOutput()" in complete_body
    assert "renderOutput(finalStoryOutput || state.job.runProgress.pendingStoryOutput || {}, { force: true })" in complete_body
    assert "const output = await loadLatestStoryLogOutput()" in refresh_story_body
    assert "function loadLatestStoryLogOutput()" in source


def test_run_progress_rotates_public_think_and_splits_phases():
    source = app_source()
    stream_body = function_body(source, "renderRunStreamText")
    stage_body = function_body(source, "runProgressPhaseForStage")
    apply_body = function_body(source, "applyRunProgressStage")
    rotate_body = function_body(source, "rotatingPublicThink")
    tween_body = function_body(source, "startRunProgressTween")

    assert "renderRunStreamText()" in tween_body
    assert "rotatingPublicThink(think)" in stream_body
    assert ".map((item)" not in stream_body
    assert "phaseStartedAt" in rotate_body
    assert "/ 2200" in rotate_body
    assert '"director_turn"' in stage_body
    assert '"actor_waiting"' in stage_body
    assert '"light_analysis"' in stage_body
    assert 'state.job.runProgress.phase === "director" && phase === "actor"' in apply_body
    assert "paintRunProgress(100)" in apply_body


def test_gallery_filters_load_from_asset_contract_without_raw_category_growth():
    source = app_source()
    fallback_block = source.split("const FALLBACK_ASSET_CONTRACT = {", 1)[1].split("};", 1)[0]

    assert "/api/asset-contract" in function_body(source, "loadAssetContract")
    assert "/api/extensions/gallery" in function_body(source, "loadRawGallery")
    assert "raw.assets" in function_body(source, "loadRawGallery")
    assert "rawGalleryFilters" in function_body(source, "renderGalleryFilters")
    assert "galleryFiltersFromAssetContract(state.assets.assetContract || FALLBACK_ASSET_CONTRACT)" in function_body(source, "rawGalleryFilters")
    assert "state.gallery.rawAssets || []" not in function_body(source, "rawGalleryFilters")
    assert "galleryFiltersFromAssetContract(state.assets.assetContract || FALLBACK_ASSET_CONTRACT)" in function_body(source, "registeredGalleryCategoryIds")
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

    assert "asset.gallery_category" in bodies
    assert "asset.category || asset.type" not in bodies
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


def test_raw_gallery_canvas_jobs_cache_back_to_source_asset_and_custom_filter():
    source = app_source()
    media_body = function_body(source, "rawGalleryAssetMediaUrl")
    rank_body = function_body(source, "galleryCachedAssetRank")
    current_map_body = function_body(source, "bestCurrentMapAsset")
    jobs_body = function_body(source, "processCanvasJobs")

    assert "state.assets.cachedAssets" in media_body
    assert "subject_key" in media_body
    assert "`gallery:${assetId}`" in media_body
    assert "desiredGalleryRendererVersion(asset)" in media_body
    assert "galleryCachedAssetRank(b, desiredRenderer)" in media_body
    assert "galleryCachedAssetRank(a, desiredRenderer)" in media_body
    assert "versionedAssetUrl(cached.url, cached.key || cached.created_at || cached.renderer_version)" in media_body
    assert "renderer === desiredRenderer" in rank_body
    assert "bestCachedCurrentMapAsset()" in current_map_body
    assert "bestRawMapAsset()" not in current_map_body
    assert "job.source === \"gallery_raw\"" in jobs_body
    assert "subject_key: job.subject_key || `gallery:${job.asset_id || job.asset_key}`" in jobs_body
    assert "gallery_category: job.gallery_category || \"character\"" in jobs_body
    assert "gallery_category: job.gallery_category || job.kind" in jobs_body


def test_raw_gallery_scene_specs_use_custom_canvas_renderer_not_item_fallback():
    source = app_source()
    jobs_body = function_body(source, "processCanvasJobs")
    scene_body = function_body(source, "drawCustomSceneCanvas")
    custom_scene_body = function_body(source, "hasCustomSceneCanvasSpec")

    assert "hasCustomSceneCanvasSpec(canvasSpec)" in jobs_body
    assert "drawCustomSceneCanvas(canvas, job.title || job.asset_key || job.job_id, canvasSpec" in jobs_body
    assert "renderer_version: job.renderer_version || \"\"" in jobs_body
    assert "variant: job.renderer_version || undefined" in jobs_body
    assert "scene_canvas_spec" in custom_scene_body
    assert "spec.subjects" in scene_body
    assert "drawSceneSpecSubject" in scene_body


def test_show_map_image_binds_visibility_handlers_after_asset_url_assignment():
    body = function_body(app_source(), "showMapImage")

    assert body.index("setAssetImage(img, url)") < body.index("img.onload =")
    assert "if (img.complete && img.naturalWidth > 0)" in body


def test_current_map_panel_renders_map_asset_protocol_directly():
    source = app_source()
    semantic_body = function_body(source, "hasSemanticMapCanvas")
    render_body = function_body(source, "renderCachedMap")

    assert "hasMapAssetProtocolSpec(mapCanvas)" in semantic_body
    assert "drawMapAssetProtocol(canvas, mapCanvas)" in render_body
    assert "drawPixelMap(seed" in render_body


def test_gallery_map_card_opens_current_map_instead_of_rendering_separate_asset():
    source = app_source()
    open_body = function_body(source, "openAssetFromGallery")
    media_body = function_body(source, "rawGalleryAssetMediaUrl")

    assert "isRawMapAsset(asset)" in open_body
    assert "openCurrentMapOverlay()" in open_body
    assert "state.map.currentMapAsset?.cachedUrl" in media_body


def test_gallery_visibility_and_map_candidate_logic_follow_new_contract():
    source = app_source()
    match_body = function_body(source, "galleryAssetMatchesFilter")
    map_body = function_body(source, "isRawMapAsset") + function_body(source, "bestCurrentMapAsset")

    assert "const categories = normalizeGalleryCategories" in match_body
    assert "const registered = registeredGalleryCategoryIds()" in match_body
    assert "const validCategories = categories.filter((item) => registered.has(item))" in match_body
    assert 'value === "all") return true' in match_body
    assert "return validCategories.includes" in match_body
    assert 'type === "map"' in map_body
    assert 'zone === "map"' in map_body
    assert "bestCachedCurrentMapAsset()" in map_body
    assert "protocolRawGalleryAsset(rawMap)" not in map_body
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


def test_gallery_inspector_syncs_status_rows_without_new_gallery_card():
    source = app_source()
    inspector_body = function_body(source, "renderGalleryInspector")
    lookup_body = function_body(source, "inventoryItemForGalleryAsset")
    gallery_status_body = function_body(source, "galleryStatusRows")
    status_rows_body = function_body(source, "inventoryStatusRows")
    render_status_body = function_body(source, "renderGalleryStatusRows")
    field_rows_body = function_body(source, "galleryStatusFieldRows")

    assert "galleryInspectorInventory" in source
    assert "galleryInspectorInventoryText" in source
    assert "galleryStatusRows(asset)" in inspector_body
    assert "renderGalleryStatusRows(asset)" in inspector_body
    assert "inventoryBox.hidden = !statusRows.length" in inspector_body
    assert "inventoryItemForGalleryAsset(asset)" in gallery_status_body
    assert "inventoryStatusRows(inventoryItemForGalleryAsset(asset))" in gallery_status_body
    assert "galleryStatusFieldRows(raw)" in gallery_status_body
    assert "galleryStatusFieldRows(raw.state)" in gallery_status_body
    assert "galleryStatusFieldRows(raw.payload)" in gallery_status_body
    assert 'asset.gallery_category !== "item"' in lookup_body
    assert "payload.item_id" in lookup_body
    assert "protocolInventoryRows()" in lookup_body
    assert "rows.find" in lookup_body
    assert "inventoryStatusRow" in render_status_body
    assert '"visible_description"' in field_rows_body
    assert '"unknowns"' in field_rows_body
    assert "来源物品" in status_rows_body


def test_inventory_state_display_uses_player_facing_labels_and_lines():
    source = app_source()
    raw_body = function_body(source, "protocolRawInventoryItem")
    rows_body = function_body(source, "inventoryKeyValueRows")
    labeled_rows_body = function_body(source, "inventoryLabeledRows")
    labels_body = function_body(source, "inventoryFieldLabel")

    assert 'detailParts.join("\\n")' in raw_body
    assert "inventoryLabeledRows(value)" in rows_body
    assert "inventoryFieldLabel(key)" in labeled_rows_body
    assert "当前状态" in labels_body
    assert "可见描述" in labels_body
    assert "未知信息" in labels_body
    assert '`${key}:' not in rows_body
    assert 'join(" | ")' not in raw_body


def test_inventory_empty_state_and_duplicate_titles_are_preserved():
    source = app_source()
    side_body = function_body(source, "renderSidePanel")
    raw_body = function_body(source, "protocolInventoryRows") + function_body(source, "protocolRawInventoryItem")

    assert "暂无物品" in side_body or "鏆傛棤鐗╁搧" in side_body
    assert 'state.ui.sideTab === "items" ? rows : rows.slice(-5)' in side_body
    assert ".map(protocolRawInventoryItem).filter(Boolean)" in raw_body
    assert "new Map" not in raw_body
    assert "byKey" not in raw_body


def test_canvas_items_use_declarative_canvas_spec_not_fixed_templates():
    source = app_source()
    draw_body = function_body(source, "drawCanvasItem")
    normalize_body = function_body(source, "normalizeItemCanvasSpec")
    custom_body = function_body(source, "drawCustomItemCanvas")
    cache_body = function_body(source, "assetContractPayload")
    reusable_body = function_body(source, "assetMetadataReusable")

    assert "normalizeItemCanvasSpec(asset, prompt)" in draw_body
    assert "hasCustomItemCanvasSpec(spec)" in draw_body
    assert "drawCustomItemCanvas(ctx, canvas.width, canvas.height, seed, spec)" in draw_body
    assert "silhouette" in normalize_body
    assert "materials" in normalize_body
    assert "state_effects" in normalize_body
    assert "palette" in normalize_body
    assert "drawCustomPendant" in custom_body
    assert "drawCustomRelicBox" in custom_body
    assert "drawCustomDevice" in custom_body
    assert "canvas_spec: metadata.canvas_spec" in cache_body
    assert "stableJson(requested.canvas_spec) === stableJson(existing.canvas_spec || {})" in reusable_body


def test_gallery_custom_canvas_protocol_excludes_character_and_cg():
    source = app_source()
    jobs_body = function_body(source, "processCanvasJobs")
    draw_body = function_body(source, "drawGalleryAsset")

    assert "isProtocolCanvasGalleryKind(job.kind)" in jobs_body
    assert "drawProtocolCanvasAsset(rawCanvas, asset)" in draw_body
    assert "asset.gallery_category === \"map\"" in draw_body
    assert "asset.gallery_category === \"item\"" in draw_body
    assert "asset.gallery_category === \"prop\"" in draw_body
    assert "asset.gallery_category === \"character\"" not in draw_body
    assert "asset.gallery_category === \"cg\"" not in draw_body


def test_map_asset_protocol_renderer_is_data_driven():
    source = app_source()
    protocol_body = function_body(source, "drawMapAssetProtocol")
    overlay_body = function_body(source, "drawMapProtocolOverlayFeature")

    assert "trpg.map_asset_protocol.v1" in source
    assert "layer.type === \"area\"" in protocol_body
    assert "layer.type === \"route\"" in protocol_body
    assert "layer.type === \"site\"" in protocol_body
    assert "layer.type === \"overlay\"" in protocol_body
    assert "feature.target_site" in overlay_body
    assert "feature.radius" in overlay_body


def test_canvas_portraits_keep_player_and_companion_out_of_gallery_and_customise_npcs():
    source = app_source()
    payload_body = function_body(source, "assetContractPayload")
    contract_role_body = function_body(source, "roleForCanvasAssetContract")
    portrait_body = function_body(source, "drawPixelActorPortrait")
    actor_spec_body = function_body(source, "normalizeActorCanvasSpec")
    custom_actor_body = function_body(source, "drawCustomActorPortraitToCanvas")

    assert "hiddenPortrait" in payload_body
    assert 'gallery_category: hiddenPortrait ? "hidden"' in payload_body
    assert 'display_zone: hiddenPortrait ? "hidden"' in payload_body
    assert "roleForCanvasAssetContract(kind, metadata)" in payload_body
    assert "text.includes(\"companion\")" in contract_role_body
    assert "text.includes(\"player\")" in contract_role_body
    assert "normalizeActorCanvasSpec" in portrait_body
    assert "hasCustomActorCanvasSpec(canvasSpec)" in portrait_body
    assert "drawCustomActorPortraitToCanvas(canvas, effectiveSeed, role, canvasSpec)" in portrait_body
    assert "features" in actor_spec_body
    assert "state_effects" in actor_spec_body
    assert "schema: String(raw.schema || \"actor_canvas_spec.v1\")" in actor_spec_body
    assert "drawIconBase" in custom_actor_body


def test_map_canvas_prefers_ascii_driven_renderer_over_fixed_room_template():
    source = app_source()
    semantic_body = function_body(source, "drawSemanticSceneMap")
    ascii_body = function_body(source, "drawAsciiDrivenMap")
    regions_body = function_body(source, "connectedAsciiRegions")
    walls_body = function_body(source, "drawAsciiWallCells")
    labels_body = function_body(source, "asciiLabelLookup")
    render_body = function_body(source, "renderCachedMap")
    raw_map_body = function_body(source, "isRawMapAsset")
    gallery_draw_body = function_body(source, "drawGalleryAsset")

    assert "Array.isArray(mapCanvas.ascii) && mapCanvas.ascii.length" in semantic_body
    assert "drawAsciiDrivenMap(ctx, w, h, seed, mapCanvas, palette)" in semantic_body
    assert "const hasCanvas = hasSemanticMapCanvas(mapCanvas)" in render_body
    assert "!isValidMapRoute(route) && !hasCanvas" in render_body
    assert 'category === "map"' in raw_map_body
    assert "asset.gallery_category === \"map\"" in gallery_draw_body
    assert "drawAsciiMapRegions" in ascii_body
    assert "drawAsciiMapMarkers" in ascii_body
    assert "connectedAsciiRegions(rows)" in function_body(source, "drawAsciiMapRegions")
    assert "rows[ny]?.[nx]" in regions_body
    assert "region.symbol === \"#\"" in function_body(source, "drawAsciiRegion")
    assert "roundRectPath(ctx, x + 0.5" in walls_body
    assert "mapCanvas.legend" in labels_body
