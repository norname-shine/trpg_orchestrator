from trpg_orchestrator.output_contract import filter_unauthorized_payloads


def test_filter_unauthorized_payloads_keeps_nested_map_canvas_without_scalar_text():
    output_requests = {
        "map": {"mode": "update_canvas"},
    }
    payloads = {
        "map_canvas": {
            "ascii": [
                "####",
                "#@?#",
                "####",
            ],
            "points": [],
            "routes": [],
            "hazards": [],
        }
    }

    filtered, warnings = filter_unauthorized_payloads(payloads, output_requests)

    assert filtered == payloads
    assert warnings == []
