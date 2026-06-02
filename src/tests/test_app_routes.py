import unittest

from src.app.main import app


class AppRoutesTestCase(unittest.TestCase):
    def test_expected_routes_are_registered(self):
        paths = {route.path for route in app.routes}

        self.assertIn("/health", paths)
        self.assertIn("/emails/ingest", paths)
        self.assertIn("/emails/list", paths)
        self.assertIn("/processing/process-next", paths)
        self.assertIn("/processing/process-all", paths)
        self.assertIn("/db/overview", paths)
        self.assertIn("/db/reset", paths)
        self.assertIn("/categories/list", paths)
        self.assertIn("/classification-results/list", paths)
        self.assertIn("/dashboard", paths)


if __name__ == "__main__":
    unittest.main()
