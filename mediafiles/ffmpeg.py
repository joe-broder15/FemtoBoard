"""WebM inspection and poster-frame generation via FFmpeg/FFprobe.

Always invoked as an argument vector, never through a shell, and always
against a server-generated temporary path -- never the client's original
filename (design doc 80.12).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from django.conf import settings

from mediafiles.validation import MediaValidationError

_ALLOWED_VIDEO_CODECS = {"vp8", "vp9", "av1"}


@dataclass(frozen=True)
class WebmMetadata:
    width: int
    height: int
    duration_seconds: float


def probe_webm(path: str) -> WebmMetadata:
    cmd = [
        settings.FEMTOBOARD_FFPROBE_BINARY,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            timeout=settings.FEMTOBOARD_FFMPEG_TIMEOUT_SECONDS,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise MediaValidationError("Could not inspect WebM content") from exc

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaValidationError("WebM inspection returned unexpected output") from exc

    streams = data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise MediaValidationError("WebM file has no video stream")

    stream = video_streams[0]
    if stream.get("codec_name") not in _ALLOWED_VIDEO_CODECS:
        raise MediaValidationError("Unsupported WebM video codec")

    fmt = data.get("format", {})
    try:
        width = int(stream["width"])
        height = int(stream["height"])
        duration = float(fmt.get("duration") or stream.get("duration") or 0)
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaValidationError("Could not determine WebM dimensions/duration") from exc

    if width <= 0 or height <= 0:
        raise MediaValidationError("Invalid WebM dimensions")
    if duration <= 0 or duration > settings.FEMTOBOARD_MAX_WEBM_DURATION_SECONDS:
        raise MediaValidationError("WebM duration outside allowed range")

    return WebmMetadata(width=width, height=height, duration_seconds=duration)


def extract_poster_frame(input_path: str, output_path: str) -> None:
    cmd = [
        settings.FEMTOBOARD_FFMPEG_BINARY,
        "-y",
        "-nostdin",
        "-ss",
        "00:00:00.5",
        "-i",
        input_path,
        "-frames:v",
        "1",
        "-f",
        "image2",
        output_path,
    ]
    try:
        subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            timeout=settings.FEMTOBOARD_FFMPEG_TIMEOUT_SECONDS,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise MediaValidationError("Could not generate a poster frame for this WebM") from exc
