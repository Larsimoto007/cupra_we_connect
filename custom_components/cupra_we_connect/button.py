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

    _LOGGER.warning("BUTTON setup: vehicles_count=%s", len(vehicles))

    entities = []
    for vehicle in vehicles:  # weConnect.vehicles.items():
        vin = getattr(vehicle.vin, "value", str(vehicle.vin))
        _LOGGER.warning("BUTTON creating for VIN=%s nick=%s", vin, vehicle.nickname)
        entities.append(VolkswagenIDStartClimateButton(vehicle, we_connect))
        entities.append(VolkswagenIDStopClimateButton(vehicle, we_connect))
        entities.append(VolkswagenIDStartChargingButton(vehicle, we_connect))
        entities.append(VolkswagenIDStopChargingButton(vehicle, we_connect))
        entities.append(VolkswagenIDToggleACChargeSpeed(vehicle, we_connect))

    _LOGGER.warning("BUTTON adding %s entities", len(entities))
    async_add_entities(entities)

    return True


class VolkswagenIDStartClimateButton(ButtonEntity):
    """Button for starting climate."""

    def __init__(self, vehicle, we_connect) -> None:
        """Initialize VolkswagenID vehicle sensor."""
        self._we_connect = we_connect
        self._vehicle = vehicle

        vin = getattr(vehicle.vin, "value", str(vehicle.vin))

        self._attr_name = f"Start Climate"
        self._attr_unique_id = f"{vin}-start_climate"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{vin}")},
            manufacturer="CUPRA",
            model=getattr(vehicle, "model", None),
            name=vehicle.nickname,
        )
    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            set_climatisation, self._vehicle.vin.value, self._we_connect, "start", 0
        )


class VolkswagenIDStopClimateButton(ButtonEntity):
    """Button for starting climate."""

    def __init__(self, vehicle, we_connect) -> None:
        """Initialize VolkswagenID vehicle sensor."""
        self._we_connect = we_connect
        self._vehicle = vehicle

        vin = getattr(vehicle.vin, "value", str(vehicle.vin))

        self._attr_name = f"Stop Climate"
        self._attr_unique_id = f"{vin}-stop_climate"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{vin}")},
            manufacturer="CUPRA",
            model=getattr(vehicle, "model", None),
            name=vehicle.nickname,
        )

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            set_climatisation, self._vehicle.vin.value, self._we_connect, "stop", 0
        )


class VolkswagenIDStartChargingButton(ButtonEntity):
    """Button for starting charging."""

    def __init__(self, vehicle, we_connect) -> None:
        """Initialize VolkswagenID vehicle sensor."""
        self._we_connect = we_connect
        self._vehicle = vehicle

        vin = getattr(vehicle.vin, "value", str(vehicle.vin))

        self._attr_name = f"Start Charging"
        self._attr_unique_id = f"{vin}-start_charging"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{vin}")},
            manufacturer="CUPRA",
            model=getattr(vehicle, "model", None),
            name=vehicle.nickname,
        )

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            start_stop_charging, self._vehicle.vin.value, self._we_connect, "start"
        )


class VolkswagenIDStopChargingButton(ButtonEntity):
    """Button for starting climate."""

    def __init__(self, vehicle, we_connect) -> None:
        """Initialize VolkswagenID vehicle sensor."""
        self._we_connect = we_connect
        self._vehicle = vehicle

        vin = getattr(vehicle.vin, "value", str(vehicle.vin))

        self._attr_name = f"Stop Charging"
        self._attr_unique_id = f"{vin}-stop_charging"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{vin}")},
            manufacturer="CUPRA",
            model=getattr(vehicle, "model", None),
            name=vehicle.nickname,
        )

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            start_stop_charging, self._vehicle.vin.value, self._we_connect, "stop"
        )

class VolkswagenIDToggleACChargeSpeed(ButtonEntity):
    """Button for toggling the charge speed."""

    def __init__(self, vehicle, we_connect: weconnect_cupra.WeConnect) -> None:
        """Initialize VolkswagenID vehicle sensor."""
        self._we_connect = we_connect
        self._vehicle = vehicle

        vin = getattr(vehicle.vin, "value", str(vehicle.vin))

        self._attr_name = f"Toggle AC Charge Speed"
        self._attr_unique_id = f"{vin}-toggle_ac_charge_speed"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{vin}")},
            manufacturer="CUPRA",
            model=getattr(vehicle, "model", None),
            name=vehicle.nickname,
        )

    async def async_press(self) -> None:
        """Handle the button press asynchronously."""
        current_state = get_object_value(
            self._vehicle.domains["charging"]["chargingSettings"].maxChargeCurrentAC
        )

        if current_state == "maximum":
            _LOGGER.debug("Switching AC charge speed to reduced for VIN %s", self._vehicle.vin.value)
            await self.hass.async_add_executor_job(
                set_ac_charging_speed,
                self._vehicle.vin.value,
                self._we_connect,
                "reduced",
            )
        else:
            _LOGGER.debug("Switching AC charge speed to maximum for VIN %s", self._vehicle.vin.value)
            await self.hass.async_add_executor_job(
                set_ac_charging_speed,
                self._vehicle.vin.value,
                self._we_connect,
                "maximum",
            )
