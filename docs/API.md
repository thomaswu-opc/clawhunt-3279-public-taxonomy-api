# 对外只读标签接口

## 1. 小程序端：`GET /api/public/taxonomy/{dict}`

只返回 `active` 标签，且**每个标签只有两个字段**：`code`、`name`。定义、统计、别名、层级、状态一律不返回。

**请求头**：`X-Member-Token: <会员登录态>`。缺失返回 `401 {"error":"MEMBER_TOKEN_REQUIRED"}`。
本单不实现 S3-MINI 的鉴权，用该头模拟；生产环境替换 `public_taxonomy/routes.py` 的 `require_member()`。

**成功响应**（`200`）：

```json
{
  "dict_code": "industry",
  "tags": [
    {"code": "A01", "name": "农业"},
    {"code": "A02", "name": "林业"}
  ]
}
```

**响应头**：`Cache-Control: max-age=300`（AC-3）。仅 200 带此头，404 不带 —— 避免把错误页缓存 5 分钟。

**错误**：

| 状态 | body | 场景 |
|---|---|---|
| 401 | `{"error":"MEMBER_TOKEN_REQUIRED"}` | 缺会员登录态 |
| 404 | `{"error":"DICT_NOT_FOUND","detail":"<dict>"}` | 字典不存在或无任何标签 |

## 2. 内部服务函数（同进程调用，不走 HTTP）

```python
from public_taxonomy.service import TagStore, get_tags, resolve

get_tags(store, "industry", ["A01", "A02"])   # -> [{"code","name"}, ...]，未知 code 静默略过
resolve(store, "industry", "林木")             # -> {"code":"A02","name":"林业"} 或 None
```

- `get_tags`：批量按 code 取，用于渲染场景，不因个别 code 缺失而报错。
- `resolve`：先按 code 精确命中，未中再在 **active** 标签的 `aliases` 里查（AC-2）。
  只在本字典内解析，不会串到别的字典；`draft` 标签的别名不参与解析。

两个函数的返回体同样只有 `code` 与 `name` —— 内部调用不构成泄露借口，白名单在 `service.py` 的
`SERVICE_FIELDS` 一处维护。

## 3. 为什么白名单而不是黑名单

"记得别把 definition 带出去"是纪律；"只从白名单构造响应"是结构。前者在有人加字段时会漏，
后者在有人加字段时默认不出去。测试 `test_ac1_response_has_only_code_and_name` 断言字段集合
**恰好等于** `{code, name}`，多一个就失败。

## 4. 运行与测试

```bash
python -m unittest discover -s tests -t . -v     # 12 passed（无 fastapi 时 10 passed，HTTP 层跳过）
python -m pip install fastapi httpx              # 可选：启用 HTTP 层用例
python -m uvicorn public_taxonomy.routes:create_app --factory --port 8000
```
