#!/usr/bin/env python3
"""
Unit tests for TncModel digipeater and beacon protocol handling.

Tests the KISS encode/decode round-trip for the new extended commands
(digipeater settings, aliases, beacons) without requiring GTK or Bluetooth.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from io import BytesIO

# Mock the GTK and Bluetooth imports before importing TncModel
sys.modules['gi'] = MagicMock()
sys.modules['gi.repository'] = MagicMock()
sys.modules['bluetooth'] = MagicMock()

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from TncModel import KissEncode, KissDecode, KissData, TncModel, decode_call_t, encode_call_t


class TestKissEncodeDecode(unittest.TestCase):
    """Test KISS encoding and decoding of digipeater/beacon commands."""

    def setUp(self):
        self.encoder = KissEncode()
        self.decoder = KissDecode()

    def _round_trip(self, raw_data):
        """Encode raw data in KISS framing, then decode it back."""
        encoded = self.encoder.encode(raw_data)
        packet = None
        for c in encoded:
            result = self.decoder.process(c)
            if result is not None:
                packet = result
        return packet

    def test_encode_decode_digipeater_settings_response(self):
        """Decode an EXT_GET_DIGIPEATER response: [0x06, 0xC1, 0x8B, enabled, mode, dedupe]"""
        raw = bytes([0x06, 0xC1, 0x8B, 1, 0x40, 30])
        packet = self._round_trip(raw)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.packet_type, 0x06)
        self.assertEqual(packet.sub_type, 0xC1)
        # data[0] is the extended type (0x8B), rest is the payload
        self.assertEqual(packet.data[0], 0x8B)
        self.assertEqual(packet.data[1], 1)      # enabled
        self.assertEqual(packet.data[2], 0x40)  # routing_mode (SUBSTITUTE)
        self.assertEqual(packet.data[3], 30)     # dedupe_seconds

    def test_encode_decode_aliases_count_response(self):
        """Decode an EXT_GET_ALIASES response: [0x06, 0xC1, 0x88, count]"""
        raw = bytes([0x06, 0xC1, 0x88, 8])
        packet = self._round_trip(raw)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.sub_type, 0xC1)
        self.assertEqual(packet.data[0], 0x88)
        self.assertEqual(packet.data[1], 8)

    def test_encode_decode_beacon_slots_response(self):
        """Decode an EXT_GET_BEACON_SLOTS response: [0x06, 0xC1, 0x8C, count]"""
        raw = bytes([0x06, 0xC1, 0x8C, 4])
        packet = self._round_trip(raw)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.sub_type, 0xC1)
        self.assertEqual(packet.data[0], 0x8C)
        self.assertEqual(packet.data[1], 4)

    def test_encode_decode_alias_response(self):
        """Decode an EXT_GET_ALIAS response with an SSID-bearing call_t."""
        # [0x06, 0xC1, 0x89, index, call_t(8), set, use, hops]
        # call_t = [callsign[6] space-padded][pad=0][ssid]
        # "WIDE1" with ssid=1 -> callsign "WIDE1 " (space-padded), pad 0, ssid 1
        call_t = b'WIDE1 \x00\x01'
        raw = bytes([0x06, 0xC1, 0x89, 0]) + call_t + bytes([1, 1, 2])
        packet = self._round_trip(raw)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.data[0], 0x89)
        self.assertEqual(packet.data[1], 0)  # index
        # call_t is bytes 2..9 (after peeling ext type and index)
        self.assertEqual(packet.data[2:10], call_t)
        self.assertEqual(packet.data[10], 1)  # set
        self.assertEqual(packet.data[11], 1)  # use
        self.assertEqual(packet.data[12], 2)  # hops

    def test_encode_decode_beacon_response(self):
        """Decode an EXT_GET_BEACON response with NUL-terminated strings."""
        # [0x06, 0xC1, 0x8D, slot, interval_H, interval_L, dest\0, path\0, text\0]
        raw = bytes([0x06, 0xC1, 0x8D, 0, 0x07, 0x08])  # slot=0, interval=1800
        raw += b'APZ001\x00'
        raw += b'WIDE1-1,WIDE2-2\x00'
        raw += b'!5100.00N/12345.67W\x00'
        packet = self._round_trip(raw)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.data[0], 0x8D)
        self.assertEqual(packet.data[1], 0)  # slot
        interval = (packet.data[2] << 8) + packet.data[3]
        self.assertEqual(interval, 0x0708)  # 1800

    def test_encode_digipeater_set_command(self):
        """Encode a SET_DIGIPEATER command and verify the KISS frame."""
        raw = bytes([0x06, 0xC1, 0x8F, 1, 0x40, 30])
        encoded = self.encoder.encode(raw)
        # Should start and end with FEND (0xC0)
        self.assertEqual(encoded[0], 0xC0)
        self.assertEqual(encoded[-1], 0xC0)
        # Decode back to verify content
        packet = self._round_trip(raw)
        self.assertEqual(packet.packet_type, 0x06)
        self.assertEqual(packet.sub_type, 0xC1)
        self.assertEqual(packet.data[0], 0x8F)
        self.assertEqual(packet.data[1], 1)      # enabled
        self.assertEqual(packet.data[2], 0x40)  # routing_mode
        self.assertEqual(packet.data[3], 30)    # dedupe_seconds

    def test_encode_decode_with_fesc_escape(self):
        """Test that FEND (0xC0) in data is properly escaped."""
        # Data containing 0xC0 should be escaped as 0xDB 0xDC
        raw = bytes([0x06, 0xC1, 0x8F, 0xC0, 0x00, 30])
        encoded = self.encoder.encode(raw)
        # The encoder escapes 0xC0 as 0xDB 0xDC and 0xDB as 0xDB 0xDD
        # Check that the raw 0xC0 is not present between FEND delimiters
        inner = encoded[1:-1]
        self.assertNotIn(0xC0, inner)
        # Decode back to verify content is preserved
        packet = self._round_trip(raw)
        self.assertEqual(packet.data[0], 0x8F)
        self.assertEqual(packet.data[1], 0xC0)  # Should unescape back to 0xC0


class TestTncModelHandlers(unittest.TestCase):
    """Test TncModel response handler methods with mock app."""

    def setUp(self):
        self.mock_app = MagicMock()
        self.device = {'host': '00:11:22:33:44:55', 'port': 1}
        self.tnc = TncModel(self.mock_app, self.device)
        self.tnc.sio_writer = None  # Prevent attempts to send on disconnect

    def _make_packet(self, sub_type, data):
        """Create a KissData packet for testing."""
        packet = KissData()
        packet.packet_type = 0x06
        packet.sub_type = sub_type
        packet.data = bytearray(data)
        packet.ready = True
        return packet

    def test_handle_get_aliases(self):
        """Test that handle_get_aliases calls app.tnc_digipeater_supported."""
        packet = self._make_packet(0xC1, bytes([0x88, 8]))
        self.tnc.handle_extended_range_1(packet)
        self.assertEqual(self.tnc.alias_count, 8)
        self.mock_app.tnc_digipeater_supported.assert_called_once_with(8)

    def test_handle_get_beacon_slots(self):
        """Test that handle_get_beacon_slots calls app.tnc_beacon_supported."""
        packet = self._make_packet(0xC1, bytes([0x8C, 4]))
        self.tnc.handle_extended_range_1(packet)
        self.assertEqual(self.tnc.beacon_count, 4)
        self.mock_app.tnc_beacon_supported.assert_called_once_with(4)

    def test_handle_get_digipeater(self):
        """Test that handle_get_digipeater calls app.tnc_digipeater_settings."""
        packet = self._make_packet(0xC1, bytes([0x8B, 1, 0x40, 30]))
        self.tnc.handle_extended_range_1(packet)
        self.mock_app.tnc_digipeater_settings.assert_called_once_with(1, 0x40, 30)

    def test_handle_get_alias(self):
        """Test that handle_get_alias parses call_t (with SSID) correctly."""
        # call_t for "WIDE1" ssid=1: callsign "WIDE1 " (space-padded), pad 0, ssid 1
        call_t = b'WIDE1 \x00\x01'
        data = bytes([0x89, 0]) + call_t + bytes([1, 1, 2])
        packet = self._make_packet(0xC1, data)
        self.tnc.handle_extended_range_1(packet)
        self.mock_app.tnc_alias.assert_called_once_with(0, 'WIDE1-1', 1, 1, 2)

    def test_handle_get_alias_no_ssid(self):
        """call_t with ssid=0 renders without a dash."""
        call_t = b'WIDE2 \x00\x00'
        data = bytes([0x89, 3]) + call_t + bytes([1, 0, 2])
        packet = self._make_packet(0xC1, data)
        self.tnc.handle_extended_range_1(packet)
        self.mock_app.tnc_alias.assert_called_once_with(3, 'WIDE2', 1, 0, 2)

    def test_handle_get_beacon(self):
        """Test that handle_get_beacon calls app.tnc_beacon with parsed values."""
        data = bytes([0x8D, 0, 0x07, 0x08])  # slot=0, interval=1800
        data += b'APZ001\x00WIDE1-1\x00!5100.00N/12345.67W\x00'
        packet = self._make_packet(0xC1, data)
        self.tnc.handle_extended_range_1(packet)
        self.mock_app.tnc_beacon.assert_called_once()
        call_args = self.mock_app.tnc_beacon.call_args[0]
        self.assertEqual(call_args[0], 0)      # slot
        self.assertEqual(call_args[1], 0x0708) # interval
        self.assertEqual(call_args[2], 'APZ001')
        self.assertEqual(call_args[3], 'WIDE1-1')
        self.assertEqual(call_args[4], '!5100.00N/12345.67W')

    def test_routing_mode_constants(self):
        """Verify routing mode flag constants."""
        self.assertEqual(TncModel.ROUTING_PREEMPT_FRONT, 0x01)
        self.assertEqual(TncModel.ROUTING_PREEMPT_TRUNCATE, 0x02)
        self.assertEqual(TncModel.ROUTING_PREEMPT_DROP, 0x04)
        self.assertEqual(TncModel.ROUTING_PREEMPT_MARK, 0x08)
        self.assertEqual(TncModel.ROUTING_SUBSTITUTE, 0x40)
        self.assertEqual(TncModel.ROUTING_SKIP_COMPLETE, 0x80)

    def test_extended_command_constants(self):
        """Verify extended command sub-type constants."""
        self.assertEqual(TncModel.HANDLE_EXT1_GET_ALIASES, 0x88)
        self.assertEqual(TncModel.HANDLE_EXT1_GET_ALIAS, 0x89)
        self.assertEqual(TncModel.HANDLE_EXT1_SET_ALIAS, 0x8A)
        self.assertEqual(TncModel.HANDLE_EXT1_GET_DIGIPEATER, 0x8B)
        self.assertEqual(TncModel.HANDLE_EXT1_GET_BEACON_SLOTS, 0x8C)
        self.assertEqual(TncModel.HANDLE_EXT1_GET_BEACON, 0x8D)
        self.assertEqual(TncModel.HANDLE_EXT1_SET_BEACON, 0x8E)
        self.assertEqual(TncModel.HANDLE_EXT1_SET_DIGIPEATER, 0x8F)


class TestCallTCodec(unittest.TestCase):
    """Test call_t encode/decode against the firmware 8-byte wire layout:
    [callsign[6] space-padded][pad=0][ssid]."""

    def test_encode_with_ssid(self):
        self.assertEqual(encode_call_t("WIDE1-1"), b'WIDE1 \x00\x01')

    def test_encode_no_ssid(self):
        self.assertEqual(encode_call_t("WIDE2"), b'WIDE2 \x00\x00')

    def test_encode_full_length(self):
        # 6-char callsign, no padding needed
        self.assertEqual(encode_call_t("ABCDEF-5"), b'ABCDEF\x00\x05')

    def test_encode_ssid_clamped(self):
        # SSID above 15 is clamped to 15
        self.assertEqual(encode_call_t("WIDE1-99"), b'WIDE1 \x00\x0f')

    def test_decode_with_ssid(self):
        self.assertEqual(decode_call_t(b'WIDE1 \x00\x01'), "WIDE1-1")

    def test_decode_no_ssid(self):
        self.assertEqual(decode_call_t(b'WIDE2 \x00\x00'), "WIDE2")

    def test_decode_strips_space_padding(self):
        self.assertEqual(decode_call_t(b'WIDE  \x00\x02'), "WIDE-2")

    def test_round_trip(self):
        for call in ["WIDE1-1", "WIDE2", "WX9O-1", "RELAY", "ECHO-15"]:
            self.assertEqual(decode_call_t(encode_call_t(call)), call)


if __name__ == '__main__':
    unittest.main()