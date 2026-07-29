#!/usr/bin/env python3
"""Tests for the serial/bluetooth transport abstraction.

These exercise the transport-agnostic plumbing added to unify the master
(pyserial) and feature/RFCOMM (bluetooth) branches: the SerialTransport
adapter that maps the socket API onto pyserial, and the discovery dispatch.
No GTK, no hardware.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock GTK and the optional transport libraries before importing TncModel.
sys.modules['gi'] = MagicMock()
sys.modules['gi.repository'] = MagicMock()
sys.modules['bluetooth'] = MagicMock()
sys.modules['serial'] = MagicMock()
sys.modules['serial.tools'] = MagicMock()
sys.modules['serial.tools.list_ports'] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import TncModel
from TncModel import SerialTransport, TncModel as TncModelClass


class TestSerialTransport(unittest.TestCase):
    """SerialTransport must expose the socket API over a pyserial object."""

    def setUp(self):
        self.fake_ser = MagicMock()
        self.transport = SerialTransport(self.fake_ser)

    def test_send_maps_to_write(self):
        self.transport.send(b'\xc0\x01\xc0')
        self.fake_ser.write.assert_called_once_with(b'\xc0\x01\xc0')

    def test_recv_maps_to_read(self):
        self.fake_ser.read.return_value = b'\xc0\x01'
        result = self.transport.recv(160)
        self.fake_ser.read.assert_called_once_with(160)
        self.assertEqual(result, b'\xc0\x01')

    def test_close_maps_to_close(self):
        self.transport.close()
        self.fake_ser.close.assert_called_once_with()

    def test_send_returns_write_count(self):
        self.fake_ser.write.return_value = 3
        self.assertEqual(self.transport.send(b'abc'), 3)


class TestDiscoveryDispatch(unittest.TestCase):
    """available_devices() must route to the right backend by transport."""

    def _with_fake_serial(self, ports):
        """Run serial discovery against a fake pyserial module.

        When pyserial is absent at import time, TncModel.serial is never
        bound, so we inject a fake module and restore state afterwards.
        Returns the discovered device list.
        """
        fake_serial = MagicMock()
        fake_serial.tools.list_ports.comports.return_value = ports
        had_serial = getattr(TncModel, 'serial', None)
        had_flag = TncModel.HAVE_SERIAL
        TncModel.serial = fake_serial
        TncModel.HAVE_SERIAL = True
        try:
            return TncModel.available_devices('serial')
        finally:
            TncModel.HAVE_SERIAL = had_flag
            if had_serial is None:
                del TncModel.serial
            else:
                TncModel.serial = had_serial

    def test_serial_dispatch(self):
        devices = self._with_fake_serial(
            [MagicMock(device='/dev/ttyUSB0', description='TNC')])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]['host'], '/dev/ttyUSB0')
        self.assertEqual(devices[0]['name'], 'TNC')
        self.assertEqual(devices[0]['port'], 0)

    def test_serial_filters_out_legacy_uarts(self):
        # Only USB serial adapters (ttyUSB*/ttyACM*) should be listed.
        # Legacy PC UARTs (ttyS*) are never used for a TNC.
        devices = self._with_fake_serial([
            MagicMock(device='/dev/ttyUSB0', description='FT232'),
            MagicMock(device='/dev/ttyACM0', description='STM32 CDC'),
            MagicMock(device='/dev/ttyS0', description='16550A'),
            MagicMock(device='/dev/ttyS1', description='16550A'),
        ])
        hosts = [d['host'] for d in devices]
        self.assertEqual(hosts, ['/dev/ttyUSB0', '/dev/ttyACM0'])

    def test_serial_missing_returns_empty(self):
        with patch.object(TncModel, 'HAVE_SERIAL', False):
            self.assertEqual(TncModel.available_devices('serial'), [])

    def test_bluetooth_missing_returns_empty(self):
        with patch.object(TncModel, 'HAVE_BLUETOOTH', False):
            self.assertEqual(TncModel.available_devices('bluetooth'), [])

    def test_default_is_bluetooth(self):
        with patch.object(TncModel, 'HAVE_BLUETOOTH', False):
            # default arg routes to bluetooth backend
            self.assertEqual(TncModel.available_devices(), [])


class TestTncModelTransport(unittest.TestCase):
    """TncModel must record the selected transport."""

    def test_default_transport_is_bluetooth(self):
        app = MagicMock()
        tnc = TncModelClass(app, {'host': 'AA:BB', 'port': 1})
        self.assertEqual(tnc.transport, 'bluetooth')

    def test_serial_transport_recorded(self):
        app = MagicMock()
        tnc = TncModelClass(app, {'host': '/dev/ttyUSB0', 'port': 0},
                            transport='serial')
        self.assertEqual(tnc.transport, 'serial')


if __name__ == '__main__':
    unittest.main()
