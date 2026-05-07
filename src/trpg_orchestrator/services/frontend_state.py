# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


def _web_server():
    from .. import web_server

    return web_server


def frontend_state_response(campaign_id: str = "") -> dict[str, Any]:
    return _web_server()._frontend_state_response_impl(campaign_id)


def campaign_state(campaign_id: str) -> dict[str, Any]:
    return _web_server()._campaign_state_impl(campaign_id)

