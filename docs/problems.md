# Problems met during the build, one by one

In the order they came up. Each entry gives what was seen, why it happened, what fixed it and how the fix was checked. Status is one of resolved, workaround or open.

| # | Problem | Status |
| --- | --- | --- |
| 1 | [Black screen when the graphics driver loads](#1-black-screen-when-the-graphics-driver-loads) | resolved |
| 2 | [Disk Utility shows no internal drive](#2-disk-utility-shows-no-internal-drive) | resolved |
| 3 | [The installer reboots into the same stage forever](#3-the-installer-reboots-into-the-same-stage-forever) | resolved |
| 4 | [USB port map, and the lost Intel AMT keyboard and mouse](#4-usb-port-map-and-the-lost-intel-amt-keyboard-and-mouse) | resolved |
| 5 | [One wired mouse never worked](#5-one-wired-mouse-never-worked) | workaround |
| 6 | [Sleep takes 30 seconds to start](#6-sleep-takes-30-seconds-to-start) | open |
| 7 | [Monitor stays black after wake](#7-monitor-stays-black-after-wake) | resolved |
| 8 | [Volume keys do nothing on HDMI audio](#8-volume-keys-do-nothing-on-hdmi-audio) | open |
| 9 | [Wi-Fi and Bluetooth on the Intel 9560](#9-wi-fi-and-bluetooth-on-the-intel-9560) | resolved |
| 10 | [Keyboard Setup Assistant on every reconnect](#10-keyboard-setup-assistant-on-every-reconnect) | open |

## 1. Black screen when the graphics driver loads

**Status:** resolved

**Symptom.** The recovery image booted through the verbose text, then the screen went black at the moment the graphics driver takes over and stayed black. No panic. The monitor was on HDMI.

**Cause.** macOS drives the UHD 630 through a framebuffer table chosen by `AAPL,ig-platform-id`. The desktop one, `07009B3E`, defines three connectors, all as DisplayPort:

| Connector | Bus ID | Type |
| --- | --- | --- |
| con0 | `0x05` | DisplayPort |
| con1 | `0x04` | DisplayPort |
| con2 | `0x06` | DisplayPort |

The first attempt only changed the type of each connector to HDMI (`00080000`). That is not enough. The bus ID selects the pins used to talk to the monitor, and the stock values are the DisplayPort channels. On the Cannon Point chipset family, which includes Q370, the HDMI pins for the three ports are 1, 2 and 4.

**Fix.** Set the HDMI type and the HDMI bus ID together. On this machine the DisplayPort is con0 and the two HDMI ports are con1 and con2, so only those two are patched:

```
framebuffer-con1-enable  01000000
framebuffer-con1-type    00080000
framebuffer-con1-busid   02000000
framebuffer-con2-enable  01000000
framebuffer-con2-type    00080000
framebuffer-con2-busid   04000000
```

**Checked.** Picture at 1920x1080 in Recovery, in the installer and in macOS, with Metal 3 and HDMI audio. `ioreg` shows the display on `AppleIntelFramebuffer@1`.

**Notes.**
- Which connector is which was worked out from two facts: under Linux the monitor was on `HDMI-A-2`, and under macOS on framebuffer 1.
- The DisplayPort (con0) and the second HDMI port (con2) were not tested.
- An active DisplayPort to HDMI adapter keeps the signal as DisplayPort and needs an unpatched connector.

## 2. Disk Utility shows no internal drive

**Status:** resolved

**Symptom.** In Recovery, Disk Utility listed a small `NO NAME` volume and the recovery disk image, but not the SSD. It looked as if macOS could not see the NVMe drive.

**Cause.** Disk Utility shows volumes by default, not drives. The SSD still held a Linux install, and the only part of it macOS can read is the old EFI partition, which is what `NO NAME` was. So the drive was detected all along.

**Fix.** View > Show All Devices, then select the drive itself (the top line) and erase it as APFS with a GUID Partition Map. If the Scheme field is missing, a volume is selected, not the drive.

**Checked.** The installer offered `Macintosh HD` afterwards.

## 3. The installer reboots into the same stage forever

**Status:** resolved

**Symptom.** After the first stage, `macOS Installer` booted, printed pages of lines like the one below, and rebooted. Five times.

```
patchd: _patchd_macos_copyfile_callback(172): CopyFile: Done copying /mnt5/softwareupdate/MSUPreservedBootObjects/Preboot/...
```

Two or three boots of `macOS Installer` are normal. What gave it away was the timing: the OpenCore log files on the stick were one minute apart, far too short for a real install stage.

**Cause.** Not proven from logs. OpenCore's log shows the boot loader finishing cleanly each time, including Apple Secure Boot checks, so the failure is inside the installer. The looping stage copies boot files that depend on the secure boot model, and with `SecureBootModel` set to `Default` OpenCore emulates the model of a Mac mini with a T2 chip.

**Fix.**

```
Misc > Security > SecureBootModel = Disabled      (was Default)
```

**Checked.** The next boot of `macOS Installer` ran through to the "Select Your Country or Region" screen. Installed version 15.8.1.

**Notes.**
- The line `[AHCI][PRT] ... Port 3 - COMRESET did not proceed` in the same output is an empty SATA port and harmless.
- Setting it back to `Default` after the install was not tried.

## 4. USB port map, and the lost Intel AMT keyboard and mouse

**Status:** resolved

**Background.** macOS allows 15 ports per USB controller. This controller has 26: 16 USB 2 and 10 USB 3. A map tells macOS which ones exist. Without one, USBToolBox exposes ports 1 to 15, which are all USB 2, so everything works but only at USB 2 speed. The mapping tool runs on Windows and macOS only, and the machine ran Linux.

**What was done.** The map was generated from the firmware instead. The DSDT (from `acpidump`, decompiled with `iasl`) describes each port: whether it is connectable (`_UPC`) and which physical connector it belongs to (`_PLD`). For this board:

| USB 2 port | USB 3 port | Physical connector |
| --- | --- | --- |
| HS02 (2) | SS01 (17) | group 2 |
| HS04 (4) | SS02 (18) | group 4 |
| HS05 (5) | SS04 (20) | group 5 |
| HS06 (6) | SS03 (19) | group 6 |
| HS07 (7) | SS05 (21) | group 7 |
| HS08 (8) | SS06 (22) | group 8 |

**Symptom.** With that 12-port map, the keyboard and mouse of the Intel AMT remote session (MeshCommander) stopped working. They had worked on the default map.

**Cause.** AMT's remote keyboard and mouse are USB devices on two internal "USB redirection" ports, `USR1` (15) and `USR2` (16). The firmware marks them not connectable, so the generated map dropped them.

**Fix.** Add them as internal ports, and the internal Bluetooth port too:

```python
("HS14", 14, INTERNAL, "Intel 9560 Bluetooth (internal)"),
("USR1", 15, INTERNAL, "Intel AMT USB-R (KVM keyboard and mouse)"),
("USR2", 16, INTERNAL, "Intel AMT USB-R (storage redirection)"),
```

That makes exactly 15.

**Checked.** `ioreg` lists the 15 named ports. AMT input works. Devices plugged into four different ports appeared on the port numbers the table predicts.

**Notes.**
- The firmware labels HS04 as USB-C, but a USB-A receiver was plugged into it. The connector types in the map are therefore not all right. Nothing misbehaves because of it.
- USB 3 speed and the real USB-C port were not tested.
- If you do not use Intel AMT, the two `USR` ports can be replaced by others.

## 5. One wired mouse never worked

**Status:** workaround

**Symptom.** A wired mouse did nothing in macOS, on every map and after reboots. The keyboard in the next port worked. This was first taken for a port map problem.

**Cause.** The mouse. macOS saw it connect and failed to read its descriptor, eight attempts each time:

```
kPortStatConnectCount = 8
kPortStatEnumerationFailureCount = 8
```

```
IOUSBHostDevice: device descriptor fragment is invalid
IOUSBHostFamily::validateEndpointMaxPacketSize: endpoint 0x00 invalid wMaxPacketSize 0x0000
AppleUSBHostPort::enumerateDeviceComplete_block_invoke: enumeration failed
```

A different mouse on the same port was recognised at once. Why this one answers Linux and the firmware but not macOS was not investigated.

**Fix.** None. Use another mouse.

**How to tell a dead port from a rejected device.** Read the per-port counters with `ioreg -r -c AppleUSB20XHCIPort -l | grep port-statistics`, and the kernel log with `sudo dmesg | grep -iE "usb|enumerat"`. A port with connects and enumeration failures is alive.

## 6. Sleep takes 30 seconds to start

**Status:** open

**Symptom.** After choosing Sleep, the display turns off at once, but the machine only sleeps about 30 s later.

**Cause.** The power log names it on every sleep:

```
Kernel Client Acks  Delays to Sleep notifications: [wifip2pd timed out(30000 ms)]
```

`wifip2pd` is a macOS Wi-Fi service. The `Macmini8,1` identity implies Apple Wi-Fi hardware, the service is asked to prepare for sleep, never answers, and macOS waits out the timeout. Adding the Intel card did not change it, because `itlwm` does not present itself as native Wi-Fi.

**Fix.** None yet. The service is protected by System Integrity Protection.

**A false alarm on the way.** The first tests looked as if sleep did not work at all: the screen went dark and came back 20 s later, and `pmset -g stats` showed `Sleep Count:0`. The keyboard was being pressed during the wait, which cancels sleep. Triggered with `pmset sleepnow` over SSH and hands off the keyboard, it slept: power LED blinking, fan stopped. The `pmset` settings in the guide were applied during that confusion and kept, because those features need Apple hardware.

**Checked.** `pmset -g log` shows `Entering Sleep state` and `Wake from Normal Sleep`, with a wake time around 1.2 s.

## 7. Monitor stays black after wake

**Status:** resolved

**Symptom.** After waking, the machine was up and reachable, but the HDMI monitor stayed black until the cable was unplugged and plugged back in. `system_profiler SPDisplaysDataType` listed the graphics chip with no display attached.

**Cause.** A known behaviour of this graphics generation with HDMI under macOS: after wake the driver does not see the display as online.

**Fix.** WhateverGreen's switch for it, as a device property on the graphics chip:

```
force-online  01000000
```

The boot argument `igfxonln=1` does the same.

**Checked.** Sleep, wake by key press, and the monitor came back by itself.

**Notes.** `force-online` can make macOS believe a monitor is attached to an unused output. If a phantom display appears, remove it. DisplayPort should not need it.

## 8. Volume keys do nothing on HDMI audio

**Status:** open

**Symptom.** The keyboard's volume control works with the internal speaker and does nothing when the sound goes to the monitor over HDMI.

**Cause.** Normal macOS behaviour, the same on a real Mac. HDMI and DisplayPort audio have no software volume. macOS sends full level and leaves the volume to the monitor.

**Fix.** The MonitorControl app catches the volume keys and sets the monitor's own volume over DDC. It needs Accessibility access.

**Checked.** Not yet. The app is installed, but whether DDC gets through on these HDMI ports is unconfirmed. If it does not, check the monitor's DDC/CI setting.

## 9. Wi-Fi and Bluetooth on the Intel 9560

**Status:** resolved

**Background.** An Intel Wireless-AC 9560 module was added to the M.2 slot after the install. macOS lists it as PCI device `8086:a370`.

**Decision.**

| Part | Kexts | Notes |
| --- | --- | --- |
| Wi-Fi | `itlwm` 2.3.0 | Appears as an Ethernet interface. The HeliPort app chooses the network |
| Bluetooth | `IntelBluetoothFirmware`, `IntelBTPatcher` 2.4.0, `BlueToolFixup` 2.7.2 | Not `IntelBluetoothInjector`, which is for macOS 11 and older |

`AirportItlwm` would give the native Wi-Fi menu, but its newest build is for Sonoma 14.4 and there is none for Sequoia.

Two more things Bluetooth needs:

- NVRAM variables required by BlueToolFixup 2.7 and newer:
  ```
  bluetoothExternalDongleFailed    00
  bluetoothInternalControllerInfo  0000000000000000000000000000
  ```
- Its internal USB port, HS14, in the map (see problem 4).

**Checked.** All kexts loaded. The Wi-Fi interface got an address and reached the internet on its own. The Bluetooth controller went from `Address: NULL`, State Off, to a real address, State On. A keyboard and a mouse were paired.

**Notes.**
- No AirDrop or Handoff with this driver.
- HeliPort is not code-signed, and must be added to Login Items or Wi-Fi does not reconnect after a reboot.
- HeliPort's disk image has a licence prompt that blocks `hdiutil attach` over SSH. Converting it first works: `hdiutil convert HeliPort.dmg -format UDTO -o HeliPort.cdr`.
- The EFI grows from 8 MB to 35 MB, mostly Wi-Fi firmware.

## 10. Keyboard Setup Assistant on every reconnect

**Status:** open

**Symptom.** Each time the keyboard or the mouse connected, macOS opened the Keyboard Setup Assistant again.

**Cause.** Several devices present a keyboard interface: the keyboard's receiver, the mouse (for its extra buttons) and the Intel AMT remote keyboard. macOS asks about each one it cannot identify. Why the answers were not kept was not established.

**Fix.** Write the answers into the file macOS reads them from. The key is `<product ID>-<vendor ID>-0` in decimal, and the value is 40 for ANSI, 41 for ISO or 42 for JIS:

```bash
sudo defaults write /Library/Preferences/com.apple.keyboardtype keyboardtype -dict-add "<product>-<vendor>-0" -int 40
```

Find the IDs with `hidutil list` (usage page 1, usage 6 is a keyboard) and convert them from hex.

**Checked.** Partly. The entries are stored and the assistant was not running afterwards. Whether it stays away on a reconnect is unconfirmed.

**Notes.** A device can report a different product ID per mode, for example through its USB receiver and over Bluetooth. Each needs its own entry.
