"""Tests for safe display-name translation and English fallbacks."""

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.localization import (
    LocalizedEntityNameMixin,
    translated_text,
)


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        (None, "Soil Moisture CH2"),
        (42, "Soil Moisture CH2"),
        ("Bodenfeuchte {missing}", "Soil Moisture CH2"),
        ("Bodenfeuchte {channel", "Soil Moisture CH2"),
        ("Bodenfeuchte {}", "Soil Moisture CH2"),
        ("Bodenfeuchte {channel}", "Bodenfeuchte 2"),
    ],
)
async def test_translation_fallback_and_channel_formatting(
    hass: HomeAssistant, template, expected: str
) -> None:
    """Missing or broken translations retain the complete English display name."""
    hass.config.language = "de"
    translations = (
        {f"component.{DOMAIN}.entity.sensor.soil_moisture_ch.name": template}
        if template is not None
        else {}
    )
    with patch(
        "custom_components.ecowitt_local.localization.async_get_cached_translations",
        return_value=translations,
    ) as cached_translations:
        assert (
            translated_text(
                hass,
                "entity",
                "sensor.soil_moisture_ch.name",
                "Soil Moisture CH2",
                {"channel": "2"},
            )
            == expected
        )

    cached_translations.assert_called_once_with(hass, "de", "entity", DOMAIN)


@pytest.mark.parametrize(
    ("name", "translation_key"),
    [(None, "temperature"), ("Custom Sensor Name", None)],
)
def test_names_without_translation_keep_their_original_value(
    name, translation_key
) -> None:
    """Unnamed entities and names without a translation key need no catalog."""
    entity = LocalizedEntityNameMixin()
    entity._attr_name = name
    entity._attr_translation_key = translation_key

    with patch(
        "custom_components.ecowitt_local.localization.translated_text"
    ) as translate:
        assert entity.name == name

    translate.assert_not_called()
