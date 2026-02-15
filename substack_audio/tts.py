"""Text-to-speech: chunking, ElevenLabs API, MP3 concatenation."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List

from elevenlabs.client import ElevenLabs


def split_text(text: str, max_len: int) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    cur = ""

    for para in paragraphs:
        candidate = f"{cur}\n\n{para}".strip() if cur else para
        if len(candidate) <= max_len:
            cur = candidate
            continue

        if cur:
            chunks.append(cur)
            cur = ""

        while len(para) > max_len:
            cut = para.rfind(" ", 0, max_len)
            if cut == -1:
                cut = max_len
            chunks.append(para[:cut].strip())
            para = para[cut:].strip()

        cur = para

    if cur:
        chunks.append(cur)

    return chunks


def elevenlabs_tts(
    client: ElevenLabs,
    voice_id: str,
    model_id: str,
    output_format: str,
    text: str,
) -> bytes:
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
    )
    if isinstance(audio, (bytes, bytearray)):
        return bytes(audio)
    return b"".join(chunk for chunk in audio if isinstance(chunk, (bytes, bytearray)))


def concat_mp3(parts: List[Path], output_file: Path) -> None:
    if len(parts) == 1:
        output_file.write_bytes(parts[0].read_bytes())
        return

    ffmpeg_available = False
    try:
        subprocess.run(["ffmpeg", "-version"], check=False, capture_output=True)
        ffmpeg_available = True
    except FileNotFoundError:
        ffmpeg_available = False

    if ffmpeg_available:
        with tempfile.NamedTemporaryFile("w", delete=False) as list_file:
            for part in parts:
                list_file.write(f"file '{part.resolve()}'\n")
            list_path = list_file.name

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_path,
                    "-c",
                    "copy",
                    str(output_file),
                ],
                check=True,
                capture_output=True,
            )
            return
        finally:
            try:
                os.unlink(list_path)
            except OSError:
                pass

    with output_file.open("wb") as out:
        for part in parts:
            out.write(part.read_bytes())
