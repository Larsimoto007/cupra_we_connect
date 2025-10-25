import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import set_climatisation, start_stop_charging, get_object_value
from weconnect_cupra import weconnect_cupra
from weconnect_cupra.elements.control_operation import ControlOperation

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    we_connect: weconnect_cupra.WeConnect = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = hass.data[DOMAIN][config_entry.entry_id + "_coordinator"]
    vehicles = hass.data[DOMAIN][config_entry.entry_id + "_vehicles"]  # Liste!

    entities = []
    for idx, vehicle in enumerate(vehicles):
        entities.append(CupraClimateSwitch(we_connect, coordinator, idx))
        entities.append(CupraChargingSwitch(we_connect, coordinator, idx))

    async_add_entities(entities, update_before_add=False)
    return True


class _CupraBase(CoordinatorEntity, SwitchEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, we_connect: weconnect_cupra.WeConnect, coordinator, index: int):
        super().__init__(coordinator)
        self.we_connect = we_connect
        self.index = index

        v = self.data  # Shortcut
        vin = getattr(v.vin, "value", str(v.vin))

        self._vin = vin
        self._nickname = getattr(v, "nickname", vin)
        self._model = getattr(v, "model", None)

        # WICHTIG: identisch zu deinen anderen Entitäten
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"vw{vin}")},
            manufacturer="CUPRA",
            model=self._model,
            name=self._nickname,
        )

    @property
    def data(self):
        # Vehicle-Objekt aus dem Coordinator nach Index
        return self.coordinator.data[self.index]


class CupraClimateSwitch(_CupraBase):
    """Ein/Aus für Klimatisierung."""

    def __init__(self, we_connect, coordinator, index: int):
        super().__init__(we_connect, coordinator, index)
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
            return str(state).lower() not in ("off","aus", "false", "inactive", "stopped", "0", "")
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
        await self.hass.async_add_executor_job(
            set_climatisation,
            self._vin,
            self.we_connect,
            "start",
            0,  # oder Zieltemp, wenn du magst
        )
        # Optional optimistisch:
        # self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(
            set_climatisation,
            self._vin,
            self.we_connect,
            "stop",
            0,
        )
        # Optional optimistisch:
        # self.async_write_ha_state()


class CupraChargingSwitch(_CupraBase):
    """Ein/Aus für Ladevorgang."""

    def __init__(self, we_connect, coordinator, index: int):
        super().__init__(we_connect, coordinator, index)
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
        await self.hass.async_add_executor_job(
            start_stop_charging,
            self._vin,
            self.we_connect,
            "start",
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(
            start_stop_charging,
            self._vin,
            self.we_connect,
            "stop",
        )
