# Music Lyriz

Music Lyriz is a Windows desktop karaoke lyrics viewer. The project is being built in phases so every milestone stays runnable.

## Current Status

Completed:

- Project structure
- JSON configuration loader/saver
- Rotating application logging
- Modern dark PySide6 main window
- Keyboard shortcuts
- Hide-to-tray plumbing
- Single-instance startup guard
- Startup-safe settings validation and repair
- Windows system audio monitoring through WASAPI loopback
- Audio output device selection with a Windows-default option
- Windows media-session recognition provider for players that expose title/artist metadata
- LRCLIB lyrics lookup with synced LRC priority and plain-lyrics fallback
- Genius plain-lyrics fallback when LRCLIB has no result
- Local lyrics cache
- Fullscreen stage mode with keep-awake display behavior and poster-derived colors
- High-resolution album artwork lookup with Windows thumbnail fallback
- Fullscreen media controls for previous, play/pause, and next
- Selectable lyric animations: glow and line-by-line
- Windows packaging scripts for a bundled desktop build and installer
- Stable interfaces for future fingerprint recognition and lyrics modules
- Unit tests for configuration, audio device selection, UI construction, and LRC parsing

Later phases will fill in audio fingerprint recognition, live LRC synchronization against playback position, settings polish, and packaging polish.

## Run

Python 3.12+ is required by the project spec.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Build Windows App

The Windows build uses PyInstaller to bundle Python, Music Lyriz, and all required packages into `dist\Music Lyriz`. Users do not need Python installed to run that build.

For a single EXE that you can send by itself, build the portable one-file app:

```powershell
.\scripts\build_windows.ps1 -OneFile
```

Output:

```text
dist\Music Lyriz Portable.exe
```

That portable EXE includes Python and the app requirements. The first launch can be slower because Windows has to unpack it before starting.

For the folder-based app, build:

```powershell
.\scripts\build_windows.ps1 -SkipInstaller
```

Important: if you use the folder-based app, send the whole `dist\Music Lyriz` folder. Do not send only `Music Lyriz.exe`, because it needs the `_internal` folder beside it.

To build an installer EXE, install Inno Setup first, then run:

```powershell
winget install --id JRSoftware.InnoSetup -e -s winget
.\scripts\build_windows.ps1
```

Outputs:

```text
dist\Music Lyriz Portable.exe
dist\Music Lyriz\Music Lyriz.exe
dist\installer\MusicLyrizSetup-0.1.0.exe
```

Installed builds store settings, logs, and lyrics cache in `%LOCALAPPDATA%\Music Lyriz`.

## Test

The current non-GUI tests use only the standard library:

```powershell
python -m unittest discover
```

## Structure

```text
audio/          Windows audio capture interface and future WASAPI implementation
recognizer/     Recognition manager and provider contracts
lyrics/         Lyrics search, parsing, synchronization, and cache boundaries
ui/             PySide6 windows, widgets, and theme
utils/          Configuration, logging, paths, and shared helpers
database/       Persistent metadata storage
cache/          Downloaded lyrics and album art
logs/           Rotating application logs
config/         User-editable settings
tests/          Unit tests
main.py         Application entrypoint
```
