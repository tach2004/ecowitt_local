"""Test locally calculated absolute humidity through the sensor platform."""

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import device_registry as dr

from custom_components.ecowitt_local.const import DOMAIN
from tests.test_entity_naming import (
    _entities_by_key,
    _entry,
    _mapping,
    _set_gateway,
    _setup,
    _wh31,
)


@pytest.mark.parametrize("include_inactive", [False, True])
async def test_only_air_temperature_and_humidity_create_entities(
    hass, mock_ecowitt_api, include_inactive
):
    """Rain, soil and temperature-only sensors don't enter the entity registry."""
    entry = _entry(hass)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "include_inactive": include_inactive}
    )
    hass.config.language = "de"
    mappings = [
        _mapping("A90", "ws90", 48, "Weather Station"),
        _mapping("A40", "wh40", 3, "Rain"),
        _mapping("A45", "wh45", 39, "PM25 & PM10 & CO2"),
        _mapping("A52", "wh51", 14, "Soil Moisture CH1"),
        _wh31("AAA", 1),
        _wh31("AAA", 2),
        _wh31("BBB", 3),
        _wh31("CCC", 4),
    ]
    live = {
        "common_list": [
            {"id": "0x02", "val": "20 °C"},
            {"id": "0x07", "val": "50%"},
            {"id": "absolute_humidity_ch3", "val": "99"},
        ],
        "wh25": [{"intemp": "20", "unit": "C", "inhumi": 50}],
        "co2": [{"temp": "68", "unit": "F", "humidity": "50%"}],
        "ch_aisle": [
            {"channel": "1", "temp": "68", "humidity": "50%"},
            {"channel": "2", "temp": "68", "humidity": "25%"},
            {"channel": "3", "temp": "70", "humidity": "None"},
            {"channel": "4", "humidity": "90%"},
        ],
        "ch_ec": [{"channel": "1", "temp": "20", "unit": "C", "humidity": "60%"}],
        "rain": [{"id": "0x13", "val": "29.5 mm", "battery": "0"}],
    }
    await _setup(hass, mock_ecowitt_api, entry, mappings, live)

    expected = {
        "sensor.ecowitt_absolute_humidity_a90": ("A90", 8.62),
        "sensor.ecowitt_absolute_humidity_a45": ("A45", 8.62),
        "sensor.ecowitt_absolute_humidity_aaa_ch1": ("AAA_ch1", 8.62),
        "sensor.ecowitt_absolute_humidity_aaa_ch2": ("AAA_ch2", 4.31),
        "sensor.ecowitt_absolute_humidity_indoor": (None, 8.62),
    }
    entities = {
        entity.entity_id: entity
        for key, entity in _entities_by_key(hass, entry).items()
        if "absolute_humidity" in key
    }
    assert entities.keys() == expected.keys()
    devices = dr.async_get(hass)
    for entity_id, (hardware_id, value) in expected.items():
        entity = entities[entity_id]
        assert entity.disabled_by is None
        state = hass.states.get(entity_id)
        assert float(state.state) == pytest.approx(value, abs=0.005)
        assert state.attributes["unit_of_measurement"] == "g/m³"
        assert state.attributes["device_class"] == SensorDeviceClass.ABSOLUTE_HUMIDITY
        assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT
        assert state.attributes["icon"] == "mdi:water-opacity"
        assert "Absolute Luftfeuchtigkeit" in state.attributes["friendly_name"]
        if hardware_id:
            device = devices.async_get_device(identifiers={(DOMAIN, hardware_id)})
            assert entity.device_id == device.id


async def test_absolute_humidity_appears_and_updates_with_valid_inputs(
    hass, mock_ecowitt_api
):
    """Either input can change the value, and a missing input makes it unavailable."""
    entry = _entry(hass)
    mappings = [_wh31("D01", 1)]
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        mappings,
        {"ch_aisle": [{"channel": "1", "temp": "20", "humidity": None}]},
    )
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entity_id = "sensor.ecowitt_absolute_humidity_d01"
    assert hass.states.get(entity_id) is None

    async def poll(readings):
        live = {"ch_aisle": [{"channel": "1", **readings}]}
        _set_gateway(mock_ecowitt_api, mappings, live)
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        return hass.states.get(entity_id).state

    assert float(await poll({"temp": "20", "humidity": "50%"})) == pytest.approx(
        8.62, abs=0.005
    )
    assert float(await poll({"temp": "20", "humidity": "25%"})) == pytest.approx(
        4.31, abs=0.005
    )
    assert float(await poll({"temp": 0, "humidity": "25%"})) == pytest.approx(
        1.21, abs=0.005
    )
    assert await poll({"humidity": "25%"}) == STATE_UNAVAILABLE
    assert await poll({"temp": "20", "humidity": "--"}) == STATE_UNAVAILABLE
    assert float(await poll({"temp": "20", "humidity": 0})) == 0.0


async def test_absolute_humidity_follows_outdoor_mapping(hass, mock_ecowitt_api):
    """A gateway fallback stays unavailable when the sensor gains its own device."""
    entry = _entry(hass)
    live = {
        "common_list": [
            {"id": "tempf", "val": "68"},
            {"id": "humidity", "val": "50%"},
        ]
    }
    await _setup(hass, mock_ecowitt_api, entry, [], live)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    fallback = "sensor.ecowitt_absolute_humidity_outdoor"
    assert float(hass.states.get(fallback).state) == pytest.approx(8.62, abs=0.005)

    mappings = [_mapping("A68", "wh68", 1, "Solar & Wind")]
    # Both encodings may be present, but the hardware gets one derived entity.
    live["common_list"] += [
        {"id": "0x02", "val": "20", "unit": "C"},
        {"id": "0x07", "val": "50%"},
    ]
    _set_gateway(mock_ecowitt_api, mappings, live)
    await coordinator.async_refresh_mapping()
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(fallback).state == STATE_UNAVAILABLE
    mapped = hass.states.get("sensor.ecowitt_absolute_humidity_a68")
    assert float(mapped.state) == pytest.approx(8.62, abs=0.005)
