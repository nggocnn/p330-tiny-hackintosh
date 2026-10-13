#!/usr/bin/env python3
"""Download and unpack OpenCore and the kexts that build-efi.py expects.

Archives go to downloads/, unpacked trees to build/. Both are ignored by git.
Versions are pinned to the ones this build was tested with.
"""
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT / "downloads"
BUILD = ROOT / "build"
GH = "https://github.com"

# (folder under build/, URL)
ARCHIVES = [
    ("oc", f"{GH}/acidanthera/OpenCorePkg/releases/download/1.0.8/OpenCore-1.0.8-RELEASE.zip"),
    ("k/Lilu", f"{GH}/acidanthera/Lilu/releases/download/1.7.2/Lilu-1.7.2-RELEASE.zip"),
    ("k/VirtualSMC", f"{GH}/acidanthera/VirtualSMC/releases/download/1.3.8/VirtualSMC-1.3.8-RELEASE.zip"),
    ("k/WhateverGreen", f"{GH}/acidanthera/WhateverGreen/releases/download/1.7.1/WhateverGreen-1.7.1-RELEASE.zip"),
    ("k/AppleALC", f"{GH}/acidanthera/AppleALC/releases/download/1.9.8/AppleALC-1.9.8-RELEASE.zip"),
    ("k/IntelMausi", f"{GH}/acidanthera/IntelMausi/releases/download/1.0.8/IntelMausi-1.0.8-RELEASE.zip"),
    ("k/NVMeFix", f"{GH}/acidanthera/NVMeFix/releases/download/1.1.3/NVMeFix-1.1.3-RELEASE.zip"),
    ("k/USBToolBox", f"{GH}/USBToolBox/kext/releases/download/1.2.0/USBToolBox-1.2.0-RELEASE.zip"),
    ("k/itlwm", f"{GH}/OpenIntelWireless/itlwm/releases/download/v2.3.0/itlwm_v2.3.0_stable.kext.zip"),
    ("k/IntelBluetooth", f"{GH}/OpenIntelWireless/IntelBluetoothFirmware/releases/download/v2.4.0/IntelBluetooth-v2.4.0.zip"),
    ("k/BrcmPatchRAM", f"{GH}/acidanthera/BrcmPatchRAM/releases/download/2.7.2/BrcmPatchRAM-2.7.2-RELEASE.zip"),
]

# (destination relative to the repo, URL)
FILES = [
    ("downloads/HfsPlus.efi", f"{GH}/acidanthera/OcBinaryData/raw/master/Drivers/HfsPlus.efi"),
    ("build/utb_template.plist", "https://raw.githubusercontent.com/USBToolBox/tool/master/resources/Info.plist"),
]


def fetch(url, dest):
    if dest.exists():
        return
    print(f"downloading {dest.name}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, open(dest, "wb") as fh:
        shutil.copyfileobj(response, fh)


def unpack(archive, dest):
    """Unpack with the unix modes stored in the zip, so the kext binaries stay executable."""
    if dest.exists():
        shutil.rmtree(dest)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            path = Path(zf.extract(info, dest))
            mode = info.external_attr >> 16
            if mode and not info.is_dir():
                path.chmod(mode & 0o777)


def main():
    for folder, url in ARCHIVES:
        archive = DOWNLOADS / url.rsplit("/", 1)[1]
        fetch(url, archive)
        unpack(archive, BUILD / folder)
    for dest, url in FILES:
        fetch(url, ROOT / dest)
    print("done")


if __name__ == "__main__":
    main()
