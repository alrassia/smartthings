"""Support for binary sensors through the SmartThings cloud API."""

from __future__ import annotations

from collections.abc import Sequence

from pysmartthings import Attribute, Capability

import asyncio

import json

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.smartthings import _LOGGER

from .const import DATA_BROKERS, DOMAIN
from .utils import format_component_name, get_device_attributes, get_device_status
from .entity import SmartThingsEntity

CAPABILITY_TO_ATTRIB = {
    Capability.acceleration_sensor: Attribute.acceleration,
    Capability.contact_sensor: Attribute.contact,
    Capability.filter_status: Attribute.filter_status,
    Capability.motion_sensor: Attribute.motion,
    Capability.presence_sensor: Attribute.presence,
    Capability.sound_sensor: Attribute.sound,
    Capability.switch: Attribute.power,
    Capability.tamper_alert: Attribute.tamper,
    Capability.valve: Attribute.valve,
    Capability.water_sensor: Attribute.water,
}

ATTRIB_TO_CLASS = {
    Attribute.acceleration: BinarySensorDeviceClass.MOVING,
    Attribute.contact: BinarySensorDeviceClass.OPENING,
    Attribute.filter_status: BinarySensorDeviceClass.PROBLEM,
    Attribute.motion: BinarySensorDeviceClass.MOTION,
    Attribute.presence: BinarySensorDeviceClass.PRESENCE,
    Attribute.power: BinarySensorDeviceClass.POWER,
    Attribute.sound: BinarySensorDeviceClass.SOUND,
    Attribute.tamper: BinarySensorDeviceClass.PROBLEM,
    Attribute.valve: BinarySensorDeviceClass.OPENING,
    Attribute.water: BinarySensorDeviceClass.MOISTURE,
    Attribute.door: BinarySensorDeviceClass.DOOR,
}

ATTRIB_TO_ENTITY_CATEGORY = {
    Attribute.tamper: EntityCategory.DIAGNOSTIC,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary sensors for a config entry."""
    broker = hass.data[DOMAIN][DATA_BROKERS][config_entry.entry_id]
    sensors = []

    for device in broker.devices.values():
        capabilities = broker.get_assigned(device.device_id, Platform.BINARY_SENSOR)
        device_components = get_device_attributes(device)

        for component_id in list(device_components.keys()):
            attributes = device_components[component_id]

            for capability in capabilities:
                attrib = CAPABILITY_TO_ATTRIB[capability]

                if attributes is None or attrib in attributes:
                    sensors.append(
                        SmartThingsBinarySensor(device, attrib, component_id)
                    )

        if (
            device.status.attributes[Attribute.mnmn].value == "Samsung Electronics"
            and device.type == "OCF"
        ):
            model = device.status.attributes[Attribute.mnmo].value
            model = model.split("|")[0]
            if model in ("TP2X_DA-KS-RANGE-0101X",):
                sensors.extend(
                    [
                        SamsungCooktopBurner(device, "Cooktop Bottom Left Burner", 1),
                        SamsungCooktopBurner(device, "Cooktop Top Left Burner", 2),
                        SamsungCooktopBurner(device, "Cooktop Top Right Burner", 8),
                        SamsungCooktopBurner(device, "Cooktop Bottom Right", 16),
                    ]
                )

            elif model in ("21K_REF_LCD_FHUB6.0", "ARTIK051_REF_17K" ):
                """", "TP2X_REF_20K" """
                sensors.extend(
                    [
                        SamsungOcfDoorBinarySensor(
                            device,
                            "Cooler Door",
                            "/door/cooler/0",
                            "Open",
                            "Closed",
                            BinarySensorDeviceClass.DOOR,
                        ),
                        SamsungOcfDoorBinarySensor(
                            device,
                            "Freezer Door",
                            "/door/freezer/0",
                            "Open",
                            "Closed",
                            BinarySensorDeviceClass.DOOR,
                        ),
                        SamsungOcfDoorBinarySensor(
                            device,
                            "FlexZone Door",
                            "/door/cvroom/0",
                            "Open",
                            "Closed",
                            BinarySensorDeviceClass.DOOR,
                        ),
                    ]
                )

    async_add_entities(sensors)


def get_capabilities(capabilities: Sequence[str]) -> Sequence[str] | None:
    """Return all capabilities supported if minimum required are present."""
    return [
        capability for capability in CAPABILITY_TO_ATTRIB if capability in capabilities
    ]


class SmartThingsBinarySensor(SmartThingsEntity, BinarySensorEntity):
    """Define a SmartThings Binary Sensor."""

    def __init__(self, device, attribute, component_id: str | None = None) -> None:
        """Init the class."""
        super().__init__(device)
        self._attribute = attribute
        self._component_id = component_id

        self._attr_name = format_component_name(device.label, attribute, component_id)
        self._attr_unique_id = format_component_name(
            device.device_id, attribute, component_id, "."
        )
        self._attr_device_class = ATTRIB_TO_CLASS[attribute]
        self._attr_entity_category = ATTRIB_TO_ENTITY_CATEGORY.get(attribute)

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._attr_name}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._attr_unique_id}"
    
    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        status = get_device_status(self._device, self._component_id)
        _LOGGER.debug("status SmartThingsBinarySensor: %s of device %s", status, self._device._name)
        if status is None:
            return False
        return status
        
    @property
    def device_class(self):
        """Return the class of this device."""
        return ATTRIB_TO_CLASS[self._attribute]

    @property
    def entity_category(self):
        """Return the entity category of this device."""
        return ATTRIB_TO_ENTITY_CATEGORY.get(self._attribute)


class SamsungCooktopBurner(SmartThingsEntity, BinarySensorEntity):
    """Define Samsung Cooktop Burner Sensor"""

    execute_state = 0
    output_state = False
    init_bool = False

    def __init__(self, device, name, burner_bitmask):
        super().__init__(device)
        self._name = name
        self._burner_bitmask = burner_bitmask

    def startup(self):
        """Make sure that OCF page visits cooktopmonitoring on startup"""
        tasks = []
        tasks.append(self._device.execute("/cooktopmonitoring/vs/0"))
        asyncio.gather(*tasks)

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._device.label} {self._name}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        _unique_id = self._name.lower().replace(" ", "_")
        return f"{self._device.device_id}.{_unique_id}"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if not self.init_bool:
            self.startup()

        if (
            self._device.status.attributes[Attribute.data].data["href"]
            == "/cooktopmonitoring/vs/0"
        ):
            self.init_bool = True
            self.execute_state = int(
                self._device.status.attributes[Attribute.data].value["payload"][
                    "x.com.samsung.da.cooktopMonitoring"
                ]
            )
            if self.execute_state & self._burner_bitmask:
                self.output_state = True
            else:
                self.output_state = False
        return self.output_state

    @property
    def icon(self):
        if self.is_on:
            return "mdi:checkbox-blank-circle"
        return "mdi:checkbox-blank-circle-outline"


class SamsungOcfModeOptionsBinarySensor(SmartThingsEntity, BinarySensorEntity):
    """Define Samsung Cooktop Burner Sensor"""

    execute_state = False
    init_bool = False

    def __init__(
        self,
        device,
        name: str,
        on_value: str,
        off_value: str,
        device_class: str | None,
        on_icon: str | None,
        off_icon: str | None,
    ):
        super().__init__(device)
        self._name = name
        self._on_value = on_value
        self._off_value = off_value
        self._attr_device_class = device_class
        self._on_icon = on_icon
        self._off_icon = off_icon

    def startup(self):
        """Make sure that OCF page visits mode on startup"""
        tasks = []
        tasks.append(self._device.execute("/mode/vs/0"))
        asyncio.gather(*tasks)
        self.init_bool = True

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._device.label} {self._name}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        _unique_id = self._name.lower().replace(" ", "_")
        return f"{self._device.device_id}.{_unique_id}"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if not self.init_bool:
            self.startup()

        output = json.dumps(self._device.status.attributes[Attribute.data].value)

        if self._on_value in output:
            self.execute_state = True
        if self._off_value in output:
            self.execute_state = False
        return self.execute_state

    @property
    def icon(self):
        if self.is_on:
            return self._on_icon
        return self._off_icon


class SamsungOcfDoorBinarySensor(SmartThingsEntity, BinarySensorEntity):
    """Define Samsung Door Sensor"""

    execute_state = False
    init_bool = False

    def __init__(
        self,
        device,
        name: str,
        page: str,
        on_value: str,
        off_value: str,
        device_class: str | None,
    ):
        super().__init__(device)
        self._name = name
        self._page = page
        self._on_value = on_value
        self._off_value = off_value
        self._attr_device_class = device_class

    def startup(self):
        """Make sure that OCF page visits mode on startup"""
        tasks = []
        tasks.append(self._device.execute(self._page))
        asyncio.gather(*tasks)

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._device.label} {self._name}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        _unique_id = self._name.lower().replace(" ", "_")
        return f"{self._device.device_id}.{_unique_id}"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if not self.init_bool:
            self.startup()
        if self._device.status.attributes[Attribute.data].data["href"] == self._page:
            self.init_bool = True
            output = self._device.status.attributes[Attribute.data].value["payload"][
                "openState"
            ]
            if self._on_value in output:
                self.execute_state = True
            if self._off_value in output:
                self.execute_state = False
        return self.execute_state

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._attr_device_class