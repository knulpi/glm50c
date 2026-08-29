"""Freezes the behavior of the original German verbalizer."""

from glm50c.lang import de


def test_zahlwort():
    assert de.zahlwort(0) == "null"
    assert de.zahlwort(1) == "ein"
    assert de.zahlwort(17) == "siebzehn"
    assert de.zahlwort(21) == "einundzwanzig"
    assert de.zahlwort(84) == "vierundachtzig"
    assert de.zahlwort(100) == "einhundert"
    assert de.zahlwort(101) == "einhunderteins"
    assert de.zahlwort(1001) == "eintausendeins"
    assert de.zahlwort(2345) == "zweitausenddreihundertfünfundvierzig"


def test_distance_auto():
    assert de.distance_text(1.843) == "ein Meter vierundachtzig Komma drei"
    assert de.distance_text(1.84) == "ein Meter vierundachtzig"
    assert de.distance_text(1.0) == "ein Meter"
    assert de.distance_text(2.0) == "zwei Meter"
    assert de.distance_text(0.5) == "fünfzig Zentimeter"
    assert de.distance_text(0.512) == "einundfünfzig Komma zwei Zentimeter"
    assert de.distance_text(0.0) == "null"


def test_distance_coarse():
    assert de.distance_text(1.843, precise=False) == "ein Meter vierundachtzig"


def test_distance_fixed_units():
    assert de.distance_text(0.001, unit="mm") == "ein Millimeter"
    assert de.distance_text(1.843, unit="mm") == (
        "eintausendachthundertdreiundvierzig Millimeter")
    assert de.distance_text(0.015, unit="cm") == "eins Komma fünf Zentimeter"
    assert de.distance_text(1.5, unit="m") == "ein Meter fünfzig"


def test_distance_negative():
    assert de.distance_text(-1.0) == "minus ein Meter"


def test_area_volume():
    assert de.area_text(2.128) == "zwei Komma eins drei Quadratmeter"
    assert de.area_text(2.1) == "zwei Komma eins Quadratmeter"
    assert de.area_text(1.0) == "ein Quadratmeter"
    assert de.volume_text(0.5) == "null Komma fünf Kubikmeter"


def test_speech_builders():
    assert de.mode_speech("Länge") == "Modus Länge"
    assert de.error_speech() == "Messfehler"
    assert de.partial_speech(1, "ein Meter") == "Erste Länge ein Meter"
    assert de.partial_speech(2, "x") == "Zweite Länge x"
    assert de.area_result_speech("a", "b") == "Zweite Länge a, Fläche b"
    assert de.volume_result_speech("a", "b") == "Dritte Länge a, Volumen b"
    assert de.result_speech("x") == "Ergebnis x"
    assert de.connected_speech() == "Verbunden"
