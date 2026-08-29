from glm50c.lang import LANGUAGES, de, en, get_language

PUBLIC_API = ["NAME", "DEFAULT_VOICE", "MODES", "UI", "distance_text",
              "area_text", "volume_text", "mode_speech", "error_speech",
              "partial_speech", "area_result_speech", "volume_result_speech",
              "result_speech", "connected_speech"]


def test_number_word():
    assert en.number_word(0) == "zero"
    assert en.number_word(1) == "one"
    assert en.number_word(17) == "seventeen"
    assert en.number_word(21) == "twenty-one"
    assert en.number_word(84) == "eighty-four"
    assert en.number_word(100) == "one hundred"
    assert en.number_word(101) == "one hundred one"
    assert en.number_word(1001) == "one thousand one"


def test_distance_auto():
    assert en.distance_text(1.843) == "one point eight four three meters"
    assert en.distance_text(1.84) == "one point eight four meters"
    assert en.distance_text(1.0) == "one meter"
    assert en.distance_text(2.0) == "two meters"
    assert en.distance_text(0.5) == "fifty centimeters"
    assert en.distance_text(0.512) == "fifty-one point two centimeters"
    assert en.distance_text(0.0) == "zero"


def test_distance_coarse():
    assert en.distance_text(1.843, precise=False) == "one point eight four meters"


def test_distance_fixed_units():
    assert en.distance_text(0.001, unit="mm") == "one millimeter"
    assert en.distance_text(0.002, unit="mm") == "two millimeters"
    assert en.distance_text(0.015, unit="cm") == "one point five centimeters"
    assert en.distance_text(1.5, unit="m") == "one point five meters"


def test_distance_negative():
    assert en.distance_text(-1.0) == "minus one meter"


def test_area_volume():
    assert en.area_text(2.128) == "two point one three square meters"
    assert en.area_text(1.0) == "one square meter"
    assert en.volume_text(0.5) == "zero point five cubic meters"


def test_speech_builders():
    assert en.mode_speech("Length") == "Length mode"
    assert en.error_speech() == "Measurement failed"
    assert en.partial_speech(1, "one meter") == "First length one meter"
    assert en.area_result_speech("a", "b") == "Second length a, area b"
    assert en.volume_result_speech("a", "b") == "Third length a, volume b"
    assert en.result_speech("x") == "Result x"
    assert en.connected_speech() == "Connected"


def test_language_modules_share_interface():
    for module in LANGUAGES.values():
        for name in PUBLIC_API:
            assert hasattr(module, name), f"{module.NAME} lacks {name}"
    assert set(de.UI) == set(en.UI)
    assert set(de.MODES) == set(en.MODES)


def test_get_language():
    assert get_language("de") is de
    assert get_language("en") is en
    assert get_language(None) in (de, en)  # locale-dependent, must not raise
