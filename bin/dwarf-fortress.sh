#!/usr/bin/env bash
# Dwarf Fortress launcher for Moonlight - pure wine, no gamescope
export DISPLAY=:0
export WINEPREFIX="$HOME/.wine"
export WINEARCH=win64
export WINEDEBUG=-all

cd "/mnt/HDD1-Games/Dwarf Fortress"
exec wine "Dwarf Fortress.exe"