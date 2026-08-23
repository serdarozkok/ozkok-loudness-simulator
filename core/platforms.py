"""
Streaming platform preset definitions.

Each preset encodes the loudness target (LUFS), codec, bitrate, and
container format used by a specific streaming tier. The ``turns_up``
flag indicates whether the platform boosts tracks quieter than its
target (Apple Music does; Spotify Normal, YouTube, and Tidal do not).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlatformPreset:
    """Immutable description of a streaming platform's audio pipeline."""

    name: str
    display_name: str
    target_lufs: Optional[float]
    codec: Optional[str]        # FFmpeg codec name: 'libvorbis', 'aac', or None
    bitrate: Optional[int]      # Bits per second (e.g. 160_000)
    container: Optional[str]    # Container format: 'ogg', 'adts', or None
    turns_up: bool = False      # Whether quiet tracks are boosted


# ── Registry ────────────────────────────────────────────────────────
PLATFORM_PRESETS: dict[str, PlatformPreset] = {
    "spotify_loud": PlatformPreset(
        name="spotify_loud",
        display_name="Spotify Loud  (-11 LUFS)",
        target_lufs=-11.0,
        codec="libvorbis",
        bitrate=160_000,
        container="ogg",
    ),
    "spotify_normal": PlatformPreset(
        name="spotify_normal",
        display_name="Spotify Normal  (-14 LUFS)",
        target_lufs=-14.0,
        codec="libvorbis",
        bitrate=160_000,
        container="ogg",
    ),
    "spotify_quiet": PlatformPreset(
        name="spotify_quiet",
        display_name="Spotify Quiet  (-19 LUFS)",
        target_lufs=-19.0,
        codec="libvorbis",
        bitrate=160_000,
        container="ogg",
    ),
    "spotify_high": PlatformPreset(
        name="spotify_high",
        display_name="Spotify High  (320k -14 LUFS)",
        target_lufs=-14.0,
        codec="libvorbis",
        bitrate=320_000,
        container="ogg",
    ),
    "apple_music": PlatformPreset(
        name="apple_music",
        display_name="Apple Music  (-16 LUFS)",
        target_lufs=-16.0,
        codec="aac",
        bitrate=256_000,
        container="adts",
        turns_up=True,
    ),
    "youtube_music": PlatformPreset(
        name="youtube_music",
        display_name="YouTube Music  (-14 LUFS)",
        target_lufs=-14.0,
        codec="aac",
        bitrate=256_000,
        container="adts",
    ),
    "tidal": PlatformPreset(
        name="tidal",
        display_name="TIDAL  (-14 LUFS)",
        target_lufs=-14.0,
        codec="aac",
        bitrate=256_000,
        container="adts",
    ),
    "amazon": PlatformPreset(
        name="amazon",
        display_name="Amazon Music  (-14 LUFS)",
        target_lufs=-14.0,
        codec="aac",
        bitrate=256_000,
        container="adts",
        turns_up=True,
    ),
    "deezer": PlatformPreset(
        name="deezer",
        display_name="Deezer  (-15 LUFS)",
        target_lufs=-15.0,
        codec="aac",
        bitrate=256_000,
        container="adts",
    ),
    "unnormalized": PlatformPreset(
        name="unnormalized",
        display_name="Unnormalized",
        target_lufs=None,
        codec=None,
        bitrate=None,
        container=None,
    ),
}

# Ordered list of keys for UI display
PLATFORM_ORDER: list[str] = [
    "spotify_normal",
    "apple_music",
    "youtube_music",
    "tidal",
    "amazon",
    "deezer",
]
