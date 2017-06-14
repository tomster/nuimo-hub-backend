import logging

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

from .dbus_bluez_interfaces import Advertisement, Application, BLUEZ_SERVICE_NAME, DBUS_OM_IFACE, DBUS_PROP_IFACE, \
    GATT_MANAGER_IFACE, LE_ADVERTISING_MANAGER_IFACE

logger = logging.getLogger(__name__)


class Peripheral(object):
    """
    This class can be used to create a Bluetooth LE GATT server using BlueZ.
    It manages the advertisement and included services and creates a mainloop for event handling.
    It also adjusts related settings of the bluetooth adapter (like the alias name and power state).
    """

    def __init__(self, alias, adapter=None):
        """
        Initializes this object and prepare the bluetooth adapter.
        :param alias: Alias name to be advertised
        :param adapter: bluetooth adapter to use
        """

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()

        if not adapter:
            adapter = self._find_adapter()
            if not adapter:
                logger.error("Could not find any adapter implementing GattManager1 + LEAdvertisingManager1 interfaces")
                raise BleNotSupportedException(
                    "No adapter implementing GattManager1 + LEAdvertisingManager1 found")
        self._adapter_path = '/org/bluez/' + adapter
        self._device_properties_changed_signal = None
        self._adapter_properties_changed_signal = None
        self._main_loop = None

        self._adapter_props = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path), DBUS_PROP_IFACE)

        logger.info("Creating BLE Peripheral with alias: %s" % alias)

        self.alias = alias
        self.is_powered = True
        self.is_discoverable = True
        self.discoverable_timeout = 0

        # Prepare Managers:

        self._ad_manager = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path),
            LE_ADVERTISING_MANAGER_IFACE)

        self._gatt_manager = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path),
            GATT_MANAGER_IFACE)

        # Create Advertisement and GATT Application:

        self._advertisement = Advertisement(self.bus, 0, 'peripheral')
        self._app = Application(self.bus)

    def run(self):
        """
        Registers advertisement and services to D-Bus and starts the main loop.
        """
        if self._main_loop:
            return
        self._main_loop = GObject.MainLoop()
        self._disconnect_all()
        self._register()
        logger.info("--- Mainloop started ---")
        try:
            self._main_loop.run()
        except KeyboardInterrupt:
            # ignore exception as it is a valid way to exit the program
            # and skip to finally clause
            pass
        except Exception as e:
            logger.error(e)
        finally:
            logger.info("--- Mainloop finished ---")
            self._unregister()
            self._main_loop.quit()
            self._main_loop = None

    def stop(self):
        """
        Stops the main loop started with `run()`
        """
        if self._main_loop:
            self._main_loop.quit()

    def add_service(self, service):
        self._app.add_service(service)

    def add_advertised_service_uuid(self, uuid):
        self._advertisement.add_service_uuid(uuid)

    def _find_adapter(self):
        """
        Tries to find a bluetooth adapter with the required functions.
        :return: path to an adapter or None
        """
        required_interfaces = [GATT_MANAGER_IFACE, LE_ADVERTISING_MANAGER_IFACE]
        object_manager = dbus.Interface(self.bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
        objects = object_manager.GetManagedObjects()

        for object_path, properties in objects.items():
            missing_interfaces = [i for i in required_interfaces if i not in properties.keys()]
            if missing_interfaces:
                continue
            return object_path.rsplit('/', 1)[1]

        return None

    def _disconnect_all(self):
        object_manager = dbus.Interface(self.bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
        objects = object_manager.GetManagedObjects()

        for object_path, properties in objects.items():
            if 'org.bluez.Device1' in properties.keys():
                if properties['org.bluez.Device1'].get('Connected', False):
                    logging.info("Disconnecting from device: %s" % properties['org.bluez.Device1'].get('Name', "unknown"))
                    device = dbus.Interface(
                        self.bus.get_object(BLUEZ_SERVICE_NAME, object_path), 'org.bluez.Device1')
                    device.Disconnect()

    @property
    def alias(self):
        return self._adapter_props.Get('org.bluez.Adapter1', 'Alias')

    @alias.setter
    def alias(self, value):
        self._adapter_props.Set('org.bluez.Adapter1', 'Alias', value)

    @property
    def is_discoverable(self):
        return self._adapter_props.Get('org.bluez.Adapter1', 'Discoverable') == 1

    @is_discoverable.setter
    def is_discoverable(self, value):
        self._adapter_props.Set('org.bluez.Adapter1', 'Discoverable', dbus.Boolean(value))

    @property
    def discoverable_timeout(self):
        return self._adapter_props.Get('org.bluez.Adapter1', 'DiscoverableTimeout')

    @discoverable_timeout.setter
    def discoverable_timeout(self, value):
        self._adapter_props.Set('org.bluez.Adapter1', 'DiscoverableTimeout', dbus.UInt32(value))

    @property
    def is_powered(self):
        return self._adapter_props.Get('org.bluez.Adapter1', 'Powered') == 1

    @is_powered.setter
    def is_powered(self, value):
        self._adapter_props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(value))

    @property
    def is_connected(self):
        return self._adapter_props.Get('org.bluez.Device1', 'Connected') == 1

    def _device_properties_changed(self, interface, changed_props, invalidated, path):
        """
        Used to detect if the remote device disconnected.
        In this case it calls the remote_disconnected() method of all services.
        """
        if 'Connected' in changed_props.keys():
            if not changed_props['Connected']:
                logger.info("Remote device was disconnected.")
                for service in self._app.services:
                    service.remote_disconnected()

    def _adapter_properties_changed(self, interface, changed_props, invalidated, path):
        """
        Sets Powered and Discoverable adapter properties to True when they were changed.
        """
        if 'Discoverable' in changed_props.keys():
            if not self.is_discoverable:
                self.is_discoverable = True
        if 'Powered' in changed_props.keys():
            if not self.is_powered:
                self.is_powered = True
        if 'DiscoverableTimeout' in changed_props.keys():
            # DiscoverableTimeout = 0 means timeout is disabled
            if self.discoverable_timeout != 0:
                self.discoverable_timeout = 0

    def _register(self):
        logger.info('Registering Advertisement...')
        self._ad_manager.RegisterAdvertisement(
            self._advertisement.get_path(), {},
            reply_handler=lambda: logger.info("Advertisement registered"),
            error_handler=self._register_ad_error_cb)

        logger.info('Registering GATT application...')
        self._gatt_manager.RegisterApplication(
            self._app.get_path(), {},
            reply_handler=lambda: logger.info("GATT application registered"),
            error_handler=self._register_app_error_cb)

        self._device_properties_changed_signal = self.bus.add_signal_receiver(
            self._device_properties_changed,
            dbus_interface=dbus.PROPERTIES_IFACE,
            signal_name='PropertiesChanged',
            arg0='org.bluez.Device1',
            path_keyword='path')

        self._adapter_properties_changed_signal = self.bus.add_signal_receiver(
            self._adapter_properties_changed,
            dbus_interface=dbus.PROPERTIES_IFACE,
            signal_name='PropertiesChanged',
            arg0='org.bluez.Adapter1',
            path_keyword='path')

    def _register_app_error_cb(self, error):
        logger.error("Failed to register application: %s" % error)
        self._main_loop.quit()

    def _register_ad_error_cb(self, error):
        logger.error("Failed to register advertisement: %s" % error)
        logger.error("Make sure no device is connected before registering an advertisement!")
        self._main_loop.quit()

    def _unregister(self):
        self._device_properties_changed_signal.remove()
        self._adapter_properties_changed_signal.remove()
        try:
            self._ad_manager.UnregisterAdvertisement(self._advertisement.get_path())
        except dbus.exceptions.DBusException:
            logger.warning("Couldn't unregister advertisement, maybe it wasn't created.")
        try:
            self._gatt_manager.UnregisterApplication(self._app.get_path())
        except dbus.exceptions.DBusException:
            logger.warning("Couldn't unregister application, maybe it wasn't created.")
        logger.info("Peripheral unregistered")


class BleNotSupportedException(Exception):
    """ 
    Raised when a required Bluetooth Low Energy function is not
    supported by the system.
    """
    pass
