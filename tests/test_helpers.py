"""
Unit tests for individual helper and decoder functions in app.py.
Run with: pytest tests/test_helpers.py -v
"""
import unittest
from app import (
    degrees_to_compass,
    celsius_to_fahrenheit,
    knots_to_mph,
    parse_temp,
    decode_wx_code,
    decode_sky,
)


class TestDegreesToCompass(unittest.TestCase):
    """degrees_to_compass() — converts wind direction degrees to a label."""

    def test_north(self):
        self.assertEqual(degrees_to_compass(0), "North")

    def test_north_360(self):
        self.assertEqual(degrees_to_compass(360), "North")

    def test_northeast(self):
        self.assertEqual(degrees_to_compass(45), "Northeast")

    def test_east(self):
        self.assertEqual(degrees_to_compass(90), "East")

    def test_southeast(self):
        self.assertEqual(degrees_to_compass(135), "Southeast")

    def test_south(self):
        self.assertEqual(degrees_to_compass(180), "South")

    def test_southwest(self):
        self.assertEqual(degrees_to_compass(225), "Southwest")

    def test_west(self):
        self.assertEqual(degrees_to_compass(270), "West")

    def test_northwest(self):
        self.assertEqual(degrees_to_compass(315), "Northwest")

    def test_north_northeast(self):
        self.assertEqual(degrees_to_compass(22), "North-Northeast")

    def test_east_northeast(self):
        self.assertEqual(degrees_to_compass(67), "East-Northeast")


class TestCelsiusToFahrenheit(unittest.TestCase):
    """celsius_to_fahrenheit() — standard C→F conversion."""

    def test_freezing_point(self):
        self.assertEqual(celsius_to_fahrenheit(0), 32)

    def test_boiling_point(self):
        self.assertEqual(celsius_to_fahrenheit(100), 212)

    def test_body_temperature(self):
        self.assertEqual(celsius_to_fahrenheit(37), 99)

    def test_negative_temp(self):
        self.assertEqual(celsius_to_fahrenheit(-10), 14)

    def test_same_value(self):
        # -40°C == -40°F
        self.assertEqual(celsius_to_fahrenheit(-40), -40)


class TestKnotsToMph(unittest.TestCase):
    """knots_to_mph() — wind speed conversion."""

    def test_calm(self):
        self.assertEqual(knots_to_mph(0), 0)

    def test_ten_knots(self):
        self.assertEqual(knots_to_mph(10), 12)

    def test_fifty_knots(self):
        self.assertEqual(knots_to_mph(50), 58)

    def test_hurricane_force(self):
        # 64 knots = minimum hurricane, should be ~74 mph
        self.assertGreaterEqual(knots_to_mph(64), 73)


class TestParseTemp(unittest.TestCase):
    """parse_temp() — handles both positive and METAR negative (M-prefix) temps."""

    def test_positive(self):
        self.assertEqual(parse_temp("12"), 12)

    def test_zero(self):
        self.assertEqual(parse_temp("00"), 0)

    def test_negative_prefix(self):
        # METAR uses 'M' to denote below-zero
        self.assertEqual(parse_temp("M03"), -3)

    def test_negative_double_digit(self):
        self.assertEqual(parse_temp("M15"), -15)


class TestDecodeWxCode(unittest.TestCase):
    """decode_wx_code() — converts raw weather codes to plain English."""

    def test_light_rain(self):
        self.assertIn("light", decode_wx_code("-RA"))
        self.assertIn("rain", decode_wx_code("-RA"))

    def test_heavy_rain(self):
        self.assertIn("heavy", decode_wx_code("+RA"))

    def test_thunderstorm_rain(self):
        result = decode_wx_code("TSRA")
        self.assertIn("thunderstorm", result)
        self.assertIn("rain", result)

    def test_light_thunderstorm_rain(self):
        result = decode_wx_code("-TSRA")
        self.assertIn("light", result)
        self.assertIn("thunderstorm", result)
        self.assertIn("rain", result)

    def test_snow(self):
        self.assertIn("snow", decode_wx_code("SN"))

    def test_fog(self):
        self.assertIn("fog", decode_wx_code("FG"))

    def test_mist(self):
        self.assertIn("mist", decode_wx_code("BR"))

    def test_haze(self):
        self.assertIn("haze", decode_wx_code("HZ"))

    def test_freezing_rain(self):
        result = decode_wx_code("FZRA")
        self.assertIn("freezing", result)
        self.assertIn("rain", result)

    def test_nearby_shower(self):
        result = decode_wx_code("VCSH")
        self.assertIn("nearby", result)
        self.assertIn("shower", result)

    def test_heavy_snow(self):
        result = decode_wx_code("+SN")
        self.assertIn("heavy", result)
        self.assertIn("snow", result)


class TestDecodeSky(unittest.TestCase):
    """decode_sky() — converts sky condition tuples to readable descriptions."""

    def test_clear_skies(self):
        self.assertEqual(decode_sky([("CLEAR", 0, None)]), "Clear skies")

    def test_empty_returns_none(self):
        self.assertIsNone(decode_sky([]))

    def test_few_clouds(self):
        result = decode_sky([("FEW", 2500, None)])
        self.assertIn("few", result.lower())
        self.assertIn("2,500 ft", result)

    def test_scattered_clouds(self):
        result = decode_sky([("SCT", 5000, None)])
        self.assertIn("scattered", result.lower())
        self.assertIn("5,000 ft", result)

    def test_broken_clouds(self):
        result = decode_sky([("BKN", 4000, None)])
        self.assertIn("mostly cloudy", result.lower())

    def test_overcast(self):
        result = decode_sky([("OVC", 1000, None)])
        self.assertIn("overcast", result.lower())

    def test_cumulonimbus(self):
        result = decode_sky([("BKN", 4000, "CB")])
        self.assertIn("cumulonimbus", result.lower())

    def test_towering_cumulus(self):
        result = decode_sky([("FEW", 3000, "TCU")])
        self.assertIn("towering cumulus", result.lower())

    def test_multiple_layers(self):
        result = decode_sky([("FEW", 2500, None), ("SCT", 8000, None)])
        self.assertIn("2,500 ft", result)
        self.assertIn("8,000 ft", result)


if __name__ == "__main__":
    unittest.main()
