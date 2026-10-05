#!/usr/bin/env bash
set -euo pipefail
kit_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
command -v python3 >/dev/null || { echo 'Install python3 first.'; exit 1; }
if ! command -v moonlight >/dev/null; then
  command -v flatpak >/dev/null || { echo 'Install flatpak with your distribution package manager, then rerun.'; exit 1; }
  flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
  flatpak install --user -y flathub com.moonlight_stream.Moonlight
fi
python3 "$kit_dir/linux/setup_crosspaste.py"
echo 'Pair Moonlight and CrossPaste once. See docs/linux-client.md for display placement.'
