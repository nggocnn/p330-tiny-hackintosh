# macOS Sequoia on the Lenovo ThinkStation P330 Tiny

An OpenCore hackintosh build for the P330 Tiny (i7-8700, UHD 630, Q370): macOS 15.8.1 as `Macmini8,1` with OpenCore 1.0.8.

This repo holds the scripts that build the EFI, a step-by-step install guide and a log of every problem met on the way. The EFI folder itself is not stored here. Three Python scripts download pinned releases of OpenCore and the kexts and generate it, so every setting is written down once, with the reason next to it.

- [docs/guide.md](docs/guide.md): how to build the EFI, install macOS and finish the setup.
- [docs/problems.md](docs/problems.md): each problem met on the way, with its symptom, cause and fix.

## Hardware

| Part | Model |
| --- | --- |
| Machine | Lenovo ThinkStation P330 Tiny (Q370), BIOS `M1UKT79A` |
| CPU / graphics | Intel Core i7-8700, UHD 630, no discrete GPU |
| Memory / disk | 16 GB, WDC PC SN730 256 GB NVMe |
| Ethernet | Intel I219-LM |
| Audio | Realtek ALC235 (codec ID `10ec0235`) |
| Wireless | Intel Wireless-AC 9560 (M.2) |
| Video outputs | 1 DisplayPort, 2 HDMI (one on the optional module) |
| USB | 1 USB-C and 1 USB-A in front, 4 USB-A at the rear |

## Software

| Part | Version |
| --- | --- |
| macOS | Sequoia 15.8.1 |
| SMBIOS | `Macmini8,1` |
| Boot loader | OpenCore 1.0.8 |

Do not move to macOS Tahoe with this config. It dropped the `Macmini8,1` model and the audio framework AppleALC builds on.

## Status

### Works

| Item | Notes |
| --- | --- |
| Boot from the internal SSD | |
| Graphics acceleration | Metal, 1080p at 75 Hz, HEVC hardware decode |
| HDMI video and audio | On both HDMI ports. Pick the monitor as sound output once per port, macOS remembers it |
| Ethernet | |
| Internal speaker and microphone | |
| USB 2 and USB 3 on all six ports | 15 mapped ports, each checked with a USB 2 and a USB 3 drive |
| Intel AMT remote keyboard and mouse | Needs two internal ports in the USB map |
| Sleep and wake | USB keyboards and the power button wake it |
| Wi-Fi | Through `itlwm` and the HeliPort app |
| Bluetooth | Keyboard and mouse tested |
| CPU power management | |
| Temperature and fan sensors | Readable with the Stats app |
| Volume keys on HDMI audio | Needs the MonitorControl app |

### Known issues

| Item | Notes |
| --- | --- |
| Sleep takes 30 s to start | A macOS Wi-Fi service times out. No fix found |
| Wi-Fi is slower than Ethernet | About 150 Mbit/s down and 90 up on a link that gives 246 and 206 by cable |
| Bluetooth devices cannot wake the machine | Use a USB keyboard or the power button |
| No AirDrop or Handoff | Not supported by the Wi-Fi driver |
| CPU reaches 100 °C under a full all-core load | Around 58 °C idle. Not compared with another operating system |

### Not tested

DisplayPort, Apple ID, iMessage and FaceTime.

## Quick start

```bash
python3 fetch-deps.py                     # download OpenCore and the kexts
python3 build-usbmap.py                   # generate the USB port map
PROFILE=installer python3 build-efi.py    # EFI for the USB installer
python3 build-efi.py                      # EFI for the internal SSD
```

The result is in `efi/EFI`. The scripts need Python 3 and run on Linux, including WSL. Each `build-efi.py` run replaces `efi/EFI`, so copy the installer build to the USB stick before building the SSD one.

The [guide](docs/guide.md) covers the BIOS settings, the USB installer, the install itself and the steps afterwards.

## Files

| File | Purpose |
| --- | --- |
| `fetch-deps.py` | Downloads pinned releases of OpenCore and the kexts into `downloads/` and unpacks them into `build/` |
| `build-usbmap.py` | Writes `usb-map/UTBMap.kext`, the USB port map |
| `build-efi.py` | Assembles `efi/EFI` and its `config.plist`, then runs OpenCore's validator |
| `install-efi.sh` | Run on the Mac with `sudo`: copies a staged EFI onto the SSD's EFI partition |
| `docs/guide.md` | The full walk-through |
| `docs/problems.md` | The problem log |

## Not in this repo

`smbios.json` (the generated serial numbers), the hardware dumps and all build output are ignored by git on purpose. `build-efi.py` creates its own `smbios.json` on the first run. Never publish yours: it identifies your machine to Apple.

## Disclaimer

This is a record of one machine, not a supported product. Installing erases the internal drive. Running macOS on non-Apple hardware is against Apple's licence terms.
