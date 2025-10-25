import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import set_climatisation, start_stop_charging, get_object_value,  set_ac_charging_speed
from weconnect_cupra import weconnect_cupra
from weconnect_cupra.elements.control_operation import ControlOperation

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    we_connect: weconnect_cupra.WeConnect = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = hass.data[DOMAIN][config_entry.entry_id + "_coordinator"]
    vehicles = hass.data[DOMAIN][config_entry.entry_id + "_vehicles"]  # Liste!

    entities = []
    for idx, vehicle in enumerate(vehicles):
        entities.append(CupraClimateSwitch(we_connect, coordinator, idx, vehicle))
        entities.append(CupraChargingSwitch(we_connect, coordinator, idx, vehicle))
        entities.append(CupraACChargeSpeedSwitch(we_connect, coordinator, idx, vehicle))


    async_add_entities(entities, update_before_add=False)
    return True


class CupraSwitchBase(CoordinatorEntity, SwitchEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, we_connect: weconnect_cupra.WeConnect, coordinator, index: int, vehicle):
        super().__init__(coordinator)
        self.we_connect = we_connect
        self.index = index
        self._vehicle = vehicle

        vin = getattr(vehicle.vin, "value", str(vehicle.vin))
        nickname = getattr(vehicle, "nickname", vin)
        model = getattr(vehicle, "model", None)

        self._vin = vin
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{vin}")},
            manufacturer="Cupra",
            model=model,
            name=nickname,
        )

    @property
    def data(self):
        # Vehicle-Objekt aus dem Coordinator nach Index
        return self.coordinator.data[self.index]



class CupraClimateSwitch(CupraSwitchBase):
    """Ein/Aus für Klimatisierung."""

    def __init__(self, we_connect, coordinator, index: int, vehicle):
        super().__init__(we_connect, coordinator, index, vehicle)
        self._attr_name = "Climate"
        self._attr_unique_id = f"{self._vin}-climate_switch"

    @property
    def is_on(self) -> bool:
        v = self.data
        # Versuche, einen sinnvollen Status zu lesen:
        # 1) über Domains (falls vorhanden)
        try:
            state = get_object_value(
                v.domains["climatisation"]["climatisationStatus"].climatisationState.value
            )
            # Mögliche Werte je nach Lib: "on"/"off", "heating"/"cooling"/"off" etc.
            return str(state).lower() not in ("off", "aus", "false", "inactive", "stopped", "0", "")
        except Exception:
            # 2) Fallback: Control-Zustand, wenn verfügbar (nicht immer lesbar)
            try:
                ctrl = v.controls.climatizationControl
                if ctrl is not None and hasattr(ctrl, "value"):
                    return ctrl.value == ControlOperation.START
            except Exception:
                pass
        return False

    async def async_turn_on(self, **kwargs) -> None:
        success = await self.hass.async_add_executor_job(
            set_climatisation, self._vin, self.we_connect, "start", 0
        )
        if success:
            # Optimistisch: sofort auf AN setzen
            self._attr_is_on = True
            self.async_write_ha_state()
        else:
            _LOGGER.error("Climate START failed for VIN %s", self._vin)

    async def async_turn_off(self, **kwargs) -> None:
        success = await self.hass.async_add_executor_job(
            set_climatisation, self._vin, self.we_connect, "stop", 0
        )
        if success:
            self._attr_is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.error("Climate STOP failed for VIN %s", self._vin)

class CupraChargingSwitch(CupraSwitchBase):
    """Ein/Aus für Ladevorgang."""

    def __init__(self, we_connect, coordinator, index: int, vehicle):
        super().__init__(we_connect, coordinator, index, vehicle)
        self._attr_name = "Charging"
        self._attr_unique_id = f"{self._vin}-charging_switch"

    @property
    def is_on(self) -> bool:
        v = self.data
        # Lies einen Status, z. B. ob aktuell geladen wird
        try:
            status = get_object_value(
                v.domains["charging"]["chargingStatus"].chargingState.value
            )
            # typische Werte: "charging", "ready", "error", "off", ...
            return str(status).lower() in ("charging", "dc_charging", "ac_charging", "on")
        except Exception:
            # Fallback: kein sicherer Status bekannt -> False
            return False

    async def async_turn_on(self, **kwargs) -> None:
        success = await self.hass.async_add_executor_job(
            start_stop_charging, self._vin, self.we_connect, "start"
        )
        if success:
            self._attr_is_on = True
            self.async_write_ha_state()
        else:
            _LOGGER.error("Charging START failed for VIN %s", self._vin)

    async def async_turn_off(self, **kwargs) -> None:
        success = await self.hass.async_add_executor_job(
            start_stop_charging, self._vin, self.we_connect, "stop"
        )
        if success:
            self._attr_is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.error("Charging STOP failed for VIN %s", self._vin)

class CupraACChargeSpeedSwitch(CupraSwitchBase):
    """Switch: ON = maximum, OFF = reduced"""

    def __init__(self, we_connect, coordinator, index: int, vehicle):
        super().__init__(we_connect, coordinator, index, vehicle)
        self._attr_name = "AC Charge Speed (Maximum)"
        self._attr_unique_id = f"{self._vin}-ac_charge_speed_switch"

    @property
    def is_on(self) -> bool:
        v = self.data
        try:
            current = get_object_value(
                v.domains["charging"]["chargingSettings"].maxChargeCurrentAC
            )
            return str(current).lower() == "maximum"
        except Exception:
            return False

    async def async_turn_on(self, **kwargs) -> None:
        success = await self.hass.async_add_executor_job(
            set_ac_charging_speed, self._vin, self.we_connect, "maximum"
        )
        if success:
            # Optional sofort aktualisieren
            self._attr_is_on = True
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set AC charge speed to maximum for VIN %s", self._vin)

    async def async_turn_off(self, **kwargs) -> None:
        success = await self.hass.async_add_executor_job(
            set_ac_charging_speed, self._vin, self.we_connect, "reduced"
        )
        if success:
            self._attr_is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set AC charge speed to reduced for VIN %s", self._vin)