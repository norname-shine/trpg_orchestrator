from trpg_orchestrator.canvas_job_resolver import canvas_jobs_from_payloads


def test_map_canvas_render_token_triggers_canvas_job():
    jobs = canvas_jobs_from_payloads(
        {
            "output_requests": {
                "map": {"mode": "update_canvas", "trigger": "user_requested", "reason": "map"},
                "canvas_jobs": {"mode": "none", "trigger": "none", "reason": ""},
            },
            "payloads": {
                "map_canvas": {
                    "render_token": "map_canvas.v1",
                    "ascii": ["@..", ".#.", "..?"],
                    "legend": {"@": "当前位置", "#": "阻隔", "?": "未知"},
                }
            },
        },
        "demo",
        "seed",
    )

    assert jobs == [
        {
            "job_id": "map_current_area",
            "kind": "map",
            "renderer": "pixel_map",
            "trigger": "director_triggered",
            "input_ref": "payloads.map_canvas",
            "asset_key": "map:current_area",
            "cache_policy": "stable",
            "campaign_id": "demo",
            "asset_seed": "seed",
        }
    ]


def test_map_asset_protocol_triggers_canvas_job():
    jobs = canvas_jobs_from_payloads(
        {
            "output_requests": {
                "map": {"mode": "update_canvas", "trigger": "user_requested", "reason": "map"},
                "canvas_jobs": {"mode": "none", "trigger": "none", "reason": ""},
            },
            "payloads": {
                "map_canvas": {
                    "schema": "trpg.map_asset_protocol.v1",
                    "id": "reactor_ring",
                    "title": "Reactor Ring",
                    "scale": "facility",
                    "palette": {"paper": "#eee", "land": "#999", "water": "#59a", "danger": "#c44", "route": "#333", "ink": "#111", "glow": "#6ef"},
                    "layers": [
                        {"id": "terrain", "type": "area", "features": [{"id": "deck", "shape": "ellipse", "center": [0.5, 0.5], "size": [0.6, 0.4], "style": "metal"}]},
                        {"id": "routes", "type": "route", "features": [{"id": "corridor", "points": [[0.2, 0.8], [0.8, 0.2]], "style": "main"}]},
                        {"id": "sites", "type": "site", "features": [{"id": "core", "center": [0.5, 0.5], "kind": "objective", "label": "Core"}]},
                        {"id": "state", "type": "overlay", "features": [{"id": "glow", "shape": "pulse", "target_site": "core", "radius": 0.1, "intensity": 0.5}]},
                    ],
                }
            },
        },
        "demo",
        "seed",
    )

    assert jobs == [
        {
            "job_id": "map_current_area",
            "kind": "map",
            "renderer": "map_asset_protocol",
            "trigger": "director_triggered",
            "input_ref": "payloads.map_canvas",
            "asset_key": "map:current_area",
            "cache_policy": "stable",
            "campaign_id": "demo",
            "asset_seed": "seed",
        }
    ]
