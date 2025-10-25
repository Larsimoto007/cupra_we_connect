"""Button integration."""
from weconnect_cupra import weconnect_cupra

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

from . import get_object_value, set_ac_charging_speed, set_climatisation, start_stop_charging
from .const import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add buttons for passed config_entry in HA."""
    we_connect: weconnect_cupra.WeConnect = hass.data[DOMAIN][config_entry.entry_id]
    vehicles = hass.data[DOMAIN][config_entry.entry_id + "_vehicles"]

    entities = []
    for vehicle in vehicles:  # weConnect.vehicles.items():
        entities.append(VolkswagenIDStartClimateButton(vehicle, we_connect))
        entities.append(VolkswagenIDStopClimateButton(vehicle, we_connect))
        entities.append(VolkswagenIDStartChargingButton(vehicle, we_connect))
        entities.append(VolkswagenIDStopChargingButton(vehicle, we_connect))
        entities.append(VolkswagenIDToggleACChargeSpeed(vehicle, we_connect))

    async_add_entities(entities)

    return True

class CupraBaseButton(ButtonEntity):
    """Gemeinsame Basis für Cupra Buttons."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    # Standardmäßig auf deaktiviert setzen, da die Controls als Switch vorhanden sind
    _attr_entity_registry_enabled_default = False

    def __init__(self, vehicle, we_connect):
        self._we_connect = we_connect
        self._vehicle = vehicle

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{self.data.vin}")},
            manufacturer="Cupra",
            model=f"{self.data.model}",  
            name=f"{self.data.nickname}",
        )

class VolkswagenIDStartClimateButton(CupraBaseButton):
    def __init__(self, vehicle, we_connect):
        super().__init__(vehicle, we_connect)
        self._attr_name = "Start Climate"
        self._attr_unique_id = f"{self._vin}-start_climate"

    async def async_press(self) -> None:
        from . import set_climatisation
        await self.hass.async_add_executor_job(
            set_climatisation, self._vehicle.vin.value, self._we_connect, "start", 0
        )


class VolkswagenIDStopClimateButton(CupraBaseButton):
    def __init__(self, vehicle, we_connect):
        super().__init__(vehicle, we_connect)
        self._attr_name = "Stop Climate"
        self._attr_unique_id = f"{self._vin}-stop_climate"

    async def async_press(self) -> None:
        from . import set_climatisation
        await self.hass.async_add_executor_job(
            set_climatisation, self._vehicle.vin.value, self._we_connect, "stop", 0
        )


class VolkswagenIDStartChargingButton(CupraBaseButton):
    def __init__(self, vehicle, we_connect):
        super().__init__(vehicle, we_connect)
        self._attr_name = "Start Charging"
        self._attr_unique_id = f"{self._vin}-start_charging"

    async def async_press(self) -> None:
        from . import start_stop_charging
        await self.hass.async_add_executor_job(
            start_stop_charging, self._vehicle.vin.value, self._we_connect, "start"
        )


class VolkswagenIDStopChargingButton(CupraBaseButton):
    def __init__(self, vehicle, we_connect):
        super().__init__(vehicle, we_connect)
        self._attr_name = "Stop Charging"
        self._attr_unique_id = f"{self._vin}-stop_charging"

    async def async_press(self) -> None:
        from . import start_stop_charging
        await self.hass.async_add_executor_job(
            start_stop_charging, self._vehicle.vin.value, self._we_connect, "stop"
        )


class VolkswagenIDToggleACChargeSpeed(CupraBaseButton):
    def __init__(self, vehicle, we_connect):
        super().__init__(vehicle, we_connect)
        self._attr_name = "Toggle AC Charge Speed"
        self._attr_unique_id = f"{self._vin}-toggle_ac_charge_speed"

    async def async_press(self) -> None:
        from . import get_object_value, set_ac_charging_speed

        current_state = get_object_value(
            self._vehicle.domains["charging"]["chargingSettings"].maxChargeCurrentAC
        )

        target = "reduced" if current_state == "maximum" else "maximum"
        _LOGGER.debug("Toggle AC charge speed for VIN %s -> %s", self._vin, target)

        await self.hass.async_add_executor_job(
            set_ac_charging_speed,
            self._vehicle.vin.value,
            self._we_connect,
            target,
        )