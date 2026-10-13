#!/usr/bin/env python3
"""Assemble the OpenCore EFI for the ThinkStation P330 Tiny (i7-8700, UHD 630, Q370).

Reads the unpacked OpenCore release and kexts from build/ (see fetch-deps.py)
and writes efi/EFI. SMBIOS serials are generated once and kept in smbios.json,
which must stay out of version control.

    python3 build-efi.py                    daily build for the internal SSD
    PROFILE=installer python3 build-efi.py  verbose build for the USB installer
"""
import json
import os
import plistlib
import shutil
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OC = ROOT / "build" / "oc"
KEXT_SRC = ROOT / "build" / "k"
OUT = ROOT / "efi" / "EFI"
SMBIOS_FILE = ROOT / "smbios.json"
MODEL = "Macmini8,1"
# The installer profile boots verbose, shows every picker entry, logs to a file on
# the EFI partition and uses the default USB map. It is also the rescue stick.
INSTALLER = os.environ.get("PROFILE") == "installer"

SSDTS = [
    ("SSDT-PLUG.aml", "CPU power management (plugin-type on PR00)"),
    ("SSDT-EC-USBX.aml", "Fake EC and USB power properties"),
    ("SSDT-AWAC-DISABLE.aml", "Disable AWAC clock, enable RTC"),
    ("SSDT-PMC.aml", "PMC device for native NVRAM on 300-series"),
]

# Load order matters: Lilu first, VirtualSMC before its plugins.
KEXTS = [
    ("Lilu/Lilu.kext", "Patch engine"),
    ("VirtualSMC/Kexts/VirtualSMC.kext", "SMC emulator"),
    ("VirtualSMC/Kexts/SMCProcessor.kext", "CPU temperature"),
    ("VirtualSMC/Kexts/SMCSuperIO.kext", "Fan readings"),
    ("WhateverGreen/WhateverGreen.kext", "UHD 630 framebuffer patches"),
    ("AppleALC/AppleALC.kext", "Realtek ALC235 audio"),
    ("IntelMausi/IntelMausi.kext", "Intel I219-LM Ethernet"),
    ("NVMeFix/NVMeFix.kext", "NVMe power management (WD SN730)"),
    # Intel Wireless-AC 9560 (CNVi) in the M.2 slot. itlwm shows up as an Ethernet
    # interface managed by the HeliPort app; there is no AirportItlwm for Sequoia.
    ("itlwm/itlwm.kext", "Intel 9560 Wi-Fi"),
    ("IntelBluetooth/IntelBTPatcher.kext", "Intel Bluetooth patches (Lilu plugin)"),
    ("IntelBluetooth/IntelBluetoothFirmware.kext", "Intel 9560 Bluetooth firmware loader"),
    ("BrcmPatchRAM/BlueToolFixup.kext", "Third-party Bluetooth on macOS 12+ (Lilu plugin)"),
    ("USBToolBox/USBToolBox.kext", "USB mapping engine"),
    # usb-map/UTBMap.kext comes from build-usbmap.py. The installer profile uses
    # the default map instead: ports 1-15, all USB 2, nothing left out.
    ("USBToolBox/UTBDefault.kext", "Default USB map (ports 1-15)") if INSTALLER
    else (str(ROOT / "usb-map" / "UTBMap.kext"), "USB port map for the P330 Tiny"),
]

DRIVERS = ["OpenRuntime.efi", "HfsPlus.efi", "ResetNvramEntry.efi"]
TOOLS = ["OpenShell.efi"]


def smbios():
    if SMBIOS_FILE.exists():
        return json.loads(SMBIOS_FILE.read_text())
    tool = OC / "Utilities" / "macserial" / "macserial.linux"
    tool.chmod(0o755)
    out = subprocess.run([str(tool), "-m", MODEL, "-n", "1"],
                         check=True, capture_output=True, text=True).stdout
    serial, mlb = [x.strip() for x in out.strip().split("|")]
    rom = bytearray(os.urandom(6))
    rom[0] &= 0xFE  # unicast address
    data = {"model": MODEL, "serial": serial, "mlb": mlb,
            "uuid": str(uuid.uuid4()).upper(), "rom": rom.hex()}
    SMBIOS_FILE.write_text(json.dumps(data, indent=2) + "\n")
    SMBIOS_FILE.chmod(0o600)
    return data


def strip_notes(node):
    """Drop the #WARNING / #INFO helper keys the sample ships with."""
    if isinstance(node, dict):
        for key in [k for k in node if k.startswith("#")]:
            del node[key]
        for value in node.values():
            strip_notes(value)
    elif isinstance(node, list):
        for value in node:
            strip_notes(value)


def kext_entry(name, comment):
    info = plistlib.loads((OUT / "OC" / "Kexts" / name / "Contents" / "Info.plist").read_bytes())
    exe = info.get("CFBundleExecutable", "")
    has_exe = exe and (OUT / "OC" / "Kexts" / name / "Contents" / "MacOS" / exe).exists()
    return {
        "Arch": "x86_64", "BundlePath": name, "Comment": comment, "Enabled": True,
        "ExecutablePath": f"Contents/MacOS/{exe}" if has_exe else "",
        "MaxKernel": "", "MinKernel": "", "PlistPath": "Contents/Info.plist",
    }


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    oc = OUT / "OC"
    for sub in ("ACPI", "Drivers", "Kexts", "Tools", "Resources"):
        (oc / sub).mkdir(parents=True)
    shutil.copytree(OC / "X64" / "EFI" / "BOOT", OUT / "BOOT")
    shutil.copy(OC / "X64" / "EFI" / "OC" / "OpenCore.efi", oc)

    for name, _ in SSDTS:
        shutil.copy(OC / "Docs" / "AcpiSamples" / "Binaries" / name, oc / "ACPI")
    for name in DRIVERS:
        src = OC / "X64" / "EFI" / "OC" / "Drivers" / name
        shutil.copy(src if src.exists() else ROOT / "downloads" / name, oc / "Drivers")
    for name in TOOLS:
        shutil.copy(OC / "X64" / "EFI" / "OC" / "Tools" / name, oc / "Tools")
    for path, _ in KEXTS:
        shutil.copytree(KEXT_SRC / path, oc / "Kexts" / Path(path).name, symlinks=True)

    cfg = plistlib.loads((OC / "Docs" / "Sample.plist").read_bytes())
    strip_notes(cfg)

    cfg["ACPI"]["Add"] = [{"Comment": c, "Enabled": True, "Path": n} for n, c in SSDTS]
    cfg["ACPI"]["Delete"] = []
    cfg["ACPI"]["Patch"] = []

    cfg["Booter"]["MmioWhitelist"] = []
    cfg["Booter"]["Patch"] = []
    cfg["Booter"]["Quirks"].update({
        "DevirtualiseMmio": True,
        "EnableWriteUnprotector": False,
        "ProtectUefiServices": True,
        "RebuildAppleMemoryMap": True,
        "SyncRuntimePermissions": True,
    })

    hdmi = bytes.fromhex("00080000")
    on = bytes.fromhex("01000000")
    igpu = {
        "AAPL,ig-platform-id": bytes.fromhex("07009B3E"),
        # BIOS has no DVMT pre-alloc option, so patch the framebuffer to fit 32MB.
        "framebuffer-patch-enable": on,
        "framebuffer-stolenmem": bytes.fromhex("00003001"),
    }
    # Connector layout, confirmed from the running system: con0 is the DisplayPort
    # (left at the stock DP type, bus ID 5), con1 and con2 are the two HDMI ports.
    # The stock framebuffer types every connector as DisplayPort; on the Cannon
    # Point PCH (Q370) the HDMI DDC pins for ports C/D are 2/4, so the HDMI ports
    # need both the type and the bus ID patched or the screen stays black.
    for con, bus_id in ((1, 0x02), (2, 0x04)):
        igpu[f"framebuffer-con{con}-enable"] = on
        igpu[f"framebuffer-con{con}-type"] = hdmi
        igpu[f"framebuffer-con{con}-busid"] = bytes([bus_id, 0, 0, 0])
    # Without this the HDMI monitor stays black after wake until it is replugged.
    igpu["force-online"] = on
    cfg["DeviceProperties"]["Add"] = {
        "PciRoot(0x0)/Pci(0x2,0x0)": igpu,
        # AppleALC layout 17: "ALC235 for Lenovo ThinkCentre Tiny M720q".
        "PciRoot(0x0)/Pci(0x1f,0x3)": {"layout-id": (17).to_bytes(4, "little")},
    }
    cfg["DeviceProperties"]["Delete"] = {}

    cfg["Kernel"]["Add"] = [kext_entry(Path(p).name, c) for p, c in KEXTS]
    for section in ("Block", "Force", "Patch"):
        cfg["Kernel"][section] = []
    cfg["Kernel"]["Quirks"].update({
        "AppleXcpmCfgLock": True,   # MSR 0xE2 is locked and the BIOS has no toggle
        "DisableIoMapper": True,
        "PanicNoKextDump": True,
        "PowerTimeoutKernelPanic": True,
        "XhciPortLimit": False,
    })

    cfg["Misc"]["Boot"].update({"HideAuxiliary": not INSTALLER, "Timeout": 5 if INSTALLER else 3})
    # Target 3 logs to screen only; 67 also writes a file to the ESP on every boot.
    cfg["Misc"]["Debug"].update({"AppleDebug": INSTALLER, "ApplePanic": True,
                                 "DisableWatchDog": INSTALLER, "Target": 67 if INSTALLER else 3})
    cfg["Misc"]["Security"].update({"AllowSetDefault": True, "ScanPolicy": 0,
                                    "Vault": "Optional",
                                    # Default makes the Sequoia installer loop on this
                                    # T2-era SMBIOS; revisit once macOS is installed.
                                    "SecureBootModel": "Disabled"})
    cfg["Misc"]["Entries"] = []
    cfg["Misc"]["Tools"] = [{
        "Arguments": "", "Auxiliary": True, "Comment": "UEFI shell", "Enabled": True,
        "Flavour": "OpenShell:UEFIShell:Shell", "FullNvramAccess": False,
        "Name": "UEFI Shell", "Path": "OpenShell.efi", "RealPath": False, "TextMode": False,
    }]

    nvram = cfg["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]
    nvram.pop("ForceDisplayRotationInEFI", None)
    nvram.update({
        "boot-args": "-v keepsyms=1 debug=0x100" if INSTALLER else "keepsyms=1",
        # BlueToolFixup 2.7+ needs these two set for Bluetooth on macOS 14+.
        "bluetoothExternalDongleFailed": bytes(1),
        "bluetoothInternalControllerInfo": bytes(14),
        "csr-active-config": bytes(4),
        "prev-lang:kbd": b"en-US:0",
    })
    cfg["NVRAM"]["Delete"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"] = [
        "boot-args", "bluetoothExternalDongleFailed", "bluetoothInternalControllerInfo"]

    ids = smbios()
    cfg["PlatformInfo"]["Generic"].update({
        "SystemProductName": ids["model"], "SystemSerialNumber": ids["serial"],
        "MLB": ids["mlb"], "SystemUUID": ids["uuid"], "ROM": bytes.fromhex(ids["rom"]),
    })

    cfg["UEFI"]["Drivers"] = [{"Arguments": "", "Comment": "", "Enabled": True, "HideVerbose": False,
                               "LoadEarly": False, "Path": n} for n in DRIVERS]

    with open(oc / "config.plist", "wb") as fh:
        plistlib.dump(cfg, fh, sort_keys=True)

    validator = OC / "Utilities" / "ocvalidate" / "ocvalidate.linux"
    validator.chmod(0o755)
    subprocess.run([str(validator), str(oc / "config.plist")], check=False)


if __name__ == "__main__":
    main()
