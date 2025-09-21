"""Metadata domain logic for Music Metadata Tagger."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

import pandas as pd
import streamlit as st
from mutagen import File as MutagenFile
from mutagen.asf import ASF
from mutagen.flac import FLAC
from mutagen.id3 import (
    COMM,
    ID3,
    ID3NoHeaderError,
    POPM,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TIT3,
    TPE1,
    TPE2,
    TRCK,
)
from mutagen.mp4 import MP4


@dataclass
class UpdateResult:
    path: Path
    success: bool
    message: str = ""


RATING_TO_POPM: Dict[int, int] = {0: 0, 1: 1, 2: 64, 3: 128, 4: 196, 5: 255}
RATING_TO_MP4: Dict[int, int] = {0: 0, 1: 20, 2: 40, 3: 60, 4: 80, 5: 100}
RATING_TO_ASF: Dict[int, int] = {0: 0, 1: 1, 2: 25, 3: 50, 4: 75, 5: 99}
RATING_CHOICES: List[Tuple[str, Optional[int]]] = [
    ("Skip", None),
    ("0 stars - Unrated", 0),
    ("1 star", 1),
    ("2 stars", 2),
    ("3 stars", 3),
    ("4 stars", 4),
    ("5 stars", 5),
]
RATING_LABEL_TO_VALUE: Dict[str, Optional[int]] = {
    label: value for label, value in RATING_CHOICES
}

FIELD_DEFS: List[Dict[str, Any]] = [
    {
        "name": "title",
        "label": "Title",
        "type": "text",
        "placeholder": "e.g. Pictures Of You",
        "help": "Primary track title.",
    },
    {
        "name": "subtitle",
        "label": "Subtitle",
        "type": "text",
        "placeholder": "Optional secondary title",
    },
    {
        "name": "rating",
        "label": "Rating",
        "type": "rating",
        "help": "0-5 star rating as shown in Windows Explorer.",
    },
    {
        "name": "comments",
        "label": "Comments",
        "type": "textarea",
        "placeholder": "Notes about the track",
    },
    {
        "name": "artists",
        "label": "Contributing artists",
        "type": "text",
        "placeholder": "Separate names with commas or semicolons",
    },
    {
        "name": "album_artist",
        "label": "Album artist",
        "type": "text",
        "placeholder": "e.g. Anyma",
    },
    {
        "name": "album",
        "label": "Album",
        "type": "text",
        "placeholder": "e.g. Genesys II",
    },
    {
        "name": "year",
        "label": "Year",
        "type": "text",
        "placeholder": "e.g. 2024",
    },
    {
        "name": "track_number",
        "label": "Track number",
        "type": "text",
        "placeholder": "e.g. 1 or 1/10",
    },
    {
        "name": "genre",
        "label": "Genre",
        "type": "text",
        "placeholder": "e.g. Dance",
    },
]
FIELD_LABELS: Dict[str, str] = {cfg["name"]: cfg["label"] for cfg in FIELD_DEFS}


def sanitize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_people(value: Any) -> Optional[List[str]]:
    text = sanitize_text(value)
    if not text:
        return None
    parts = [part.strip() for part in re.split(r"[;,]", text) if part.strip()]
    return parts or None


def parse_year(value: Any) -> Optional[str]:
    text = sanitize_text(value)
    if not text:
        return None
    if not re.match(r"^\d{4}(-\d{1,2}(-\d{1,2})?)?$", text):
        raise ValueError("Use YYYY or YYYY-MM-DD format.")
    return text


def parse_track_number(value: Any) -> Optional[Tuple[int, Optional[int]]]:
    text = sanitize_text(value)
    if not text:
        return None
    if "/" in text:
        first, second = text.split("/", 1)
    else:
        first, second = text, ""
    try:
        track = int(first.strip())
    except ValueError as exc:
        raise ValueError("Track must be an integer.") from exc
    total: Optional[int] = None
    if second.strip():
        try:
            total = int(second.strip())
        except ValueError as exc:
            raise ValueError("Total tracks must be an integer.") from exc
    if track < 0:
        raise ValueError("Track must be positive.")
    if total is not None and total < track:
        raise ValueError("Total tracks cannot be smaller than the track number.")
    return track, total


FIELD_PARSERS: Dict[str, Any] = {
    "title": sanitize_text,
    "subtitle": sanitize_text,
    "rating": lambda value: value,
    "comments": sanitize_text,
    "artists": parse_people,
    "album_artist": sanitize_text,
    "album": sanitize_text,
    "year": parse_year,
    "track_number": parse_track_number,
    "genre": sanitize_text,
}


def collect_updates(raw_inputs: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    updates: Dict[str, Any] = {}
    errors: List[str] = []
    for name, raw_value in raw_inputs.items():
        parser = FIELD_PARSERS.get(name, lambda v: v)
        try:
            parsed = parser(raw_value)
        except ValueError as exc:
            errors.append(f"{FIELD_LABELS.get(name, name)}: {exc}")
            continue
        if parsed is None:
            continue
        if isinstance(parsed, list) and not parsed:
            continue
        updates[name] = parsed
    return updates, errors


class BaseTagHandler:
    SUFFIXES: Tuple[str, ...] = ()

    def __init__(self, path: Path) -> None:
        self.path = path
        self.load()

    @classmethod
    def supports(cls, suffix: str) -> bool:
        return suffix.lower() in cls.SUFFIXES

    def load(self) -> None:
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def set_field(self, field: str, value: Any) -> None:
        raise NotImplementedError

    def apply(self, updates: Dict[str, Any]) -> None:
        for field, value in updates.items():
            self.set_field(field, value)
        self.save()


class MP3TagHandler(BaseTagHandler):
    SUFFIXES = (".mp3",)

    def load(self) -> None:
        try:
            self.audio = ID3(self.path)
        except ID3NoHeaderError:
            self.audio = ID3()

    def save(self) -> None:
        self.audio.save(self.path, v2_version=3)

    def set_field(self, field: str, value: Any) -> None:
        if field == "title":
            self.audio.delall("TIT2")
            self.audio.add(TIT2(encoding=3, text=[value]))
        elif field == "subtitle":
            self.audio.delall("TIT3")
            self.audio.add(TIT3(encoding=3, text=[value]))
        elif field == "comments":
            self.audio.delall("COMM")
            self.audio.add(COMM(encoding=3, lang="eng", desc="", text=[value]))
        elif field == "artists":
            self.audio.delall("TPE1")
            self.audio.add(TPE1(encoding=3, text=value))
        elif field == "album_artist":
            self.audio.delall("TPE2")
            self.audio.add(TPE2(encoding=3, text=[value]))
        elif field == "album":
            self.audio.delall("TALB")
            self.audio.add(TALB(encoding=3, text=[value]))
        elif field == "year":
            self.audio.delall("TDRC")
            self.audio.add(TDRC(encoding=3, text=[value]))
        elif field == "track_number":
            track, total = value
            track_text = f"{track}/{total}" if total else str(track)
            self.audio.delall("TRCK")
            self.audio.add(TRCK(encoding=3, text=[track_text]))
        elif field == "genre":
            self.audio.delall("TCON")
            self.audio.add(TCON(encoding=3, text=[value]))
        elif field == "rating":
            self.audio.delall("POPM")
            self.audio.add(
                POPM(
                    email="Windows Media Player 9 Series",
                    rating=RATING_TO_POPM.get(int(value), 0),
                    count=0,
                )
            )


class FLACTagHandler(BaseTagHandler):
    SUFFIXES = (".flac",)

    def load(self) -> None:
        self.audio = FLAC(self.path)

    def save(self) -> None:
        self.audio.save()

    def set_field(self, field: str, value: Any) -> None:
        if field == "title":
            self.audio["title"] = [value]
        elif field == "subtitle":
            self.audio["subtitle"] = [value]
        elif field == "comments":
            self.audio["comment"] = [value]
        elif field == "artists":
            self.audio["artist"] = value
        elif field == "album_artist":
            self.audio["albumartist"] = [value]
        elif field == "album":
            self.audio["album"] = [value]
        elif field == "year":
            self.audio["date"] = [value]
        elif field == "track_number":
            track, total = value
            self.audio["tracknumber"] = [str(track)]
            if total:
                self.audio["tracktotal"] = [str(total)]
            elif "tracktotal" in self.audio:
                del self.audio["tracktotal"]
        elif field == "genre":
            self.audio["genre"] = [value]
        elif field == "rating":
            self.audio["rating"] = [str(value)]


class MP4TagHandler(BaseTagHandler):
    SUFFIXES = (".m4a", ".m4b", ".m4p", ".m4r", ".mp4", ".m4v")

    def load(self) -> None:
        self.audio = MP4(self.path)

    def save(self) -> None:
        self.audio.save()

    def set_field(self, field: str, value: Any) -> None:
        if field == "title":
            self.audio["\xa9nam"] = [value]
        elif field == "subtitle":
            self.audio["----:com.apple.iTunes:SUBTITLE"] = [value.encode("utf-8")]
        elif field == "comments":
            self.audio["\xa9cmt"] = [value]
        elif field == "artists":
            self.audio["\xa9ART"] = value
        elif field == "album_artist":
            self.audio["aART"] = [value]
        elif field == "album":
            self.audio["\xa9alb"] = [value]
        elif field == "year":
            self.audio["\xa9day"] = [value]
        elif field == "track_number":
            track, total = value
            self.audio["trkn"] = [(track, total or 0)]
        elif field == "genre":
            self.audio["\xa9gen"] = [value]
        elif field == "rating":
            self.audio["rate"] = [RATING_TO_MP4.get(int(value), 0)]


class ASFTagHandler(BaseTagHandler):
    SUFFIXES = (".wma", ".asf")

    def load(self) -> None:
        self.audio = ASF(self.path)

    def save(self) -> None:
        self.audio.save()

    def set_field(self, field: str, value: Any) -> None:
        if field == "title":
            self.audio["Title"] = value
        elif field == "subtitle":
            self.audio["WM/SubTitle"] = value
        elif field == "comments":
            self.audio["WM/Comments"] = value
        elif field == "artists":
            self.audio["Author"] = "; ".join(value)
        elif field == "album_artist":
            self.audio["WM/AlbumArtist"] = value
        elif field == "album":
            self.audio["WM/AlbumTitle"] = value
        elif field == "year":
            self.audio["WM/Year"] = value
        elif field == "track_number":
            track, total = value
            self.audio["WM/TrackNumber"] = str(track)
            if total:
                self.audio["WM/TrackTotal"] = str(total)
            elif "WM/TrackTotal" in self.audio:
                del self.audio["WM/TrackTotal"]
        elif field == "genre":
            self.audio["WM/Genre"] = value
        elif field == "rating":
            self.audio["WM/SharedUserRating"] = RATING_TO_ASF.get(int(value), 0)


HANDLER_CLASSES: List[Type[BaseTagHandler]] = [
    MP3TagHandler,
    MP4TagHandler,
    FLACTagHandler,
    ASFTagHandler,
]
SUFFIX_HANDLER_MAP: Dict[str, Type[BaseTagHandler]] = {}
for handler_cls in HANDLER_CLASSES:
    for suffix in handler_cls.SUFFIXES:
        SUFFIX_HANDLER_MAP[suffix] = handler_cls
SUPPORTED_EXTENSIONS: str = ", ".join(sorted(SUFFIX_HANDLER_MAP.keys()))


def get_handler_for_path(path: Path) -> Optional[BaseTagHandler]:
    handler_cls = SUFFIX_HANDLER_MAP.get(path.suffix.lower())
    if not handler_cls:
        return None
    return handler_cls(path)


def list_audio_files(folder: Path, include_subfolders: bool) -> List[Path]:
    if include_subfolders:
        iterator = folder.rglob("*")
    else:
        iterator = folder.glob("*")
    files = [
        path
        for path in iterator
        if path.is_file() and path.suffix.lower() in SUFFIX_HANDLER_MAP
    ]
    files.sort()
    return files


def join_values(values: Iterable[Any]) -> str:
    if isinstance(values, (list, tuple, set)):
        parts = [str(value).strip() for value in values if str(value).strip()]
        return "; ".join(parts)
    if values is None:
        return ""
    return str(values)


def read_metadata_preview(path: Path) -> Dict[str, str]:
    preview: Dict[str, str] = {
        "file": path.name,
        "title": "",
        "artists": "",
        "album": "",
        "year": "",
        "track": "",
        "genre": "",
        "path": str(path),
    }
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        audio = None
    tags = getattr(audio, "tags", None)
    if tags:
        preview["title"] = join_values(tags.get("title", []))
        preview["artists"] = join_values(tags.get("artist", []))
        preview["album"] = join_values(tags.get("album", []))
        preview["year"] = join_values(tags.get("date", []) or tags.get("year", []))
        preview["track"] = join_values(tags.get("tracknumber", []))
        preview["genre"] = join_values(tags.get("genre", []))
        return preview
    if path.suffix.lower() in {".wma", ".asf"}:
        try:
            asf = ASF(path)
            tags = asf.tags or {}
            preview["title"] = join_values([tag.value for tag in tags.get("Title", [])])
            preview["artists"] = join_values(
                [tag.value for tag in tags.get("Author", [])]
            )
            preview["album"] = join_values(
                [tag.value for tag in tags.get("WM/AlbumTitle", [])]
            )
            preview["year"] = join_values([tag.value for tag in tags.get("WM/Year", [])])
            preview["track"] = join_values(
                [tag.value for tag in tags.get("WM/TrackNumber", [])]
            )
            preview["genre"] = join_values([tag.value for tag in tags.get("WM/Genre", [])])
        except Exception:
            pass
    return preview


def build_metadata_table(paths: List[Path], limit: int = 200) -> pd.DataFrame:
    if not paths:
        return pd.DataFrame(columns=["file", "title", "artists", "album", "year", "track", "genre", "path"])
    sample = paths if len(paths) <= limit else paths[:limit]
    records = [read_metadata_preview(path) for path in sample]
    df = pd.DataFrame(records)
    return df[["file", "title", "artists", "album", "year", "track", "genre", "path"]]


def apply_metadata_to_files(paths: List[Path], updates: Dict[str, Any]) -> List[UpdateResult]:
    results: List[UpdateResult] = []
    total = len(paths)
    progress = st.progress(0.0) if total else None
    for index, path in enumerate(paths, start=1):
        try:
            handler = get_handler_for_path(path)
            if not handler:
                raise ValueError(f"Unsupported file type: {path.suffix}")
            handler.apply(updates)
            results.append(UpdateResult(path=path, success=True))
        except Exception as exc:  # noqa: BLE001 - surface errors to the UI
            results.append(UpdateResult(path=path, success=False, message=str(exc)))
        if progress:
            progress.progress(index / total)
    if progress:
        progress.empty()
    return results


def reset_bulk_metadata_inputs() -> None:
    """Clear stored widget state for the metadata form."""
    for field_config in FIELD_DEFS:
        st.session_state.pop(f"field_{field_config['name']}", None)
