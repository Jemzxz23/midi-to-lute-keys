# MIDI → Lute Keys Player (GUI)

A Python GUI that plays `.mid/.midi` files by converting MIDI notes into QWERTY keypresses for a 7-note solfege “lute/lyre” layout.

- Hotkeys: **F4** = start, **F3** = stop
- Adjustable speed (up to **5× faster**) while playing
- Custom key mapping:
  - Upper row: `Q W E R T Y U` = `do' re' mi' fa' sol' la' si'`
  - `I` = `do''`
  - Lower row: `A S D F G H J` = `do re mi fa sol la si`

> Note: This project sends automated keypresses. Use responsibly and only where allowed.

## Requirements

- Windows 10/11
- Python 3.10+ recommended

## Installation

If `pip` isn’t recognized, use `py -m pip`:

```powershell
py -m pip install --upgrade pip
py -m pip install mido pydirectinput keyboard
