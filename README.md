# 对外只读标签接口 · #3279

对应工单 **S2-TAX-020**。范围：小程序只读接口 `GET /api/public/taxonomy/{dict}`、
内部服务函数 `get_tags()` / `resolve()`、接口文档。标签写入与统计不在本单内。

## 1. 目录

```
public_taxonomy/service.py   仓储 + 三个对外函数（响应字段白名单在这里）
public_taxonomy/routes.py    FastAPI 适配层：登录态校验 + 缓存头
docs/API.md                  接口文档（请求/响应/错误码/函数签名）
tests/test_acceptance.py     12 个用例：字段白名单、别名解析、缓存头、HTTP 层
```

## 2. 三条验收怎么落地

| AC | 做法 | 为什么这样做 |
|---|---|---|
| 响应不含定义与统计 | 从**白名单**构造响应体（`PUBLIC_FIELDS = ("code","name")`），测试断言字段集合恰好等于 `{code,name}` | 黑名单靠纪律，白名单靠结构：以后加字段默认不出去 |
| resolve 能通过别名找到标准标签 | 先 code 精确命中，再在 **active** 标签的 aliases 里找；只在本字典内解析 | draft 标签的别名不应把调用方引到未生效的标签上；跨字典命中会把两个业务域串味 |
| 响应带 `Cache-Control: max-age=300` | 用例层直接返回 headers，只有 200 带 | 404 也带长缓存会把错误页钉在客户端 5 分钟 |

## 3. 运行与测试

```bash
python -m unittest discover -s tests -t . -v     # 零依赖：10 passed（HTTP 层跳过）
python -m pip install "fastapi" "httpx"          # 可选：12 passed（含 2 个 HTTP 用例）
```

## 4. 接口文档

见 `docs/API.md`：请求头、成功/错误响应体、两个服务函数的签名与语义。

## 5. 边界与取舍

- **只暴露 active**：`draft` / `pending_review` 不出现在任何对外响应里，避免小程序展示尚未审核的标签。
- **get_tags 静默略过未知 code**：渲染场景下，一个 code 失效不应让整页报错；需要严格校验的调用方用 `resolve` 判 `None`。
- **resolve 不做模糊匹配**：别名是精确匹配，不做拼音或前缀 —— 那是搜索服务的职责（S2-TAX-010），在这里做会把两个模块的语义搅在一起。
- **登录态用头桩**：本单不含 S3-MINI，鉴权替换点写在 `routes.py` 的 `require_member()`，README 与 API.md 都标了。

## 6. 不在本单范围

标签写入与合并（S2-TAX-002）、标签使用统计（S2-TAX-013）、拼音首字母匹配与搜索排序（S2-TAX-010）、
小程序页面本身（S3-MINI）。

## 7. 验收对照

| # | 验收原文 | 用例 | 实测 |
|---|---|---|---|
| 1 | 小程序接口响应中不包含定义与统计字段（测试断言） | `test_ac1_response_has_only_code_and_name` 等 4 个 | 每个标签字段集合 `== {code,name}`；draft 标签不出现；两个服务函数同样不含 definition/stats；未知字典 404 |
| 2 | resolve 能通过别名找到标准标签（测试通过） | `test_ac2_resolve_by_alias` 等 4 个 | 「林木」「forest」「农林」三个别名均命中；draft 标签的别名不命中；跨字典别名不串味 |
| 3 | 响应带 Cache-Control max-age=300 | `test_ac3_cache_control_max_age_300` 等 2 个 | 200 响应头 `max-age=300`；404 不带缓存头 |
