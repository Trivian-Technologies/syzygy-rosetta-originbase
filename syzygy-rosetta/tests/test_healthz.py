import importlib
import unittest


class HealthzEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            app_module = importlib.import_module("app")
            from fastapi.testclient import TestClient
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"Skipping test due to missing dependency: {exc}")

        cls.client = TestClient(app_module.app)

    def test_healthz_returns_ok(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
