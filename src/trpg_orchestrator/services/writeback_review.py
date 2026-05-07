# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


def _web_server():
    from .. import web_server

    return web_server


def writeback_review_payload(campaign_id: str = "") -> dict[str, Any]:
    return _web_server()._writeback_review_payload_impl(campaign_id)


def audit_writeback_payload(campaign_id: str = "") -> dict[str, Any]:
    return _web_server()._audit_writeback_payload_impl(campaign_id)


def apply_writeback_payload(campaign_id: str = "") -> dict[str, Any]:
    return _web_server()._apply_writeback_payload_impl(campaign_id)
