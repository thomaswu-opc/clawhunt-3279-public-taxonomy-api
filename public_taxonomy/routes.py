"""FastAPI 适配层：路由 + 登录态校验 + 缓存头。

小程序接口要求会员登录态：本单不实现 S3-MINI 的鉴权，用 `X-Member-Token` 头模拟，
缺失返回 401 —— 这是接口约定的一部分，写进 docs/API.md，替换点是 `require_member()`。
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from public_taxonomy import service


def require_member(request: Request) -> bool:
    return bool((request.headers.get("x-member-token") or "").strip())


def create_app(store: service.TagStore) -> FastAPI:
    app = FastAPI(title="public-taxonomy", version="1.0")
    app.state.store = store

    @app.get("/api/public/taxonomy/{dict_code}")
    async def list_public(dict_code: str, request: Request):
        if not require_member(request):
            return JSONResponse(status_code=401,
                                content={"error": "MEMBER_TOKEN_REQUIRED"})
        status, body, headers = service.public_tags(request.app.state.store, dict_code)
        return JSONResponse(status_code=status, content=body, headers=headers)

    return app
