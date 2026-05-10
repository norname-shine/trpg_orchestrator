# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any


def detect_capability_events(player_action: str, memory: dict) -> list[dict[str, str]]:
    """Detect event-shaped capability triggers from the player's action text."""
    text = _normalize(player_action)
    if not text:
        return []

    events: list[dict[str, str]] = []

    def add(event: str, capability: str, reason: str, confidence: str = "high") -> None:
        if not any(row.get("event") == event and row.get("capability") == capability for row in events):
            events.append({
                "event": event,
                "capability": capability,
                "reason": reason,
                "confidence": confidence,
            })

    if _has_any(text, ("不生图", "不要生图", "别生图", "不生成图", "不要生成图", "别生成图", "不要图片", "无需图片", "no image", "do not generate image", "don't generate image")):
        add("image_negated", "visual_assets", "player explicitly negated image generation")

    if _has_any(text, ("生图", "生成图", "画图", "图片", "立绘", "头像", "场景图", "怪物图", "generate image", "portrait")):
        add("image_requested", "visual_assets", "player action requests visual asset generation")

    if _has_any(text, ("检定", "骰子", "投骰", "判定", "d20", "dice", "roll", "check")):
        add("dice_requested", "dice_check_requested", "player action requests a dice check")

    if _has_any(text, ("捡起", "拾起", "拿起", "获得", "取得", "收下", "放入背包", "收入背包", "拿走", "得到", "pick up", "take the", "obtain", "gain")):
        add("item_obtained", "inventory", "player action implies item gained")

    if _has_any(text, ("丢弃", "丢掉", "遗失", "失去", "交出", "消耗", "用掉", "扔掉", "drop", "lose", "discard", "consume")):
        add("item_lost", "inventory", "player action implies item lost or consumed")

    if _has_any(text, ("检查", "查看", "观察", "研究", "鉴定", "识别", "inspect", "examine", "identify")) and _has_any(text, ("物品", "道具", "装备", "钥匙", "徽章", "戒指", "卷轴", "书", "瓶", "吊坠", "item", "badge", "key")):
        add("item_inspected", "inventory", "player action inspects an item")

    if _has_any(text, ("注意到", "发现", "看见", "看到", "察觉", "听见", "闻到", "线索", "痕迹", "符号", "血迹", "脚印", "文字", "纸条", "记录", "clue", "symbol", "trace", "footprint")):
        add("clue_observed", "gallery_assets", "player action implies a visible fact may need gallery_assets")

    if _has_any(text, ("进入", "前往", "走进", "走向", "沿着", "穿过", "离开", "抵达", "到达", "小路", "仓库", "房间", "门口", "街道", "森林", "港口", "入口", "go to", "enter", "arrive", "leave")):
        add("location_changed", "map", "player action implies location or route changed")

    if _has_any(text, ("npc", "人物", "守卫", "商人", "同伴", "敌人", "怪物", "出现", "在场", "对话", "交谈", "talk to", "speak with")):
        add("npc_present", "npc_present", "player action implies an NPC or actor is present")

    if _has_any(text, ("受伤", "流血", "中毒", "疲惫", "昏迷", "恢复", "治疗", "状态", "属性", "角色卡", "injured", "poisoned", "status")):
        add("status_changed", "character_card", "player action implies character status changed")

    if _has_explicit_request(text):
        add("explicit_request", "base_director", "player action contains an explicit request")

    return events


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle.lower() in text for needle in needles)


def _has_explicit_request(text: str) -> bool:
    return _has_any(text, ("查看", "显示", "打开", "生成", "给我", "帮我", "我要", "请", "show", "open", "generate"))
