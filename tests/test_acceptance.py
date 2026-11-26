"""三条验收标准的机械验证。"""
from __future__ import annotations

import unittest

from public_taxonomy import service

FORBIDDEN = ("definition", "stats", "aliases", "status", "level", "parent_id")
HEADER = {"Cache-Control": "max-age=300"}


def store() -> service.TagStore:
    return service.TagStore([
        service.Tag("A01", "农业", "industry", definition="含种植与养殖", aliases=["农林"]),
        service.Tag("A02", "林业", "industry", definition="林木培育", aliases=["林木", "forest"]),
        service.Tag("A03", "待审标签", "industry", status="draft", aliases=["草稿别名"]),
        service.Tag("S01", "企业服务", "service", aliases=["企服"]),
    ])


class AC1NoDefinitionOrStats(unittest.TestCase):
    def test_ac1_response_has_only_code_and_name(self):
        status, body, headers = service.public_tags(store(), "industry")
        self.assertEqual(status, 200)
        self.assertTrue(body["tags"])
        for row in body["tags"]:
            self.assertEqual(set(row), {"code", "name"}, "小程序响应只能有 code 与 name")
            for bad in FORBIDDEN:
                self.assertNotIn(bad, row)

    def test_ac1_draft_tags_are_not_exposed(self):
        _, body, _ = service.public_tags(store(), "industry")
        self.assertEqual([r["code"] for r in body["tags"]], ["A01", "A02"])

    def test_ac1_service_functions_also_hide_definition_and_stats(self):
        s = store()
        for row in service.get_tags(s, "industry", ["A01"]):
            self.assertNotIn("definition", row)
            self.assertNotIn("stats", row)
        hit = service.resolve(s, "industry", "A01")
        self.assertEqual(set(hit), {"code", "name"})

    def test_ac1_unknown_dict_404(self):
        status, body, _ = service.public_tags(store(), "nope")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "DICT_NOT_FOUND")


class AC2ResolveByAlias(unittest.TestCase):
    def test_ac2_resolve_by_code(self):
        self.assertEqual(service.resolve(store(), "industry", "A02")["code"], "A02")

    def test_ac2_resolve_by_alias(self):
        for key in ("林木", "forest", "农林"):
            hit = service.resolve(store(), "industry", key)
            self.assertIsNotNone(hit, "别名 %s 应能解析" % key)
            self.assertIn(hit["code"], ("A01", "A02"))

    def test_ac2_alias_of_draft_tag_does_not_resolve(self):
        self.assertIsNone(service.resolve(store(), "industry", "草稿别名"))

    def test_ac2_unknown_returns_none_and_dict_is_scoped(self):
        self.assertIsNone(service.resolve(store(), "industry", "不存在"))
        # 企服 只在 service 字典里，industry 下不得命中 —— 防止跨字典串味
        self.assertIsNone(service.resolve(store(), "industry", "企服"))
        self.assertEqual(service.resolve(store(), "service", "企服")["code"], "S01")


class AC3CacheHeader(unittest.TestCase):
    def test_ac3_cache_control_max_age_300(self):
        _, _, headers = service.public_tags(store(), "industry")
        self.assertEqual(headers, HEADER)

    def test_ac3_cache_header_only_on_success(self):
        _, _, headers = service.public_tags(store(), "nope")
        self.assertEqual(headers, {}, "404 不应带长缓存头")


class HttpLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except Exception:  # noqa: BLE001
            raise unittest.SkipTest("需要 fastapi + httpx")
        cls.client_cls = TestClient

    def client(self):
        from public_taxonomy.routes import create_app
        return self.client_cls(create_app(store()))

    def test_http_requires_member_token(self):
        r = self.client().get("/api/public/taxonomy/industry")
        self.assertEqual(r.status_code, 401)

    def test_http_returns_cache_header(self):
        r = self.client().get("/api/public/taxonomy/industry",
                              headers={"X-Member-Token": "demo"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("cache-control"), "max-age=300")
        self.assertEqual(set(r.json()["tags"][0]), {"code", "name"})


if __name__ == "__main__":
    unittest.main(verbosity=2)