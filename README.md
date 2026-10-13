# p330-tiny-hackintosh

macOS Sequoia on a Lenovo ThinkStation P330 Tiny, booted with OpenCore. The EFI folder is not stored here: three small scripts download the parts and generate it, so every setting is written down once, with the reason next to it.

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
| Wireless | Intel Wireless-AC 9560 (M.2, added later) |
| Video outputs | 1 DisplayPort, 2 HDMI (one on the optional module) |

The ThinkCentre M720q and M920q share this platform, so most of this should carry over, but only the P330 Tiny was tested.

## What works

| Item | State |
| --- | --- |
| macOS 15.8.1 as `Macmini8,1`, boot from the internal SSD | works |
| Graphics acceleration, HDMI video and HDMI audio | works |
| Ethernet, internal speaker, microphone | works |
| Sleep and wake | works, sleep takes 30 s to start |
| USB, 15 mapped ports, Intel AMT remote keyboard and mouse | works |
| Wi-Fi and Bluetooth (Intel 9560) | works through `itlwm` and HeliPort, no AirDrop or Handoff |
| DisplayPort, second HDMI port, USB-C port, USB 3 speed | not tested |
| Apple ID, iMessage, FaceTime | not tested |

## Quick start

```bash
python3 fetch-deps.py                     # download OpenCore and the kexts
python3 build-usbmap.py                   # generate the USB port map
PROFILE=installer python3 build-efi.py    # EFI for the USB installer
python3 build-efi.py                      # EFI for the internal SSD
```

The result is in `efi/EFI`. The scripts need Python 3 and run on Linux, including WSL. The guide covers the rest.

## Files

| File | Purpose |
| --- | --- |
| `fetch-deps.py` | Downloads pinned releases of OpenCore and the kexts into `downloads/` and unpacks them into `build/` |
| `build-usbmap.py` | Writes `usb-map/UTBMap.kext`, the USB port map |
| `build-efi.py` | Assembles `efi/EFI` and its `config.plist`, then runs OpenCore's validator |
| `install-efi.sh` | Run on the Mac with `sudo`: copies a staged EFI onto the SSD's EFI partition |

## Not in this repo

`smbios.json` (the generated serial numbers) and the hardware dumps are ignored by git on purpose. `build-efi.py` creates its own `smbios.json` on the first run. Never publish yours.
