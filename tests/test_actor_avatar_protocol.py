import json

from trpg_orchestrator import web_server


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def make_campaign(tmp_path, monkeypatch, campaign_id="actor_protocol_demo", companion_name="Buddy"):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", root)
    campaign = root / campaign_id
    write_json(campaign / "campaign_profile.json", {"title": "Demo", "asset_seed": "seed123", "template": "custom"})
    write_json(
        campaign / "character_prompt.json",
        {
            "character_card": {
                "identity": {"name": "Player One", "companion": companion_name},
                "companion": {"name": companion_name, "kind": "familiar", "archetype": "spirit", "species": "wisp"},
            }
        },
    )
    write_json(campaign / "recent_context.json", {"current_scene": {"active_npcs": ["Archivist"]}})
    return campaign_id, campaign


def test_old_manifest_companion_npc_is_strongly_migrated(tmp_path, monkeypatch):
    campaign_id, campaign = make_campaign(tmp_path, monkeypatch)
    key = f"{campaign_id}:seed123:npc_portrait:buddy:default:v17"
    write_json(
        campaign / "assets" / "manifest.json",
        {
            "campaign_id": campaign_id,
            "asset_seed": "seed123",
            "assets": {
                key: {
                    "key": key,
                    "kind": "npc_portrait",
                    "path": "assets/portraits/buddy.png",
                    "metadata": {
                        "role": "npc",
                        "runtime_role": "npc",
                        "gallery_category": "servant",
                        "visible_in_gallery": True,
                        "entity_key": "npc:buddy",
                        "display_name": "Buddy",
                    },
                }
            },
        },
    )

    manifest = web_server.load_asset_manifest(campaign_id)
    migrated = manifest["assets"][key]
    metadata = migrated["metadata"]

    assert migrated["kind"] == "companion_portrait"
    assert metadata["role"] == "companion"
    assert metadata["runtime_role"] == "companion"
    assert metadata["companion_type"] == "familiar"
    assert metadata["gallery_category"] == "hidden"
    assert metadata["visible_in_gallery"] is False
    assert metadata["not_in_gallery_filters"] is True
    assert metadata["entity_key"] == "companion:buddy"
    assert metadata["display_slot"] == "companion_card"
    assert metadata["detail_slot"] == "companion_detail"
    assert "actor_role_corrected_to_companion" in migrated["migration_notes"]
    assert "portrait_kind_corrected_to_companion_portrait" in migrated["migration_notes"]


def test_gallery_excludes_current_companion_but_keeps_npc(tmp_path, monkeypatch):
    campaign_id, campaign = make_campaign(tmp_path, monkeypatch)
    companion_key = f"{campaign_id}:seed123:npc_portrait:buddy:default:v17"
    npc_key = f"{campaign_id}:seed123:npc_portrait:archivist:default:v17"
    write_json(
        campaign / "assets" / "manifest.json",
        {
            "campaign_id": campaign_id,
            "asset_seed": "seed123",
            "assets": {
                companion_key: {
                    "key": companion_key,
                    "kind": "npc_portrait",
                    "path": "assets/portraits/buddy.png",
                    "metadata": {"role": "npc", "entity_key": "npc:buddy", "display_name": "Buddy", "visible_in_gallery": True, "gallery_category": "npc"},
                },
                npc_key: {
                    "key": npc_key,
                    "kind": "npc_portrait",
                    "path": "assets/portraits/archivist.png",
                    "metadata": {"role": "npc", "entity_key": "npc:archivist", "display_name": "Archivist", "visible_in_gallery": True, "gallery_category": "npc"},
                },
            },
        },
    )

    state = web_server.campaign_state(campaign_id)
    assets = web_server.asset_list(campaign_id)["assets"]
    gallery = web_server.frontend_gallery(campaign_id, state, {"parsed": {}, "pressure_pack": {}}, assets)

    assert "companion" not in {row["key"] for row in gallery["filters"]}
    assert all(row.get("entity_key") != "companion:buddy" for row in gallery["assets"])
    assert any(row.get("entity_key") == "npc:archivist" for row in gallery["assets"])


def test_select_best_avatar_prefers_vcg_for_exact_entity_only():
    assets = [
        {"key": "c:seed:companion_portrait:buddy:default:v17", "kind": "companion_portrait", "generator_version": 17, "url": "/a.png", "metadata": {"entity_key": "companion:buddy", "portrait_asset_kind": "companion_portrait"}},
        {"key": "c:seed:companion_portrait:buddy:default:VCG", "kind": "companion_portrait", "generator_version": 17, "url": "/vcg.png", "metadata": {"entity_key": "companion:buddy", "portrait_asset_kind": "companion_portrait", "source": "cg_feedback"}},
        {"key": "c:seed:npc_portrait:buddy:default:VCG", "kind": "npc_portrait", "generator_version": 17, "url": "/npc-vcg.png", "metadata": {"entity_key": "npc:buddy", "portrait_asset_kind": "npc_portrait", "source": "cg_feedback"}},
    ]

    companion = web_server.select_best_avatar_asset("companion:buddy", "companion_portrait", assets)
    npc = web_server.select_best_avatar_asset("npc:buddy", "npc_portrait", assets)

    assert companion["key"].endswith(":VCG")
    assert companion["url"] == "/vcg.png"
    assert npc["url"] == "/npc-vcg.png"


def test_player_vcg_is_selected_and_hidden_from_gallery(tmp_path, monkeypatch):
    campaign_id, _campaign = make_campaign(tmp_path, monkeypatch)
    state = web_server.campaign_state(campaign_id)
    assets = [
        {"campaign_id": campaign_id, "key": "player-current", "kind": "player_portrait", "url": "/player-current.png", "exists": True, "generator_version": 17, "metadata": {"entity_key": "player:playerone", "portrait_asset_kind": "player_portrait", "visible_in_gallery": False}},
        {"campaign_id": campaign_id, "key": "player-vcg", "kind": "player_portrait", "url": "/player-vcg.png", "exists": True, "generator_version": 17, "metadata": {"entity_key": "player:playerone", "portrait_asset_kind": "player_portrait", "source": "vcg", "visible_in_gallery": False}},
    ]

    registry = web_server.build_visual_registry(campaign_id, state, assets)

    assert registry["avatar_index"]["player:playerone"]["selected_avatar_key"] == "player-vcg"
    assert registry["avatar_index"]["player:playerone"]["visible_in_gallery"] is False


def test_plain_npc_is_not_misclassified_as_companion(tmp_path, monkeypatch):
    campaign_id, campaign = make_campaign(tmp_path, monkeypatch)
    npc_key = f"{campaign_id}:seed123:npc_portrait:merchant:default:v17"
    write_json(
        campaign / "assets" / "manifest.json",
        {
            "campaign_id": campaign_id,
            "asset_seed": "seed123",
            "assets": {
                npc_key: {
                    "key": npc_key,
                    "kind": "npc_portrait",
                    "path": "assets/portraits/merchant.png",
                    "metadata": {"role": "npc", "entity_key": "npc:merchant", "display_name": "Merchant", "visible_in_gallery": True, "gallery_category": "npc"},
                }
            },
        },
    )

    manifest = web_server.load_asset_manifest(campaign_id)
    metadata = manifest["assets"][npc_key]["metadata"]

    assert manifest["assets"][npc_key]["kind"] == "npc_portrait"
    assert metadata["runtime_role"] == "npc"
    assert metadata["gallery_category"] == "npc"
    assert metadata["visible_in_gallery"] is True


def test_same_name_assets_do_not_cross_campaign(tmp_path, monkeypatch):
    cid_a, _ = make_campaign(tmp_path, monkeypatch, campaign_id="campaign_a")
    cid_b, _ = make_campaign(tmp_path, monkeypatch, campaign_id="campaign_b")
    assets_a = [{"campaign_id": cid_a, "key": "a-vcg", "kind": "companion_portrait", "url": "/a.png", "exists": True, "generator_version": 17, "metadata": {"entity_key": "companion:buddy", "portrait_asset_kind": "companion_portrait", "source": "vcg"}}]
    assets_b = [{"campaign_id": cid_b, "key": "b-current", "kind": "companion_portrait", "url": "/b.png", "exists": True, "generator_version": 17, "metadata": {"entity_key": "companion:buddy", "portrait_asset_kind": "companion_portrait"}}]

    reg_a = web_server.build_visual_registry(cid_a, web_server.campaign_state(cid_a), assets_a)
    reg_b = web_server.build_visual_registry(cid_b, web_server.campaign_state(cid_b), assets_b)

    assert reg_a["avatar_index"]["companion:buddy"]["selected_avatar_key"] == "a-vcg"
    assert reg_b["avatar_index"]["companion:buddy"]["selected_avatar_key"] == "b-current"


def test_companion_visual_profile_known_preset_keeps_raw_type():
    profile = web_server.build_companion_visual_profile(
        {"name": "Mimi", "kind": "palico scout", "species": "felyne", "personality": "brave, playful", "equipment": ["goggles"]},
        {"template": "custom"},
        {},
        {},
    )

    assert profile["companion_type_raw"] == "palico scout"
    assert profile["companion_type_preset"] == "palico"
    assert "do_not_reuse_player_face_template" in profile["avoid"]
    assert any("cat" in row or "feline" in row for row in profile["face_rules"] + profile["body_structure"])


def test_companion_visual_profile_unknown_type_is_custom_not_npc():
    profile = web_server.build_companion_visual_profile(
        {"name": "Umbra", "kind": "living thunder umbrella", "personality": "solemn", "equipment": "bronze bells"},
        {"template": "custom"},
        {},
        {},
    )

    assert profile["companion_type_raw"] == "living thunder umbrella"
    assert profile["companion_type_preset"] == "custom"
    assert profile["certainty"] == "confirmed"
    assert "do_not_reuse_player_face_template" in profile["avoid"]
    assert "npc" not in profile["companion_type_preset"]


def test_gallery_taxonomy_core_and_campaign_categories_from_profile(tmp_path, monkeypatch):
    campaign_id, campaign = make_campaign(tmp_path, monkeypatch)
    write_json(
        campaign / "campaign_profile.json",
        {
            "title": "Demo",
            "asset_seed": "seed123",
            "template": "custom",
            "gallery_categories": [{"id": "faction", "label": "Faction"}],
        },
    )

    taxonomy = web_server.gallery_taxonomy_for_campaign(campaign_id, web_server.campaign_state(campaign_id))
    filters = web_server.gallery_filters_from_taxonomy(taxonomy)

    core_ids = {row["id"] for row in taxonomy["core_categories"]}
    campaign_ids = {row["id"] for row in taxonomy["campaign_categories"]}
    assert {"cg", "npc", "scene", "item"}.issubset(core_ids)
    assert "faction" in campaign_ids
    assert "companion" not in {row["key"] for row in filters}


def test_gallery_taxonomy_does_not_create_filter_from_unknown_manifest_category(tmp_path, monkeypatch):
    campaign_id, campaign = make_campaign(tmp_path, monkeypatch)
    asset_key = f"{campaign_id}:seed123:npc_portrait:stranger:default:v17"
    write_json(
        campaign / "assets" / "manifest.json",
        {
            "campaign_id": campaign_id,
            "asset_seed": "seed123",
            "assets": {
                asset_key: {
                    "key": asset_key,
                    "kind": "npc_portrait",
                    "path": "assets/portraits/stranger.png",
                    "metadata": {"role": "npc", "entity_key": "npc:stranger", "display_name": "Stranger", "visible_in_gallery": True, "gallery_category": "unregistered_bucket"},
                }
            },
        },
    )

    state = web_server.campaign_state(campaign_id)
    assets = web_server.asset_list(campaign_id)["assets"]
    gallery = web_server.frontend_gallery(campaign_id, state, {"parsed": {}, "pressure_pack": {}}, assets)

    assert "unregistered_bucket" not in {row["key"] for row in gallery["filters"]}
    assert all(row.get("gallery_category") != "unregistered_bucket" for row in gallery["assets"])


def test_gallery_campaign_category_shows_normal_entity_not_companion(tmp_path, monkeypatch):
    campaign_id, campaign = make_campaign(tmp_path, monkeypatch, companion_name="Faction")
    write_json(
        campaign / "campaign_profile.json",
        {"title": "Demo", "asset_seed": "seed123", "template": "custom", "gallery_categories": [{"id": "faction", "label": "Faction"}]},
    )
    companion_key = f"{campaign_id}:seed123:npc_portrait:faction:default:v17"
    npc_key = f"{campaign_id}:seed123:npc_portrait:order:default:v17"
    write_json(
        campaign / "assets" / "manifest.json",
        {
            "campaign_id": campaign_id,
            "asset_seed": "seed123",
            "assets": {
                companion_key: {
                    "key": companion_key,
                    "kind": "npc_portrait",
                    "path": "assets/portraits/faction.png",
                    "metadata": {"role": "npc", "entity_key": "npc:faction", "display_name": "Faction", "visible_in_gallery": True, "gallery_category": "faction"},
                },
                npc_key: {
                    "key": npc_key,
                    "kind": "npc_portrait",
                    "path": "assets/portraits/order.png",
                    "metadata": {"role": "npc", "entity_key": "npc:order", "display_name": "Order", "visible_in_gallery": True, "gallery_category": "faction"},
                },
            },
        },
    )

    state = web_server.campaign_state(campaign_id)
    assets = web_server.asset_list(campaign_id)["assets"]
    gallery = web_server.frontend_gallery(campaign_id, state, {"parsed": {}, "pressure_pack": {}}, assets)

    assert "faction" in {row["key"] for row in gallery["filters"]}
    assert all(row.get("entity_key") != "companion:faction" for row in gallery["assets"])
    assert any(row.get("entity_key") == "npc:order" and row.get("gallery_category") == "faction" for row in gallery["assets"])


def test_visual_registry_uses_same_selected_avatar_for_companion(tmp_path, monkeypatch):
    campaign_id, _campaign = make_campaign(tmp_path, monkeypatch)
    state = web_server.campaign_state(campaign_id)
    assets = [
        {"campaign_id": campaign_id, "key": "current", "kind": "companion_portrait", "url": "/current.png", "exists": True, "generator_version": 17, "metadata": {"entity_key": "companion:buddy", "portrait_asset_kind": "companion_portrait"}},
        {"campaign_id": campaign_id, "key": "vcg", "kind": "companion_portrait", "url": "/vcg.png", "exists": True, "generator_version": 17, "metadata": {"entity_key": "companion:buddy", "portrait_asset_kind": "companion_portrait", "source": "formal_cg_crop"}},
    ]

    registry = web_server.build_visual_registry(campaign_id, state, assets)

    row = registry["avatar_index"]["companion:buddy"]
    assert row["selected_avatar_key"] == "vcg"
    assert row["selected_avatar_url"] == "/vcg.png"
    assert row["visible_in_gallery"] is False
    assert row["gallery_category"] == "hidden"
