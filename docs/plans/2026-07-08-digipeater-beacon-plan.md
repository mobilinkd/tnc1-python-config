# PLAN: Config App Digipeater & Beacon Support

## Goal

Add digipeater and beacon configuration UI to the `tnc1-python-config` app
(feature/RFCOMM branch) to support the TNC4 digipeater feature.

## Context

- **Branch:** feature/RFCOMM (Python 3, GTK3, Bluetooth RFCOMM sockets)
- **Firmware:** tnc4-firmware feature/digipeater-integration
- **Firmware requirements:** see `tnc4-firmware/docs/config-app-requirements.md`

The firmware already has KISS extended commands for digipeater and beacon
config (0xC1 0x88 through 0xC1 0x8F).  The firmware will be updated to include
EXT_GET_ALIASES, EXT_GET_BEACON_SLOTS, and EXT_GET_DIGIPEATER in the
GET_ALL_VALUES response stream.  The presence of these responses tells the
config app that the features are supported.

## Architecture

The app follows a consistent MVC pattern:

1. **TncModel.py** -- KISS protocol layer.  Encodes commands, decodes responses,
   dispatches to `app.tnc_*()` callbacks via `GLib.idle_add`.
2. **TncConfigApp.py** -- GTK UI layer.  Initializes frames from Glade, wires
   signal handlers, receives `tnc_*()` callbacks to update widgets.
3. **glade/TncConfigApp.glade** -- UI layout.  GtkStack pages in config_stack.

Each feature follows this pattern:
- Frame starts hidden (`set_visible(False)`)
- A `tnc_*_supported()` callback makes it visible when the firmware reports
  support during GET_ALL_VALUES
- `init_*_frame()` grabs widget references from the builder
- `on_*_enter()` / `on_*_leave()` handle stack page transitions
- Signal handlers call `self.tnc.set_*()` methods
- `tnc_*()` callback methods update widgets from firmware responses

## Changes

### Phase 1: TncModel.py -- Protocol Layer

#### 1.1 Add extended command constants

Add to the TncModel class constants block (near line 249):

```python
# Extended command sub-types (0xC1 prefix)
HANDLE_EXT1_GET_ALIASES = 0x88
HANDLE_EXT1_GET_ALIAS = 0x89
HANDLE_EXT1_SET_ALIAS = 0x8A
HANDLE_EXT1_GET_DIGIPEATER = 0x8B
HANDLE_EXT1_GET_BEACON_SLOTS = 0x8C
HANDLE_EXT1_GET_BEACON = 0x8D
HANDLE_EXT1_SET_BEACON = 0x8E
HANDLE_EXT1_SET_DIGIPEATER = 0x8F

# Routing mode flags
ROUTING_PREEMPT_FRONT    = 0x01
ROUTING_PREEMPT_TRUNCATE = 0x02
ROUTING_PREEMPT_DROP     = 0x04
ROUTING_PREEMPT_MARK     = 0x08
ROUTING_SUBSTITUTE       = 0x40
ROUTING_SKIP_COMPLETE    = 0x80
```

#### 1.2 Extend handle_extended_range_1 dispatch

In `handle_extended_range_1()` (line 431), add dispatch for the new sub-types:

```python
def handle_extended_range_1(self, packet):
    extended_type = packet.data[0]
    packet.data = packet.data[1:]
    if extended_type == self.HANDLE_EXT1_SELECTED_MODEM_TYPE:
        self.handle_selected_modem_type(packet)
    elif extended_type == self.HANDLE_EXT1_SUPPORTED_MODEM_TYPES:
        self.handle_supported_modem_types(packet)
    elif extended_type == self.HANDLE_EXT1_GET_ALIASES:
        self.handle_get_aliases(packet)
    elif extended_type == self.HANDLE_EXT1_GET_ALIAS:
        self.handle_get_alias(packet)
    elif extended_type == self.HANDLE_EXT1_GET_DIGIPEATER:
        self.handle_get_digipeater(packet)
    elif extended_type == self.HANDLE_EXT1_GET_BEACON_SLOTS:
        self.handle_get_beacon_slots(packet)
    elif extended_type == self.HANDLE_EXT1_GET_BEACON:
        self.handle_get_beacon(packet)
    else:
        pass  # Unknown extended type
```

#### 1.3 Add response handlers

```python
def handle_get_aliases(self, packet):
    # packet.data = [count]
    count = packet.data[0]
    self.app.tnc_digipeater_supported(count)

def handle_get_beacon_slots(self, packet):
    # packet.data = [count]
    count = packet.data[0]
    self.app.tnc_beacon_supported(count)

def handle_get_digipeater(self, packet):
    # packet.data = [enabled, routing_mode, dedupe_seconds]
    enabled = packet.data[0]
    routing_mode = packet.data[1]
    dedupe_seconds = packet.data[2]
    self.app.tnc_digipeater_settings(enabled, routing_mode, dedupe_seconds)

def handle_get_alias(self, packet):
    # packet.data = [index, call[0..7], set, use, hops]
    # Note: firmware reply_ext NUL-truncation bug may cause short data.
    # Handle variable-length data gracefully.
    index = packet.data[0]
    call = packet.data[1:9].rstrip(b'\x00').decode('ascii')
    set_flag = packet.data[9] if len(packet.data) > 9 else 0
    use_flag = packet.data[10] if len(packet.data) > 10 else 0
    hops = packet.data[11] if len(packet.data) > 11 else 0
    self.app.tnc_alias(index, call, set_flag, use_flag, hops)

def handle_get_beacon(self, packet):
    # packet.data = [slot, interval_H, interval_L, dest\0, path\0, text\0]
    slot = packet.data[0]
    interval = (packet.data[1] << 8) + packet.data[2]
    # Parse NUL-terminated strings starting at offset 3
    strings = packet.data[3:].split(b'\x00')
    dest = strings[0].decode('ascii') if len(strings) > 0 else ''
    path = strings[1].decode('ascii') if len(strings) > 1 else ''
    text = strings[2].decode('ascii') if len(strings) > 2 else ''
    self.app.tnc_beacon(slot, interval, dest, path, text)
```

#### 1.4 Add command methods

```python
def set_digipeater(self, enabled, routing_mode, dedupe_seconds):
    if self.sio_writer is None: return
    try:
        data = bytes(pack('>BBB', enabled, routing_mode, dedupe_seconds))
        cmd = bytes([0xC1, 0x8F]) + data
        self.sio_writer.send(self.encoder.encode(cmd))
    except Exception as e:
        self.app.exception(e)

def set_alias(self, index, call, set_flag, use_flag, hops):
    if self.sio_writer is None: return
    try:
        call_bytes = call.ljust(8, '\x00').encode('ascii')[:8]
        data = bytes([index]) + call_bytes + bytes(pack('>BBB', set_flag, use_flag, hops))
        cmd = bytes([0xC1, 0x8A]) + data
        self.sio_writer.send(self.encoder.encode(cmd))
    except Exception as e:
        self.app.exception(e)

def set_beacon(self, slot, interval, dest, path, text):
    if self.sio_writer is None: return
    try:
        data = bytes([slot])
        data += pack('>H', interval)
        data += dest.encode('ascii') + b'\x00'
        data += path.encode('ascii') + b'\x00'
        data += text.encode('ascii') + b'\x00'
        cmd = bytes([0xC1, 0x8E]) + data
        self.sio_writer.send(self.encoder.encode(cmd))
    except Exception as e:
        self.app.exception(e)

def get_all_aliases(self):
    """Fetch all aliases from the device.  Called after connect."""
    if self.sio_writer is None: return
    for i in range(self.alias_count):
        cmd = bytes([0xC1, 0x89, i])
        self.sio_writer.send(self.encoder.encode(cmd))

def get_all_beacons(self):
    """Fetch all beacons from the device.  Called after connect."""
    if self.sio_writer is None: return
    for i in range(self.beacon_count):
        cmd = bytes([0xC1, 0x8D, i])
        self.sio_writer.send(self.encoder.encode(cmd))
```

#### 1.5 Track alias/beacon counts

In `__init__` (line 262), add:

```python
self.alias_count = 0
self.beacon_count = 0
```

Update `handle_get_aliases` and `handle_get_beacon_slots` to store the counts,
then trigger the bulk fetch of individual aliases/beacons:

```python
def handle_get_aliases(self, packet):
    self.alias_count = packet.data[0]
    self.app.tnc_digipeater_supported(self.alias_count)
    if self.alias_count > 0:
        self.get_all_aliases()

def handle_get_beacon_slots(self, packet):
    self.beacon_count = packet.data[0]
    self.app.tnc_beacon_supported(self.beacon_count)
    if self.beacon_count > 0:
        self.get_all_beacons()
```

### Phase 2: TncConfigApp.py -- UI Layer

#### 2.1 Add init_digipeater_frame()

Grab widget references for the digipeater page.  Frame starts hidden.

```python
def init_digipeater_frame(self):
    self.digipeater_frame = self.builder.get_object("digipeater_frame")
    self.digipeater_frame.set_visible(False)

    self.digipeater_enable_check_button = self.builder.get_object(
        "digipeater_enable_check_button")
    self.dedupe_seconds_spin_button = self.builder.get_object(
        "dedupe_seconds_spin_button")

    # Routing mode check buttons
    self.substitute_check_button = self.builder.get_object(
        "substitute_check_button")
    self.skip_complete_check_button = self.builder.get_object(
        "skip_complete_check_button")
    self.preempt_front_check_button = self.builder.get_object(
        "preempt_front_check_button")
    self.preempt_truncate_check_button = self.builder.get_object(
        "preempt_truncate_check_button")
    self.preempt_drop_check_button = self.builder.get_object(
        "preempt_drop_check_button")
    self.preempt_mark_check_button = self.builder.get_object(
        "preempt_mark_check_button")

    # Alias table (GtkListBox)
    self.alias_list_box = self.builder.get_object("alias_list_box")
```

#### 2.2 Add init_beacon_frame()

```python
def init_beacon_frame(self):
    self.beacon_frame = self.builder.get_object("beacon_frame")
    self.beacon_frame.set_visible(False)
    # 4 beacon slots, each with enable, interval, dest, path, text
    self.beacon_widgets = []
    for i in range(4):
        prefix = f"beacon{i}_"
        self.beacon_widgets.append({
            'enable': self.builder.get_object(f"{prefix}enable_check_button"),
            'interval': self.builder.get_object(f"{prefix}interval_spin_button"),
            'dest': self.builder.get_object(f"{prefix}dest_entry"),
            'path': self.builder.get_object(f"{prefix}path_entry"),
            'text': self.builder.get_object(f"{prefix}text_entry"),
        })
```

#### 2.3 Add signal handlers

```python
### Digipeater
def on_digipeater_enter(self):
    pass

def on_digipeater_leave(self):
    pass

def on_digipeater_enable_check_button_toggled(self, widget):
    self.update_digipeater_settings()

def on_dedupe_seconds_spin_button_value_changed(self, widget):
    self.update_digipeater_settings()

def on_substitute_check_button_toggled(self, widget):
    self.update_digipeater_settings()

def on_skip_complete_check_button_toggled(self, widget):
    self.update_digipeater_settings()

def on_preempt_front_check_button_toggled(self, widget):
    self.update_digipeater_settings()

def on_preempt_truncate_check_button_toggled(self, widget):
    self.update_digipeater_settings()

def on_preempt_drop_check_button_toggled(self, widget):
    self.update_digipeater_settings()

def on_preempt_mark_check_button_toggled(self, widget):
    self.update_digipeater_settings()

def update_digipeater_settings(self):
    if self.tnc is None: return
    enabled = 1 if self.digipeater_enable_check_button.get_active() else 0
    routing_mode = 0
    if self.substitute_check_button.get_active():
        routing_mode |= self.tnc.ROUTING_SUBSTITUTE
    if self.skip_complete_check_button.get_active():
        routing_mode |= self.tnc.ROUTING_SKIP_COMPLETE
    if self.preempt_front_check_button.get_active():
        routing_mode |= self.tnc.ROUTING_PREEMPT_FRONT
    if self.preempt_truncate_check_button.get_active():
        routing_mode |= self.tnc.ROUTING_PREEMPT_TRUNCATE
    if self.preempt_drop_check_button.get_active():
        routing_mode |= self.tnc.ROUTING_PREEMPT_DROP
    if self.preempt_mark_check_button.get_active():
        routing_mode |= self.tnc.ROUTING_PREEMPT_MARK
    dedupe = int(self.dedupe_seconds_spin_button.get_value())
    self.tnc.set_digipeater(enabled, routing_mode, dedupe)
```

Alias row handlers -- each row has a callsign entry, use check, hops spin,
and set check.  Signal handlers update the alias on the device.

```python
def on_alias_set_button_clicked(self, widget, user_data):
    # user_data = alias index
    row = self.alias_rows[user_data]
    call = row['call_entry'].get_text()
    use = 1 if row['use_check'].get_active() else 0
    hops = int(row['hops_spin'].get_value())
    self.tnc.set_alias(user_data, call, 1, use, hops)
```

Beacon handlers:

```python
### Beacons
def on_beacon_enter(self):
    pass

def on_beacon_leave(self):
    pass

def on_beacon_apply_button_clicked(self, widget, user_data):
    # user_data = beacon slot
    w = self.beacon_widgets[user_data]
    interval = int(w['interval'].get_value())
    dest = w['dest'].get_text()
    path = w['path'].get_text()
    text = w['text'].get_text()
    self.tnc.set_beacon(user_data, interval, dest, path, text)
```

#### 2.4 Add tnc_* callback methods

```python
### Digipeater
def tnc_digipeater_supported(self, count):
    self.digipeater_frame.set_visible(True)
    self.digipeater_alias_count = count
    # Build alias table rows dynamically
    self.build_alias_table(count)

def tnc_digipeater_settings(self, enabled, routing_mode, dedupe_seconds):
    self.digipeater_enable_check_button.set_active(enabled != 0)
    self.substitute_check_button.set_active(
        bool(routing_mode & self.tnc.ROUTING_SUBSTITUTE))
    self.skip_complete_check_button.set_active(
        bool(routing_mode & self.tnc.ROUTING_SKIP_COMPLETE))
    self.preempt_front_check_button.set_active(
        bool(routing_mode & self.tnc.ROUTING_PREEMPT_FRONT))
    self.preempt_truncate_check_button.set_active(
        bool(routing_mode & self.tnc.ROUTING_PREEMPT_TRUNCATE))
    self.preempt_drop_check_button.set_active(
        bool(routing_mode & self.tnc.ROUTING_PREEMPT_DROP))
    self.preempt_mark_check_button.set_active(
        bool(routing_mode & self.tnc.ROUTING_PREEMPT_MARK))
    self.dedupe_seconds_spin_button.set_value(dedupe_seconds)

def tnc_alias(self, index, call, set_flag, use_flag, hops):
    if index < len(self.alias_rows):
        row = self.alias_rows[index]
        row['call_entry'].set_text(call)
        row['use_check'].set_active(use_flag != 0)
        row['hops_spin'].set_value(hops)
        row['set_label'].set_text("Yes" if set_flag else "No")

### Beacons
def tnc_beacon_supported(self, count):
    self.beacon_frame.set_visible(True)
    self.beacon_count = count

def tnc_beacon(self, slot, interval, dest, path, text):
    if slot < len(self.beacon_widgets):
        w = self.beacon_widgets[slot]
        w['interval'].set_value(interval)
        w['dest'].set_text(dest)
        w['path'].set_text(path)
        w['text'].set_text(text)
```

#### 2.5 Register init methods in __init__

Add to the init sequence (after line 91):

```python
self.init_digipeater_frame()
self.init_beacon_frame()
```

### Phase 3: glade/TncConfigApp.glade -- UI Layout

Add two new pages to the `config_stack` GtkStack, before the about page
(which moves from position 8 to 10).

#### 3.1 Digipeater page

Stack name: `digipeater`
Title: "Digipeater..."
Position: 8

Contents (inside a GtkFrame > GtkAlignment > GtkBox vertical):

1. **Enable checkbox** (`digipeater_enable_check_button`) -- "Enable Digipeater"
2. **Dedupe seconds** (`dedupe_seconds_spin_button`) -- GtkSpinButton, range 1-255, default 30, with label "Dedupe Window (seconds)"
3. **Routing mode frame** -- GtkFrame "Routing Mode" containing GtkGrid of check buttons:
   - Substitute (`substitute_check_button`) -- "Substitute exhausted n-N with my callsign"
   - Skip Complete (`skip_complete_check_button`) -- "Drop completed addresses from path"
   - Preempt Front (`preempt_front_check_button`) -- "Preempt: move to front"
   - Preempt Truncate (`preempt_truncate_check_button`) -- "Preempt: truncate path"
   - Preempt Drop (`preempt_drop_check_button`) -- "Preempt: drop ahead"
   - Preempt Mark (`preempt_mark_check_button`) -- "Preempt: mark only"
4. **Aliases frame** -- GtkFrame "Digipeater Aliases" containing:
   - GtkListBox (`alias_list_box`) -- rows built dynamically in Python

Each alias row (built in code, not Glade):
- GtkBox horizontal: [GtkEntry callsign] [GtkCheck "Use"] [GtkSpinButton hops 0-7] [GtkLabel "Set"] [GtkButton "Apply"]

#### 3.2 Beacon page

Stack name: `beacons`
Title: "Beacons..."
Position: 9

Contents (inside a GtkFrame > GtkAlignment > GtkBox vertical):

For each of 4 beacon slots, a GtkFrame containing GtkGrid:
- Label: "Beacon N"
- GtkSpinButton interval (1-65535 seconds)
- GtkEntry dest (callsign, max 8 chars)
- GtkEntry path (comma-separated path, max 32 chars)
- GtkEntry text (beacon text, max 128 chars)
- GtkButton "Apply" (with beacon slot as user_data)

### Phase 4: Python 3 Modernization

The RFCOMM branch is a Python 2/3 hybrid.  Clean up remaining Python 2isms:

- TncModel.py: change shebang from `python2.7` to `python3`
- Remove `from __future__ import print_function, unicode_literals`
- Remove `from builtins import bytes, chr`
- Ensure all string/bytes handling is Python 3 native

### Phase 5: Testing

#### 5.1 Protocol unit test

Write a test that creates a TncModel with a mock socket, feeds it KISS-encoded
digipeater/beacon responses, and verifies the correct `app.tnc_*` callbacks
fire with correct values.

#### 5.2 Manual hardware testing

1. Connect to TNC4 with digipeater firmware
2. Verify digipeater and beacon pages appear in sidebar
3. Verify existing settings still work (no regressions)
4. Configure digipeater enable, routing mode, dedupe
5. Configure aliases (set callsign, use, hops)
6. Configure beacons (interval, dest, path, text)
7. Save settings to EEPROM
8. Disconnect, reconnect, verify settings persisted
9. Verify digipeater actually digipeats (send APRS frame, observe relay)

## File Summary

| File | Changes |
|------|---------|
| TncModel.py | Add constants, handlers, command methods for digipeater/beacon |
| TncConfigApp.py | Add init/handlers/callbacks for digipeater/beacon pages |
| glade/TncConfigApp.glade | Add digipeater and beacon stack pages |
| setup.py | Bump version to 1.4.0 |

## Resolved Design Decisions

1. **Alias table layout** -- GtkGrid with 8 rows defined in Glade.  Hide
   unused rows.  Chosen over GtkListBox for simplicity.  May revisit after
   seeing it in action.

2. **Beacon apply semantics** -- Each beacon slot has its own "Apply" button.
   Changes are not sent live (unlike audio gain sliders) because beacon text
   fields are longer and live sending would be noisy.

3. **reply_ext NUL bug** -- Fixed in firmware.  `reply_ext()` now copies all
   bytes unconditionally instead of stopping at the first NUL.  The Python
   handler can assume full-length data but should still handle short data
   gracefully as a defensive measure.