"""只读标签仓储 + 服务函数。

两个关键边界：
1. **小程序响应只能出现 code 与 name**（AC-1）。定义、统计、别名、层级一律不出去。
   实现上不是"记得别带上"，而是从白名单字段构造响应体 —— 字段集合本身由测试断言。
2. **resolve 要能通过别名命中标准标签**（AC-2），且 resolve 只在 active 里找；
   一个 draft 标签的别名不应把调用方引到尚未生效的标签上。
"""
from __future__ import annotations

from dataclasses import dataclass, field

ACTIVE = "active"
CACHE_HEADER = "max-age=300"


@dataclass
class Tag:
    code: str
    name: str
    dict_code: str
    status: str = ACTIVE
    definition: str = ""
    aliases: list[str] = field(default_factory=list)
    stats: dict | None = None


class TagStore:
    def __init__(self, tags: list[Tag]) -> None:
        self._tags = list(tags)

    def by_dict(self, dict_code: str) -> list[Tag]:
        return [t for t in self._tags if t.dict_code == dict_code]

    def active(self, dict_code: str) -> list[Tag]:
        return [t for t in self.by_dict(dict_code) if t.status == ACTIVE]

    def find(self, dict_code: str, code: str) -> Tag | None:
        for t in self.by_dict(dict_code):
            if t.code == code:
                return t
        return None


# 小程序响应允许的字段白名单 —— AC-1 的唯一实现点
PUBLIC_FIELDS = ("code", "name")
# 内部服务函数可返回的字段（可以多，但不得含 definition / stats）
SERVICE_FIELDS = ("code", "name")


def _project(tag: Tag, fields: tuple[str, ...]) -> dict:
    return {k: getattr(tag, k) for k in fields}


def public_tags(store: TagStore, dict_code: str) -> tuple[int, dict, dict]:
    """GET /api/public/taxonomy/{dict} 的用例层：返回 (status, body, headers)。"""
    if not store.by_dict(dict_code):
        return 404, {"error": "DICT_NOT_FOUND", "detail": dict_code}, {}
    rows = [_project(t, PUBLIC_FIELDS) for t in store.active(dict_code)]
    return 200, {"dict_code": dict_code, "tags": rows}, {"Cache-Control": CACHE_HEADER}


def get_tags(store: TagStore, dict_code: str, codes: list[str]) -> list[dict]:
    """按 code 批量取（内部服务用）。未知 code 直接略过，不抛错 —— 调用方多为渲染场景。"""
    want = set(codes)
    return [_project(t, SERVICE_FIELDS) for t in store.active(dict_code) if t.code in want]


def resolve(store: TagStore, dict_code: str, code_or_alias: str) -> dict | None:
    """先按 code 精确命中，再在 active 标签的 aliases 里找（AC-2）。"""
    hit = store.find(dict_code, code_or_alias)
    if hit and hit.status == ACTIVE:
        return _project(hit, SERVICE_FIELDS)
    for tag in store.active(dict_code):
        if code_or_alias in tag.aliases:
            return _project(tag, SERVICE_FIELDS)
    return None
