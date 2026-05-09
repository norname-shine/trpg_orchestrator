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
