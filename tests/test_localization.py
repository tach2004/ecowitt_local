"""Contracts for complete name catalogs and safe localization fallbacks."""

from __future__ import annotations

import json
from pathlib import Path
from string import Formatter
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations, recursive_flatten

from custom_components.ecowitt_local.const import (
    BATTERY_SENSORS,
    BINARY_SENSORS,
    DOMAIN,
    SENSOR_TYPES,
    SYSTEM_SENSORS,
)
from custom_components.ecowitt_local.device_naming import (
    device_name,
    device_name_kwargs,
    gateway_name_kwargs,
)
from custom_components.ecowitt_local.localization import (
    LocalizedEntityNameMixin,
    name_translation_spec,
    translated_text,
)

COMPONENT = Path(__file__).parents[1] / "custom_components" / DOMAIN


def _unique_object(pairs):
    """Fail loudly if a hand-edited catalog contains duplicate JSON keys."""
    result = {}
    for key, value in pairs:
        assert key not in result, f"Duplicate translation key: {key}"
        result[key] = value
    return result


def _catalog(relative_path):
    """Read exactly the UTF-8 file that ships with the integration."""
    return json.loads(
        (COMPONENT / relative_path).read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )


def test_complete_german_catalog_matches_english_contract():
    """German must cover the source schema and preserve every placeholder."""
    source = _catalog("strings.json")
    english = _catalog("translations/en.json")
    german = _catalog("translations/de.json")
    assert source == english
    source_flat = recursive_flatten("", source)
    german_flat = recursive_flatten("", german)
    assert source_flat.keys() == german_flat.keys()
    formatter = Formatter()
    for key, source_text in source_flat.items():
        translated = german_flat[key]
        assert isinstance(translated, str) and translated.strip(), key
        source_fields = {
            field for _, field, _, _ in formatter.parse(source_text) if field
        }
        translated_fields = {
            field for _, field, _, _ in formatter.parse(translated) if field
        }
        assert source_fields == translated_fields, key


def test_catalog_covers_every_builtin_sensor_and_runtime_name():
    """A new sensor definition must not silently introduce an English-only name."""
    source = _catalog("strings.json")["entity"]
    available = set(source["sensor"]) | set(source["binary_sensor"])
    definitions = [SENSOR_TYPES, BATTERY_SENSORS, SYSTEM_SENSORS, BINARY_SENSORS]
    names = {
        definition[field]
        for definitions_by_key in definitions
        for definition in definitions_by_key.values()
        for field in ("name", "entity_name")
        if field in definition
    }
    names.update(
        {
            "Signal Strength",
            "RSSI",
            "Signal Quality",
            "Hardware ID",
            "Channel",
            "Battery",
            "Solar Illuminance",
            "Solar Radiation",
        }
    )
    missing = {
        name for name in names if name_translation_spec(name)[0] not in available
    }
    assert not missing, sorted(missing)


@pytest.mark.parametrize(
    ("name", "key", "placeholders"),
    [
        ("Temperature CH1", "temperature_ch", {"channel": "1"}),
        ("Temperature CH16", "temperature_ch", {"channel": "16"}),
        ("Soil Moisture CH3 Battery", "soil_moisture_ch_battery", {"channel": "3"}),
        ("PM2.5 24h Avg CH4", "pm2_5_24h_avg_ch", {"channel": "4"}),
        ("Hardware ID", "hardware_id", {}),
        ("Solar Illuminance", "solar_illuminance", {}),
    ],
)
def test_channel_names_share_a_catalog_key(name, key, placeholders):
    """Channels use a placeholder while stable names need no runtime data."""
    assert name_translation_spec(name) == (key, placeholders)


async def test_real_loader_supplies_german_and_english_fallbacks(hass: HomeAssistant):
    """The public HA translation cache resolves display names in both languages."""
    hass.config.language = "de"
    for category in ("entity", "device"):
        await async_get_translations(hass, "de", category, {DOMAIN})
    assert translated_text(
        hass, "entity", "sensor.temperature.name", "Temperature"
    ) == ("Temperatur")
    assert (
        translated_text(
            hass,
            "entity",
            "sensor.temperature_ch.name",
            "Temperature CH16",
            {"channel": "16"},
        )
        == "Temperatur Kanal 16"
    )
    assert (
        translated_text(hass, "entity", "sensor.unknown.name", "Unknown") == "Unknown"
    )
    assert translated_text(hass, "missing", "unknown", "Fallback") == "Fallback"
    assert translated_text(
        None, "entity", "sensor.temperature.name", "Temperature"
    ) == ("Temperature")

    hass.config.language = "nl"
    await async_get_translations(hass, "nl", "entity", {DOMAIN})
    assert translated_text(
        hass, "entity", "sensor.temperature.name", "Temperature"
    ) == ("Temperature")


@pytest.mark.parametrize(
    "template", ["{missing}", "{broken", "{}", "{0}", "{channel:d}"]
)
async def test_invalid_translation_format_keeps_working(hass: HomeAssistant, template):
    """A malformed catalog entry cannot interrupt coordinator sensor updates."""
    with patch(
        "custom_components.ecowitt_local.localization.async_get_cached_translations",
        return_value={f"component.{DOMAIN}.entity.sensor.temperature.name": template},
    ):
        assert (
            translated_text(
                hass,
                "entity",
                "sensor.temperature.name",
                "Temperature",
                {"channel": "2"},
            )
            == "Temperature"
        )


def test_mixin_preserves_missing_name_and_untranslated_entity():
    """A platform without a name or catalog key keeps its original semantics."""
    entity = LocalizedEntityNameMixin()
    entity._attr_name = None
    assert entity.name is None
    entity._attr_name = "Gateway custom entity"
    assert entity.name == "Gateway custom entity"
    entity._attr_translation_key = "unknown"
    entity._attr_translation_placeholders = {}
    entity._translation_platform = "sensor"
    assert entity.name == "Gateway custom entity"


async def test_device_name_metadata_preserves_models_and_custom_titles(
    hass: HomeAssistant,
):
    """Native device translations leave hardware IDs, models and user titles intact."""
    hass.config.language = "de"
    await async_get_translations(hass, "de", "device", {DOMAIN})
    assert device_name("X1", {"sensor_type": "WH99"}, hass) == "Ecowitt WH99 X1"
    assert device_name("X1", {}, hass) == "Ecowitt Sensor X1"
    assert device_name("A1", {"sensor_type": "WH31"}) == (
        "Ecowitt Temperature/Humidity Sensor A1"
    )
    assert device_name_kwargs("X1", {"sensor_type": "WH99"}) == {
        "name": "Ecowitt WH99 X1",
        "translation_key": "model",
        "translation_placeholders": {"hardware_id": "X1", "model": "WH99"},
    }
    for info in (
        {"live_title": " Deep Freezer ", "sensor_type": "WH31"},
        {"channel": "2", "raw_data": {"name": " Deep Freezer "}},
    ):
        assert device_name_kwargs("A1", info) == {"name": "Deep Freezer"}
        assert device_name("A1", info, hass) == "Deep Freezer"
    assert gateway_name_kwargs({"host": "192.168.1.100"}) == {
        "name": "Ecowitt Gateway 192.168.1.100",
        "translation_key": "gateway",
        "translation_placeholders": {"host": "192.168.1.100"},
    }
