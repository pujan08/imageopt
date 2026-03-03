"""
Tests for the Flask API route /api/weather.
Uses Flask test client + unittest.mock to avoid real HTTP calls.
Run with: pytest tests/test_routes.py -v
"""
import unittest
from unittest.mock import patch, MagicMock
from app import app


class TestWeatherRouteSuccess(unittest.TestCase):
    """Happy-path tests — valid airport code, mock METAR returned."""

    def setUp(self):
        self.client = app.test_client()

    def _mock_response(self, text, status_code=200):
        mock = MagicMock()
        mock.text = text
        mock.status_code = status_code
        mock.raise_for_status.return_value = None
        return mock

    @patch("app.requests.get")
    def test_valid_airport_returns_200(self, mock_get):
        mock_get.return_value = self._mock_response(
            "KLAX 031853Z 25012KT 10SM FEW025 SCT250 18/08 A2994"
        )
        response = self.client.get("/api/weather?airport=KLAX")
        self.assertEqual(response.status_code, 200)

    @patch("app.requests.get")
    def test_response_contains_airport(self, mock_get):
        mock_get.return_value = self._mock_response(
            "KLAX 031853Z 25012KT 10SM FEW025 SCT250 18/08 A2994"
        )
        data = self.client.get("/api/weather?airport=KLAX").get_json()
        self.assertEqual(data["airport"], "KLAX")

    @patch("app.requests.get")
    def test_response_contains_raw(self, mock_get):
        raw = "KLAX 031853Z 25012KT 10SM FEW025 SCT250 18/08 A2994"
        mock_get.return_value = self._mock_response(raw)
        data = self.client.get("/api/weather?airport=KLAX").get_json()
        self.assertEqual(data["raw"], raw)

    @patch("app.requests.get")
    def test_response_contains_summary(self, mock_get):
        mock_get.return_value = self._mock_response(
            "KLAX 031853Z 25012KT 10SM FEW025 SCT250 18/08 A2994"
        )
        data = self.client.get("/api/weather?airport=KLAX").get_json()
        self.assertIn("summary", data)
        self.assertIsInstance(data["summary"], str)

    @patch("app.requests.get")
    def test_decoded_wind_present(self, mock_get):
        mock_get.return_value = self._mock_response(
            "KLAX 031853Z 25012KT 10SM FEW025 18/08 A2994"
        )
        data = self.client.get("/api/weather?airport=KLAX").get_json()
        self.assertIn("wind", data["decoded"])
        self.assertIsNotNone(data["decoded"]["wind"])

    @patch("app.requests.get")
    def test_decoded_temperature_present(self, mock_get):
        mock_get.return_value = self._mock_response(
            "KLAX 031853Z 25012KT 10SM FEW025 18/08 A2994"
        )
        data = self.client.get("/api/weather?airport=KLAX").get_json()
        self.assertIn("temperature", data["decoded"])

    @patch("app.requests.get")
    def test_lowercase_airport_code_normalised(self, mock_get):
        mock_get.return_value = self._mock_response(
            "KLAX 031853Z 25012KT 10SM CLR 18/08 A2994"
        )
        data = self.client.get("/api/weather?airport=klax").get_json()
        self.assertEqual(data["airport"], "KLAX")

    @patch("app.requests.get")
    def test_uses_first_line_of_multi_line_response(self, mock_get):
        mock_get.return_value = self._mock_response(
            "KLAX 031853Z 25012KT 10SM CLR 18/08 A2994\nKLAX 031753Z 24010KT 10SM CLR 17/07 A2993"
        )
        data = self.client.get("/api/weather?airport=KLAX").get_json()
        self.assertIn("18:53 UTC", data["decoded"]["time"])


class TestWeatherRouteValidation(unittest.TestCase):
    """Input validation — bad or missing airport codes."""

    def setUp(self):
        self.client = app.test_client()

    def test_missing_airport_returns_400(self):
        response = self.client.get("/api/weather")
        self.assertEqual(response.status_code, 400)

    def test_empty_airport_returns_400(self):
        response = self.client.get("/api/weather?airport=")
        self.assertEqual(response.status_code, 400)

    def test_invalid_chars_returns_400(self):
        response = self.client.get("/api/weather?airport=K@LX")
        self.assertEqual(response.status_code, 400)

    def test_too_short_code_returns_400(self):
        response = self.client.get("/api/weather?airport=K")
        self.assertEqual(response.status_code, 400)

    def test_too_long_code_returns_400(self):
        response = self.client.get("/api/weather?airport=KLAXXX")
        self.assertEqual(response.status_code, 400)

    def test_error_message_in_body(self):
        data = self.client.get("/api/weather?airport=").get_json()
        self.assertIn("error", data)


class TestWeatherRouteErrors(unittest.TestCase):
    """Error handling — external API failures, empty responses, timeouts."""

    def setUp(self):
        self.client = app.test_client()

    @patch("app.requests.get")
    def test_empty_metar_response_returns_404(self, mock_get):
        mock = MagicMock()
        mock.text = ""
        mock.raise_for_status.return_value = None
        mock_get.return_value = mock
        response = self.client.get("/api/weather?airport=ZZZZ")
        self.assertEqual(response.status_code, 404)

    @patch("app.requests.get")
    def test_timeout_returns_504(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.Timeout
        response = self.client.get("/api/weather?airport=KLAX")
        self.assertEqual(response.status_code, 504)

    @patch("app.requests.get")
    def test_connection_error_returns_502(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        response = self.client.get("/api/weather?airport=KLAX")
        self.assertEqual(response.status_code, 502)

    @patch("app.requests.get")
    def test_error_response_has_error_key(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.Timeout
        data = self.client.get("/api/weather?airport=KLAX").get_json()
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
