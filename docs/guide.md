# Guide: macOS Sequoia on the ThinkStation P330 Tiny

This walks through the whole build in order. Each step that went wrong the first time links to its entry in [problems.md](problems.md).

## 1. What you need

- The P330 Tiny, wired to Ethernet. The installer downloads macOS over the network.
- A second computer with Python 3 to build the EFI. Linux or WSL is assumed.
- A USB stick of 4 GB or more.
- A monitor. HDMI works with this config. DisplayPort is left at its native settings but was not tested.
- A USB keyboard and mouse. Not every mouse works, see [problem 4](problems.md#4-one-wired-mouse-never-worked).

Installing erases the internal drive completely.

## 2. Choices made here

| Choice | Value | Why |
| --- | --- | --- |
| macOS version | Sequoia (15) | Matches the hardware. Tahoe (26) dropped the `Macmini8,1` model and removed the audio framework AppleALC builds on |
| SMBIOS | `Macmini8,1` | The 2018 Mac mini has the same CPU family and graphics |
| Boot loader | OpenCore 1.0.8 | |
| Disk layout | macOS only | 256 GB is tight for two systems |

## 3. BIOS settings

Enter the BIOS with F1 at the Lenovo logo.

| Setting | Value |
| --- | --- |
| Secure Boot | Disabled |
| CSM | Disabled (UEFI only) |
| SATA mode | AHCI |
| Startup > Primary Boot Sequence | USB above Network |

Two things the BIOS does not offer, which the config handles instead:

- **CFG Lock** cannot be turned off. The config sets the `AppleXcpmCfgLock` quirk.
- **Graphics memory (DVMT)** cannot be raised to 64 MB. The config patches the framebuffer to fit the default 32 MB.

## 4. Optional: read the hardware from Linux first

If the machine still runs Linux, dump its tables before wiping it. This is how the settings in this repo were derived, and it is the way to check a machine that differs from the one above.

```bash
sudo apt install -y acpica-tools pciutils usbutils dmidecode msr-tools
mkdir p330-dumps && cd p330-dumps
sudo acpidump -b                                   # ACPI tables as .dat files
lspci -nn > lspci.txt
grep -hE 'Codec|Vendor Id' /proc/asound/card*/codec#* > audio-codec.txt
for c in /sys/class/drm/card*-*/status; do echo "$c: $(cat $c)"; done > drm-connectors.txt
sudo modprobe msr && sudo rdmsr 0xE2 > cfg-lock.txt
```

What to look at:

| Check | Meaning |
| --- | --- |
| `rdmsr 0xE2` has bit 15 set (for example `1e008008`) | CFG Lock is on, keep `AppleXcpmCfgLock` |
| Audio `Vendor Id: 0x10ec0235` | ALC235, layout 17 applies |
| `lspci` shows `8086:15bb` | I219-LM, IntelMausi supports it |
| Which `HDMI-A-n` reads `connected` | Tells you which graphics connector the monitor is on |

Keep the dump private. It contains the board serials and the embedded Windows licence key (`msdm.dat`).

## 5. Build the EFI

```bash
python3 fetch-deps.py                    # once
python3 build-usbmap.py                  # once, and after editing the port list
PROFILE=installer python3 build-efi.py   # the build for the USB stick
```

The output is `efi/EFI`. The first run creates `smbios.json` with a generated serial, board serial and UUID, and later runs reuse it. Open it and set `rom` to the machine's Ethernet MAC address, 12 hex digits without separators. The MAC is printed on the PXE boot screen and shown by `ip link` under Linux.

The two profiles:

| | `PROFILE=installer` | default |
| --- | --- | --- |
| Use | USB stick: install and rescue | Internal SSD: daily boot |
| Boot | Verbose text, all picker entries, 5 s timeout | Apple logo, only macOS in the picker, 3 s timeout |
| OpenCore log | Written to the EFI partition on each boot | Off |
| USB map | Default: ports 1 to 15, all USB 2 | Generated map with USB 3 and the internal ports |

What the config sets, and why:

| Area | Setting | Reason |
| --- | --- | --- |
| ACPI | `SSDT-PLUG`, `SSDT-EC-USBX`, `SSDT-AWAC-DISABLE`, `SSDT-PMC` | CPU power management, a fake embedded controller with USB power values, a working clock, and NVRAM on 300-series chipsets. OpenCore's prebuilt samples fit this board unchanged |
| Booter quirks | `DevirtualiseMmio`, `ProtectUefiServices`, `RebuildAppleMemoryMap`, `SyncRuntimePermissions` | Standard for Coffee Lake on a 300-series board |
| Kernel quirks | `AppleXcpmCfgLock`, `DisableIoMapper` | CFG Lock cannot be disabled, and VT-d stays on in the BIOS |
| Graphics | `AAPL,ig-platform-id` `07009B3E`, `framebuffer-stolenmem` `00003001` | Desktop UHD 630 with the default 32 MB of graphics memory |
| Graphics | con1 and con2 typed HDMI with bus IDs 2 and 4 | HDMI is black without it, see [problem 1](problems.md#1-black-screen-when-the-graphics-driver-loads) |
| Graphics | `force-online` | HDMI monitor stays black after wake without it, see [problem 6](problems.md#6-monitor-stays-black-after-wake) |
| Audio | `layout-id` 17 | The AppleALC layout for the ALC235 that gives working speaker, microphone and HDMI audio on this board |
| Security | `SecureBootModel` `Disabled` | The installer loops with `Default`, see [problem 2](problems.md#2-the-installer-reboots-into-the-same-stage-forever) |
| NVRAM | two `bluetooth...` variables | Required by BlueToolFixup for Bluetooth |

Kexts: Lilu, VirtualSMC with SMCProcessor and SMCSuperIO, WhateverGreen, AppleALC, IntelMausi, NVMeFix, itlwm, IntelBTPatcher, IntelBluetoothFirmware, BlueToolFixup, USBToolBox with a map.

## 6. Make the USB installer

Download the Sequoia recovery image straight from Apple with the tool that ships with OpenCore:

```bash
mkdir -p usb/com.apple.recovery.boot
python3 build/oc/Utilities/macrecovery/macrecovery.py \
  -b Mac-7BA5B2D9E42DDD94 -m 00000000000000000 \
  -o usb/com.apple.recovery.boot download
cp -a efi/EFI usb/EFI
```

Format the stick as FAT32 and copy both folders, `EFI` and `com.apple.recovery.boot`, to its root. Eject it properly.

## 7. Install macOS

1. Plug in Ethernet, monitor, keyboard and the stick. Power on, press F12 and choose the stick.
2. In the OpenCore menu choose the entry marked `(dmg)`. That is the recovery image. Scrolling text is expected.
3. In Recovery open Disk Utility and choose **View > Show All Devices**. Without it the internal drive is not listed. It shows volumes by default, and a drive that still holds another system has no volume macOS can read.
4. Select the drive itself (the top line), click Erase: name `Macintosh HD`, format APFS, scheme GUID Partition Map.
5. Quit Disk Utility and choose Reinstall macOS Sequoia.
6. The machine reboots several times. Boot the stick each time and pick `macOS Installer`, later `Macintosh HD`. Do not pick the `(dmg)` entry again, which restarts from the beginning.
7. At the setup screens choose Set Up Later for the Apple ID.

Until step 8 the SSD has no boot loader. If the firmware shows `Start PXE over IPv6`, it simply did not boot the stick: press F12 again.

## 8. Put OpenCore on the SSD

On the Mac, turn on **System Settings > General > Sharing > Remote Login**. Then from the build computer:

```bash
python3 build-efi.py                                  # default profile
ssh <user>@<mac-ip> 'mkdir -p ~/p330-efi'
scp -r efi/EFI install-efi.sh <user>@<mac-ip>:p330-efi/
ssh -t <user>@<mac-ip> 'sudo ~/p330-efi/install-efi.sh'
```

`install-efi.sh` checks that `disk0` is the SN730, mounts its EFI partition, keeps the previous `EFI` folder as `EFI.bak.<timestamp>`, copies the new one and prints the checksum of both configs. Edit the model check if your drive is different.

Reboot with F12, choose the internal drive and confirm it boots without the stick. Keep the stick: it is the rescue boot if a later change breaks the SSD copy.

## 9. After the install

**Sleep.** Turn off the features that need Apple hardware:

```bash
sudo pmset -a hibernatemode 0 standby 0 autopoweroff 0 powernap 0 proximitywake 0 tcpkeepalive 0 womp 0
sudo rm -f /var/vm/sleepimage
```

Sleep works after that, but takes 30 s to start, see [problem 5](problems.md#5-sleep-takes-30-seconds-to-start). Undo with `sudo pmset -a restoredefaults`.

**Wi-Fi.** The Intel card appears as an extra Ethernet interface. Install the HeliPort app to choose a network, and add it under System Settings > General > Login Items so it reconnects after a reboot. HeliPort is not code-signed. See [problem 8](problems.md#8-wi-fi-and-bluetooth-on-the-intel-9560).

**Bluetooth.** Works from System Settings once the kexts are loaded.

**Volume keys on HDMI.** macOS has no volume control for HDMI audio. The MonitorControl app sets the monitor's own volume from the keyboard, see [problem 7](problems.md#7-volume-keys-do-nothing-on-hdmi-audio).

**Apple ID.** Before signing in, look up the generated serial on Apple's coverage page. It must come back as not valid, meaning no real Mac owns it.

## 10. Checking the result

All of these run without `sudo` on the Mac:

| Command | Expected |
| --- | --- |
| `sysctl hw.model machdep.xcpm.mode` | `Macmini8,1`, `1` |
| `system_profiler SPDisplaysDataType` | UHD 630, Metal supported, the monitor online |
| `kextstat \| grep -v com.apple` | every kext from the list above |
| `ioreg -p IOService -r -c AppleIntelCNLUSBXHCI -d 2 \| grep -c -E 'HS\|SS\|USR'` | `15` |
| `pmset -g stats` | Sleep Count goes up after a sleep |
| `pmset -g log \| grep -E ' (Sleep\|Wake) '` | sleep and wake reasons, and slow drivers |

## 11. Changing the USB map

`build-usbmap.py` holds the port list as a table of name, controller port number, connector type and a comment. macOS allows 15 ports and the list uses all 15, so adding one means removing another. The port numbers come from the firmware's table, see [problem 3](problems.md#3-usb-port-map-and-the-lost-intel-amt-keyboard-and-mouse). After editing, run `build-usbmap.py`, then `build-efi.py`, then install as in step 8.

## 12. Updates

- Point updates inside Sequoia are normally fine. Keep the stick at hand.
- Do not move to Tahoe with this config. It needs a different SMBIOS and a different audio setup.
- To update OpenCore or a kext, change the pinned URL in `fetch-deps.py`, delete `build/`, and rebuild. Test from the stick first: build with `PROFILE=installer`, copy to the stick, boot it with F12.

## 13. Recovery

| Situation | What to do |
| --- | --- |
| SSD build does not boot or has no input | F12, boot the stick, fix the SSD copy over SSH |
| Need the boot picker's hidden entries | Press Space in the OpenCore menu |
| Strange behaviour after a config change | Space in the picker, then Reset NVRAM |
| Need the old EFI back | It is on the SSD's EFI partition as `EFI.bak.<timestamp>` |
