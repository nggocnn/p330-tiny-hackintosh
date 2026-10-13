#!/bin/sh
# Copy the staged OpenCore EFI onto the internal SSD's EFI partition.
# Run with sudo on the P330. The previous EFI folder, if any, is kept as a backup.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)/EFI"
DISK=disk0
diskutil info "$DISK" | grep -q "SN730" || { echo "disk0 is not the SN730, stopping"; exit 1; }
[ -f "$SRC/OC/config.plist" ] || { echo "no staged EFI at $SRC"; exit 1; }
diskutil mount "${DISK}s1"
ESP=$(diskutil info "${DISK}s1" | awk -F': *' '/Mount Point/ {print $2}')
[ -d "$ESP" ] || { echo "EFI partition did not mount"; exit 1; }
[ -d "$ESP/EFI" ] && mv "$ESP/EFI" "$ESP/EFI.bak.$(date +%Y%m%d-%H%M%S)"
cp -RX "$SRC" "$ESP/EFI"
find "$ESP/EFI" -name '._*' -delete
echo "installed files: $(find "$ESP/EFI" -type f | wc -l | tr -d ' ')"
shasum -a 256 "$ESP/EFI/OC/config.plist" "$SRC/OC/config.plist"
ls "$ESP"
diskutil unmount "${DISK}s1"
echo "done"
