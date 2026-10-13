#!/usr/bin/env python3
"""Generate UTBMap.kext for the P330 Tiny from the port table in its DSDT.

The firmware (BDID 0x30, PCH-H) marks these root hub ports as connectable;
HS and SS ports sharing a _PLD group are the same physical connector.
USB 3 ports start at index 17 on this controller (16 USB 2 ports before them).
"""
import plistlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "usb-map" / "UTBMap.kext" / "Contents"

USB3_A, USB_C_SWITCH, INTERNAL = 3, 9, 255
# (name, controller port index, connector type, physical connector group)
PORTS = [
    ("HS02", 2, USB3_A, "USB-A, group 2 (USB 2 side)"),
    ("HS04", 4, USB_C_SWITCH, "USB-C front (USB 2 side)"),
    ("HS05", 5, USB3_A, "USB-A, group 5 (USB 2 side)"),
    ("HS06", 6, USB3_A, "USB-A, group 6 (USB 2 side)"),
    ("HS07", 7, USB3_A, "USB-A, group 7 (USB 2 side)"),
    ("HS08", 8, USB3_A, "USB-A, group 8 (USB 2 side)"),
    # Bluetooth half of the Intel 9560 CNVi module in the M.2 slot. With this
    # entry the map is at macOS's 15-port limit.
    ("HS14", 14, INTERNAL, "Intel 9560 Bluetooth (internal)"),
    # Intel AMT USB redirection: the KVM keyboard and mouse live here (seen on
    # port 15 in macOS). Leaving these out kills MeshCommander input.
    ("USR1", 15, INTERNAL, "Intel AMT USB-R (KVM keyboard and mouse)"),
    ("USR2", 16, INTERNAL, "Intel AMT USB-R (storage redirection)"),
    ("SS01", 17, USB3_A, "USB-A, group 2 (USB 3 side)"),
    ("SS02", 18, USB_C_SWITCH, "USB-C front (USB 3 side)"),
    ("SS03", 19, USB3_A, "USB-A, group 6 (USB 3 side)"),
    ("SS04", 20, USB3_A, "USB-A, group 5 (USB 3 side)"),
    ("SS05", 21, USB3_A, "USB-A, group 7 (USB 3 side)"),
    ("SS06", 22, USB3_A, "USB-A, group 8 (USB 3 side)"),
]


def le32(value):
    return value.to_bytes(4, "little")


def main():
    info = plistlib.loads((ROOT / "build" / "utb_template.plist").read_bytes())
    info["IOKitPersonalities"] = {"XHC": {
        "CFBundleIdentifier": "com.dhinakg.USBToolBox.kext",
        "IOClass": "USBToolBox",
        "IOProviderClass": "IOPCIDevice",
        "IOMatchCategory": "USBToolBox",
        "IONameMatch": "XHC",
        "IOProviderMergeProperties": {
            "port-count": le32(max(p[1] for p in PORTS)),
            "ports": {name: {"port": le32(index), "UsbConnector": kind, "#comment": note}
                      for name, index, kind, note in PORTS},
        },
    }}
    info["OSBundleLibraries"] = {"com.dhinakg.USBToolBox.kext": "1.0.0"}
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "Info.plist", "wb") as fh:
        plistlib.dump(info, fh, sort_keys=True)
    print(f"wrote {OUT / 'Info.plist'} with {len(PORTS)} ports")


if __name__ == "__main__":
    main()
