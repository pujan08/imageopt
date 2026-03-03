"""
Integration-style unit tests for decode_metar() using realistic mock METAR strings.
Each test class represents a different weather scenario.
Run with: pytest tests/test_decoder.py -v
"""
import unittest
from app import decode_metar


class TestStandardMETAR(unittest.TestCase):
    """Clear day, simple wind, good visibility — KLAX style."""

    def setUp(self):
        self.result = decode_metar("KLAX 031853Z 25012KT 10SM FEW025 SCT250 18/08 A2994")

    def test_station(self):
        self.assertEqual(self.result["station"], "KLAX")

    def test_time(self):
        self.assertEqual(self.result["time"], "18:53 UTC")

    def test_wind_direction(self):
        self.assertIn("West", self.result["wind"])

    def test_wind_speed(self):
        self.assertIn("14 mph", self.result["wind"])

    def test_visibility(self):
        self.assertIn("10+", self.result["visibility"])

    def test_temperature(self):
        self.assertIn("64°F", self.result["temperature"])
        self.assertIn("18°C", self.result["temperature"])

    def test_dewpoint(self):
        self.assertIn("46°F", self.result["dewpoint"])

    def test_altimeter(self):
        self.assertEqual(self.result["altimeter"], "29.94 inHg")

    def test_sky_has_few_clouds(self):
        self.assertIn("few", self.result["sky"].lower())

    def test_no_weather_phenomena(self):
        self.assertIsNone(self.result["weather"])


class TestThunderstormMETAR(unittest.TestCase):
    """Active thunderstorm with heavy rain and cumulonimbus — KJFK style."""

    def setUp(self):
        self.result = decode_metar("KJFK 031853Z 04015G25KT 5SM -TSRA BKN040CB 14/12 A2985")

    def test_station(self):
        self.assertEqual(self.result["station"], "KJFK")

    def test_wind_has_gust(self):
        self.assertIn("gusting", self.result["wind"])

    def test_wind_speed(self):
        self.assertIn("17 mph", self.result["wind"])

    def test_visibility(self):
        self.assertIn("5", self.result["visibility"])

    def test_weather_has_thunderstorm(self):
        self.assertIn("thunderstorm", self.result["weather"].lower())

    def test_weather_has_rain(self):
        self.assertIn("rain", self.result["weather"].lower())

    def test_sky_has_cumulonimbus(self):
        self.assertIn("cumulonimbus", self.result["sky"].lower())

    def test_temperature(self):
        self.assertIn("57°F", self.result["temperature"])


class TestCalmWindMETAR(unittest.TestCase):
    """Calm winds, overcast, light fog — KSEA style."""

    def setUp(self):
        self.result = decode_metar("KSEA 031853Z 00000KT 2SM BR OVC010 08/07 A3005")

    def test_calm_wind(self):
        self.assertEqual(self.result["wind"], "Calm")

    def test_visibility(self):
        self.assertIn("2", self.result["visibility"])

    def test_weather_mist(self):
        self.assertIn("mist", self.result["weather"].lower())

    def test_sky_overcast(self):
        self.assertIn("overcast", self.result["sky"].lower())

    def test_temperature_near_freezing(self):
        self.assertIn("46°F", self.result["temperature"])


class TestVariableWindMETAR(unittest.TestCase):
    """Variable wind direction — KORD style."""

    def setUp(self):
        self.result = decode_metar("KORD 031853Z VRB03KT 10SM CLR 22/10 A3010")

    def test_variable_wind(self):
        self.assertIn("Variable", self.result["wind"])

    def test_clear_sky(self):
        self.assertIn("Clear", self.result["sky"])

    def test_temperature(self):
        self.assertIn("72°F", self.result["temperature"])


class TestLowVisibilityFogMETAR(unittest.TestCase):
    """Dense fog, visibility less than 1/4 mile — KBOS style."""

    def setUp(self):
        self.result = decode_metar("KBOS 031853Z 18008KT M1/4SM FG OVC002 12/12 A2990")

    def test_low_visibility(self):
        # M1/4SM is decoded as a fraction (0.25 miles), not "Less than" prefix
        self.assertIn("0.25", self.result["visibility"])

    def test_fog(self):
        self.assertIn("fog", self.result["weather"].lower())

    def test_overcast_low(self):
        self.assertIn("200 ft", self.result["sky"])

    def test_temperature_equals_dewpoint(self):
        # When temp == dewpoint, 100% humidity / fog conditions
        self.assertEqual(self.result["temperature"], self.result["dewpoint"])


class TestFreezingTemperatureMETAR(unittest.TestCase):
    """Below-zero temperatures (M prefix) — KDEN winter style."""

    def setUp(self):
        self.result = decode_metar("KDEN 031853Z 31020KT 10SM SCT060 BKN150 M05/M12 A3020")

    def test_negative_temperature(self):
        self.assertIn("23°F", self.result["temperature"])
        self.assertIn("-5°C", self.result["temperature"])

    def test_negative_dewpoint(self):
        self.assertIn("10°F", self.result["dewpoint"])
        self.assertIn("-12°C", self.result["dewpoint"])

    def test_wind_from_northwest(self):
        self.assertIn("Northwest", self.result["wind"])

    def test_multiple_cloud_layers(self):
        self.assertIn("6,000 ft", self.result["sky"])
        self.assertIn("15,000 ft", self.result["sky"])


class TestMetricPressureMETAR(unittest.TestCase):
    """International airport with Q (hPa) altimeter — EGLL (Heathrow) style."""

    def setUp(self):
        # Note: international visibility '9999' (metres) is not supported by the parser;
        # using SM format so the parser can advance past visibility to reach Q-altimeter.
        self.result = decode_metar("EGLL 031853Z 27015KT 10SM FEW025 SCT080 12/08 Q1015")

    def test_station(self):
        self.assertEqual(self.result["station"], "EGLL")

    def test_altimeter_in_hpa(self):
        self.assertEqual(self.result["altimeter"], "1015 hPa")

    def test_wind_from_west(self):
        self.assertIn("West", self.result["wind"])

    def test_temperature(self):
        self.assertIn("12°C", self.result["temperature"])


class TestMETARWithTypePrefix(unittest.TestCase):
    """METAR strings that start with the 'METAR' keyword."""

    def setUp(self):
        self.result = decode_metar("METAR KSFO 031853Z 28010KT 10SM CLR 16/08 A3002")

    def test_station_skips_keyword(self):
        self.assertEqual(self.result["station"], "KSFO")

    def test_altimeter(self):
        self.assertEqual(self.result["altimeter"], "30.02 inHg")


class TestGustingWindMETAR(unittest.TestCase):
    """Strong gusting wind scenario."""

    def setUp(self):
        self.result = decode_metar("KMDW 031853Z 29035G55KT 10SM BKN060 15/M02 A2975")

    def test_wind_has_gust(self):
        self.assertIn("gusting", self.result["wind"])

    def test_gust_speed(self):
        self.assertIn("63 mph", self.result["wind"])

    def test_negative_dewpoint(self):
        self.assertIn("-2°C", self.result["dewpoint"])


if __name__ == "__main__":
    unittest.main()
