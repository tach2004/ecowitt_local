"""Test opt-in WN32 routing and the Home Assistant entity lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import (
    CONF_HOST,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecowitt_local.const import CONF_ASSIGN_WN32_TO_WS90, DOMAIN
from tests.test_entity_naming import _entities_by_key, _mapping, _set_gateway

_WS90 = _mapping("A90", "wh90", 48, "Temp & Humidity & Solar & Wind & Rain")
_WN32 = {**_mapping("BA90", "wh26", 5, "Temp & Humidity"), "batt": "3", "signal": "2"}
_WH40 = _mapping("A40", "wh40", 3, "Rain")
_OUTDOOR_KEYS = {
    "0x02": "outdoor_temp",
    "0x07": "outdoor_humidity",
    "0x03": "dewpoint",
    "absolute_humidity_outdoor": "absolute_humidity",
}


@pytest.fixture
def gateway(mock_ecowitt_api):
    """Keep the gateway mocked during initial setup and options-driven reloads."""
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        yield mock_ecowitt_api


def _entry(hass: HomeAssistant, host: str = "192.0.2.90", **options) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: host}, options=options, minor_version=3
    )
    entry.add_to_hass(hass)
    return entry


def _live(temperature="20", humidity="50%", dew_point="9", **dew_point_fields):
    return {
        "common_list": [
            {"id": "0x02", "val": temperature, "unit": "C"},
            {"id": "0x07", "val": humidity},
            {"id": "0x03", "val": dew_point, "unit": "C", **dew_point_fields},
            {"id": "0x04", "val": "18", "unit": "C"},
            {"id": "0x05", "val": "21", "unit": "C"},
            {"id": "0x0B", "val": "2.4 m/s"},
            {"id": "0x0C", "val": "3.5 m/s"},
            {"id": "0x15", "val": "120 W/m²"},
            {"id": "0x17", "val": "3"},
            {"id": "3", "val": "19", "unit": "C"},
            {"id": "5", "val": "0.9 kPa"},
        ],
        "rain": [{"id": "0x13", "val": "12 mm", "battery": "0"}],
        "piezoRain": [{"id": "0x13", "val": "34 mm"}],
    }


async def _setup(hass, entry, gateway, mappings, live):
    _set_gateway(gateway, mappings, live)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _refresh(hass, entry, gateway, mappings, live):
    _set_gateway(gateway, mappings, live)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh_mapping()
    await coordinator.async_refresh()
    await hass.async_block_till_done()


def _outdoor_entities(hass, entry, hardware_id):
    entries = _entities_by_key(hass, entry)
    return {
        key: entries[f"{DOMAIN}_{hardware_id}_{key}"].entity_id
        for key in _OUTDOOR_KEYS
        if f"{DOMAIN}_{hardware_id}_{key}" in entries
    }


def _expected_ids(hardware_id):
    return {
        key: f"sensor.ecowitt_{name}_{hardware_id.lower()}"
        for key, name in _OUTDOOR_KEYS.items()
    }


def _state(hass, entity_id):
    state = hass.states.get(entity_id)
    return state.state if state else None


def _assert_inactive(hass, entity_ids):
    for entity_id in entity_ids.values():
        assert _state(hass, entity_id) in (None, STATE_UNAVAILABLE), entity_id


@pytest.mark.parametrize(
    ("mappings", "enabled", "expected"),
    [
        ([_WS90], True, "A90"),
        ([_WN32], True, "BA90"),
        ([_WS90, _WN32], False, "BA90"),
        ([_WS90, _WN32], True, "A90"),
        ([_WN32, _WS90], True, "A90"),
        ([_WS90, _WN32, _mapping("A80", "ws80", 2, "Wind")], True, "A90"),
        ([_WS90, _WN32, {**_WS90, "id": "DD90", "img": "ws90"}], True, "BA90"),
        ([_WS90, {**_WS90, "id": "DD90", "signal": "0"}, _WN32], True, "BA90"),
        ([{**_WS90, "signal": "0"}, _WN32], True, "BA90"),
        ([{**_WS90, "id": "00000000"}, _WN32], True, "BA90"),
    ],
)
async def test_assignment_requires_a_unique_receiving_ws90(
    hass, gateway, mappings, enabled, expected
):
    """Register one set of outdoor measurements where the active mode expects it."""
    entry = _entry(hass, **{CONF_ASSIGN_WN32_TO_WS90: enabled})
    await _setup(hass, entry, gateway, mappings, _live())

    assert _outdoor_entities(hass, entry, expected) == _expected_ids(expected)
    for key, value in zip(_OUTDOOR_KEYS, (20, 50, 9, 8.62), strict=True):
        entity_id = _expected_ids(expected)[key]
        assert float(_state(hass, entity_id)) == pytest.approx(value, abs=0.005)
    for hardware_id in {mapping["id"] for mapping in mappings} - {expected}:
        assert _outdoor_entities(hass, entry, hardware_id) == {}


async def test_options_reload_reuses_both_devices_entity_registry_entries(
    hass, gateway
):
    """Existing entries and custom names survive repeated changes in either direction."""
    entry = _entry(hass)
    hass.config.language = "de"
    await _setup(hass, entry, gateway, [_WS90, _WN32], _live())
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    wn32 = devices.async_get_device(identifiers={(DOMAIN, "BA90")})
    assert wn32.model == "wh26"
    assert (
        wn32.name == "Ecowitt WH26/WN32 Außentemperatur-/Luftfeuchtigkeitssensor BA90"
    )
    devices.async_update_device(wn32.id, name_by_user="Garden probe")

    wn32_ids = _outdoor_entities(hass, entry, "BA90")
    assert wn32_ids == _expected_ids("BA90")
    assert _outdoor_entities(hass, entry, "A90") == {}
    renamed = registry.async_update_entity(
        wn32_ids["0x02"], new_entity_id="sensor.custom_outdoor_temperature"
    )
    wn32_ids["0x02"] = renamed.entity_id
    await hass.async_block_till_done()

    async def set_option(enabled):
        old_coordinator = hass.data[DOMAIN][entry.entry_id]
        old_value = entry.options.get(CONF_ASSIGN_WN32_TO_WS90, False)
        form = await hass.config_entries.options.async_init(entry.entry_id)
        defaults = form["data_schema"]({})
        assert defaults[CONF_ASSIGN_WN32_TO_WS90] is old_value
        with patch.object(
            hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
        ) as reload_entry:
            result = await hass.config_entries.options.async_configure(
                form["flow_id"], {**defaults, CONF_ASSIGN_WN32_TO_WS90: enabled}
            )
            await hass.async_block_till_done()
        assert result["type"] == FlowResultType.CREATE_ENTRY
        reload_entry.assert_awaited_once_with(entry.entry_id)
        assert hass.data[DOMAIN][entry.entry_id] is not old_coordinator

    ws90_ids = _expected_ids("A90")
    with patch.object(registry, "async_remove", wraps=registry.async_remove) as remove:
        for enabled in (True, False, True, False):
            await set_option(enabled)
            assert _outdoor_entities(hass, entry, "BA90") == wn32_ids
            assert _outdoor_entities(hass, entry, "A90") == ws90_ids
            assert registry.async_get(wn32_ids["0x02"]).unique_id == renamed.unique_id
            assert devices.async_get(wn32.id).name_by_user == "Garden probe"
            active = ws90_ids if enabled else wn32_ids
            inactive = wn32_ids if enabled else ws90_ids
            assert float(_state(hass, active["0x02"])) == 20
            _assert_inactive(hass, inactive)
        remove.assert_not_called()

    # User removes a currently unprovided entity and leaves its old ID free.
    await set_option(True)
    humidity_id = wn32_ids["0x07"]
    registry.async_remove(humidity_id)
    await hass.async_block_till_done()
    assert registry.async_get(humidity_id) is None
    await set_option(False)
    assert _outdoor_entities(hass, entry, "BA90") == wn32_ids
    assert registry.async_get(humidity_id).unique_id == f"{DOMAIN}_BA90_0x07"
    assert float(_state(hass, humidity_id)) == 50


async def test_pairing_and_radio_loss_keep_ws90_ids_and_wn32_diagnostics(hass, gateway):
    """The gateway can switch sources while WS90 history and rain routing stay stable."""
    entry = _entry(hass, **{CONF_ASSIGN_WN32_TO_WS90: True})
    await _setup(hass, entry, gateway, [_WS90, _WH40], _live())
    ws90_ids = _expected_ids("A90")
    assert _outdoor_entities(hass, entry, "A90") == ws90_ids

    coordinator = hass.data[DOMAIN][entry.entry_id]
    unchanged = []
    for key, hardware_id in (
        ("0x04", "A90"),
        ("0x05", "A90"),
        ("0x0B", "A90"),
        ("0x0C", "A90"),
        ("0x15", "A90"),
        ("0x17", "A90"),
        ("3", "A90"),
        ("5", "A90"),
        ("0x13", "A90"),
        ("0x13", "A40"),
    ):
        reading = coordinator.get_sensor_data_by_key(key, hardware_id)
        unchanged.append((key, hardware_id, reading["entity_id"], reading["state"]))
    assert coordinator.get_sensor_data_by_key("0x13", "A90")["state"] == 34
    assert coordinator.get_sensor_data_by_key("0x13", "A40")["state"] == 12

    await _refresh(hass, entry, gateway, [_WS90, _WN32, _WH40], _live("24"))
    assert coordinator.sensor_mapper.get_hardware_id("0x02") == "BA90"
    assert _outdoor_entities(hass, entry, "BA90") == {}
    assert _outdoor_entities(hass, entry, "A90") == ws90_ids
    assert float(_state(hass, ws90_ids["0x02"])) == 24
    for key, hardware_id, entity_id, value in unchanged:
        reading = coordinator.get_sensor_data_by_key(key, hardware_id)
        assert (reading["entity_id"], reading["state"]) == (entity_id, value)

    wn32 = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "BA90")})
    entries = _entities_by_key(hass, entry)
    for key, value in {
        "wh26batt": "60",
        "signal_BA90": "50",
        "rssi_BA90": "-60",
        "signal_quality_BA90": "80",
        "hardware_id_BA90": "BA90",
        "online": STATE_ON,
    }.items():
        diagnostic = entries[f"{DOMAIN}_BA90_{key}"]
        assert diagnostic.device_id == wn32.id
        assert _state(hass, diagnostic.entity_id) == value

    online = entries[f"{DOMAIN}_BA90_online"].entity_id
    assert online == "binary_sensor.ecowitt_sensor_ba90_online"
    for signal, expected in (("0", STATE_OFF), ("--", STATE_UNKNOWN)):
        offline = {**_WN32, "signal": signal, "batt": "--"}
        await _refresh(hass, entry, gateway, [_WS90, offline, _WH40], _live("18"))
        assert coordinator.sensor_mapper.get_hardware_id("0x02") == "A90"
        assert _state(hass, online) == expected
        assert float(_state(hass, ws90_ids["0x02"])) == 18
    await _refresh(hass, entry, gateway, [_WS90, _WH40], _live("17"))
    assert _state(hass, online) == STATE_OFF
    assert float(_state(hass, ws90_ids["0x02"])) == 17
    await _refresh(
        hass, entry, gateway, [_WN32, _WS90, _WH40], _live("23", battery="0")
    )
    assert _state(hass, online) == STATE_ON
    assert float(_state(hass, ws90_ids["0x02"])) == 23
    assert _state(hass, entries[f"{DOMAIN}_BA90_wh26batt"].entity_id) == "100"
    assert _outdoor_entities(hass, entry, "A90") == ws90_ids
    assert _outdoor_entities(hass, entry, "BA90") == {}


async def test_pairing_ws90_does_not_reuse_its_readings_for_an_old_wn32_entity(
    hass, gateway
):
    """A hardware ID substring cannot keep another device's entity available."""
    entry = _entry(hass, **{CONF_ASSIGN_WN32_TO_WS90: True})
    await _setup(hass, entry, gateway, [_WN32], _live())
    wn32_ids = _outdoor_entities(hass, entry, "BA90")
    assert wn32_ids == _expected_ids("BA90")

    await _refresh(hass, entry, gateway, [_WS90, _WN32], _live("24"))
    ws90_ids = _outdoor_entities(hass, entry, "A90")
    assert ws90_ids == _expected_ids("A90")
    assert float(_state(hass, ws90_ids["0x02"])) == 24
    assert _outdoor_entities(hass, entry, "BA90") == wn32_ids
    _assert_inactive(hass, wn32_ids)

    await _refresh(hass, entry, gateway, [_WN32], _live("22"))
    assert float(_state(hass, wn32_ids["0x02"])) == 22
    _assert_inactive(hass, ws90_ids)


async def test_invalid_outdoor_readings_do_not_publish_old_values(hass, gateway):
    """Refresh never substitutes a previous valid reading after malformed input."""
    entry = _entry(hass, **{CONF_ASSIGN_WN32_TO_WS90: True})
    mappings = [_WS90, _WN32]
    await _setup(hass, entry, gateway, mappings, _live())
    ws90_ids = _expected_ids("A90")
    invalid = _live(temperature="--", humidity="101%", dew_point="nan")
    await _refresh(hass, entry, gateway, mappings, invalid)
    _assert_inactive(hass, ws90_ids)

    await _refresh(hass, entry, gateway, mappings, _live("19", "0%", "-30"))
    assert float(_state(hass, ws90_ids["0x02"])) == 19
    assert float(_state(hass, ws90_ids["absolute_humidity_outdoor"])) == 0
    assert _outdoor_entities(hass, entry, "A90") == ws90_ids


async def test_assignment_uses_mapping_at_entity_creation(hass, gateway):
    """Use the latest target if a mapping refresh finishes during live processing."""
    entry = _entry(hass, **{CONF_ASSIGN_WN32_TO_WS90: True})
    await _setup(hass, entry, gateway, [_WS90, _WN32], _live())
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async def refresh_mapping_during_poll():
        gateway.get_all_sensor_mappings.return_value = [_WN32]
        await coordinator._update_sensor_mapping()
        return []

    gateway.get_soil_calibration.side_effect = refresh_mapping_during_poll
    gateway.get_live_data.return_value = _live("24")
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    wn32_ids = _expected_ids("BA90")
    assert _outdoor_entities(hass, entry, "BA90") == wn32_ids
    assert float(_state(hass, wn32_ids["0x02"])) == 24
    _assert_inactive(hass, _expected_ids("A90"))


async def test_assignment_is_scoped_to_each_gateway(hass, mock_ecowitt_api):
    """A WS90 on one gateway cannot become the target for a different gateway."""
    first_gateway = mock_ecowitt_api
    other_gateway = AsyncMock()
    other_gateway.get_units.return_value = {}
    other_gateway.get_soil_calibration.return_value = []
    other_gateway.get_lds_config.return_value = []
    other_gateway.get_version.return_value = {"stationtype": "GW3000", "version": "1.0"}

    first = _entry(hass, **{CONF_ASSIGN_WN32_TO_WS90: True})
    second_host = "192.0.2.32"
    other_wn32 = {**_WN32, "id": "B32"}
    gateways = {
        first.data[CONF_HOST]: first_gateway,
        second_host: other_gateway,
    }
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        side_effect=lambda host, password: gateways[host],
    ):
        await _setup(hass, first, first_gateway, [_WS90, _WN32], _live("24"))
        second = _entry(hass, second_host, **{CONF_ASSIGN_WN32_TO_WS90: True})
        await _setup(hass, second, other_gateway, [other_wn32], _live("18"))

    assert _outdoor_entities(hass, first, "A90") == _expected_ids("A90")
    assert _outdoor_entities(hass, first, "BA90") == {}
    assert _outdoor_entities(hass, second, "B32") == _expected_ids("B32")
    assert _outdoor_entities(hass, second, "A90") == {}
    assert float(_state(hass, _expected_ids("A90")["0x02"])) == 24
    assert float(_state(hass, _expected_ids("B32")["0x02"])) == 18
