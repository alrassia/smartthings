"""Support for binary sensors through the SmartThings cloud API."""

from __future__ import annotations

from collections.abc import Sequence

from pysmartthings import Attribute, Capability

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartThingsEntity
from .const import DATA_BROKERS, DOMAIN

CAPABILITY_TO_ATTRIB = {
    Capability.acceleration_sensor: Attribute.acceleration,
    Capability.contact_sensor: Attribute.contact,
    Capability.filter_status: Attribute.filter_status,
    Capability.motion_sensor: Attribute.motion,
    Capability.presence_sensor: Attribute.presence,
    Capability.sound_sensor: Attribute.sound,
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
    Attribute.sound: BinarySensorDeviceClass.SOUND,
    Attribute.tamper: BinarySensorDeviceClass.PROBLEM,
    Attribute.valve: BinarySensorDeviceClass.OPENING,
    Attribute.water: BinarySensorDeviceClass.MOISTURE,
}
ATTRIB_TO_ENTTIY_CATEGORY = {
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
        for capability in broker.get_assigned(device.device_id, "binary_sensor"):
            attrib = CAPABILITY_TO_ATTRIB[capability]
            sensors.append(SmartThingsBinarySensor(device, attrib))
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
            elif model in ("21K_REF_LCD_FHUB6.0", "ARTIK051_REF_17K"):
                sensors.extend(
                    [
                        SamsungOcfDoorBinarySensor(
                            device,
                            "Cooler Door",
                            "/door/cooler/0",
                            "Open",
                            "Closed",
                            DEVICE_CLASS_DOOR,
                        ),
                        SamsungOcfDoorBinarySensor(
                            device,
                            "Freezer Door",
                            "/door/freezer/0",
                            "Open",
                            "Closed",
                            DEVICE_CLASS_DOOR,
                        ),
                        SamsungOcfDoorBinarySensor(
                            device,
                            "FlexZone Door",
                            "/door/cvroom/0",
                            "Open",
                            "Closed",
                            DEVICE_CLASS_DOOR,
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

    def __init__(self, device, attribute):
        """Init the class."""
        super().__init__(device)
        self._attribute = attribute
        self._attr_name = f"{device.label} {attribute}"
        self._attr_unique_id = f"{device.device_id}.{attribute}"
        self._attr_device_class = ATTRIB_TO_CLASS[attribute]
        self._attr_entity_category = ATTRIB_TO_ENTTIY_CATEGORY.get(attribute)

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._device.status.is_on(self._attribute)
