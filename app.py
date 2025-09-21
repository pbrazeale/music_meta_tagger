"""Streamlit-based bulk metadata editor for audio files.

Run with:
    streamlit run app.pys
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as components_html
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
    ("0 stars — Unrated", 0),
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
        "help": "0–5 star rating as shown in Windows Explorer.",
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


def render_field(field_config: Dict[str, Any], disabled: bool = False) -> Any:
    name = field_config["name"]
    label = field_config["label"]
    help_text = field_config.get("help")
    placeholder = field_config.get("placeholder", "")
    key = f"field_{name}"
    field_type = field_config.get("type", "text")

    if field_type == "textarea":
        return st.text_area(
            label,
            key=key,
            help=help_text,
            placeholder=placeholder,
            disabled=disabled,
            height=100,
        )
    if field_type == "rating":
        labels = [choice[0] for choice in RATING_CHOICES]
        selected_label = st.selectbox(
            label,
            labels,
            key=key,
            help=help_text,
            disabled=disabled,
        )
        return RATING_LABEL_TO_VALUE[selected_label]
    return st.text_input(
        label,
        key=key,
        help=help_text,
        placeholder=placeholder,
        disabled=disabled,
    )


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



def browse_for_audio_folder() -> None:
    """Open a native folder picker and persist the selection."""
    try:
        from tkinter import Tk, filedialog  # type: ignore
    except Exception:
        st.warning("Folder picker is not available in this environment.")
        return

    folder = ""
    root = None
    try:
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory()
    except Exception as exc:
        st.warning(f"Unable to open the folder picker: {exc}")
    finally:
        if root is not None:
            root.destroy()

    if folder:
        st.session_state["folder_input"] = folder
        st.session_state["folder_path"] = folder


def expand_sidebar() -> None:
    """Expand the sidebar when triggered from the main layout."""
    components_html(
        """
        <script>
        const doc = window.parent.document;
        const ctrl = doc.querySelector('[data-testid="collapsedControl"]');
        if (!ctrl) {
            return;
        }
        const expanded = ctrl.getAttribute('aria-expanded');
        if (expanded === 'false') {
            ctrl.click();
        }
        </script>
        """,
        height=0,
        width=0,
    )

def main() -> None:
    st.set_page_config(page_title="Music Metadata Tagger", layout="wide")
    st.title("Music Metadata Tagger")
    st.caption(
        "Bulk-apply Windows-friendly metadata (Title, Rating, Artists, etc.) to every audio file in a folder."
    )

    if "folder_path" not in st.session_state:
        st.session_state["folder_path"] = ""
    if "folder_input" not in st.session_state:
        st.session_state["folder_input"] = st.session_state["folder_path"]
    if "include_subfolders" not in st.session_state:
        st.session_state["include_subfolders"] = True

    with st.sidebar:
        st.header("Setup")
        st.caption(f"Supported extensions: {SUPPORTED_EXTENSIONS}")
        st.button(
            "Select audio folder",
            on_click=browse_for_audio_folder,
            use_container_width=True,
        )
        st.text_input(
            "Audio folder",
            key="folder_input",
            placeholder="Choose or enter a folder path",
        )
        st.checkbox("Include subfolders", key="include_subfolders")
        load_clicked = st.button("Load folder", use_container_width=True)
        if load_clicked:
            selected = st.session_state["folder_input"].strip()
            st.session_state["folder_path"] = selected
            st.session_state["folder_input"] = selected

    selected_folder = st.session_state["folder_path"].strip()
    include = st.session_state["include_subfolders"]
    folder = Path(selected_folder) if selected_folder else None

    files: List[Path] = []
    if folder:
        if folder.is_dir():
            files = list_audio_files(folder, include)
        else:
            st.error(f"Folder not found: {folder}")

    if not selected_folder:
        st.info("Use the Setup sidebar to choose an audio folder (the 'Select audio folder' button opens File Explorer) and click 'Load folder' when you're ready.")
        if st.button("Open setup sidebar"):
            expand_sidebar()
        return

    st.subheader("Folder overview")
    if files:
        st.write(f"Found **{len(files)}** audio files in `{folder}`.")
        if len(files) > 200:
            st.write("Preview limited to first 200 entries.")
        table = build_metadata_table(files)
        st.dataframe(table, use_container_width=True)
    else:
        st.warning("No supported audio files were found in the selected folder.")

    raw_inputs: Dict[str, Any] = {}
    with st.form("bulk_metadata"):
        st.subheader("Bulk metadata update")
        st.caption("Provide only the fields you want to change; leave others blank to skip them.")
        cols = st.columns(2)
        for index, field_config in enumerate(FIELD_DEFS):
            target_col = cols[index % len(cols)]
            with target_col:
                raw_inputs[field_config["name"]] = render_field(field_config, disabled=not files)
        apply_clicked = st.form_submit_button(
            "Apply metadata to files", disabled=not files
        )

    if not files:
        return

    if apply_clicked:
        updates, errors = collect_updates(raw_inputs)
        for error in errors:
            st.error(error)
        if errors:
            return
        if not updates:
            st.warning("No changes to apply — enter at least one value.")
            return
        with st.spinner("Updating metadata..."):
            results = apply_metadata_to_files(files, updates)
        successes = sum(1 for result in results if result.success)
        failures = [result for result in results if not result.success]
        if successes:
            st.success(f"Updated metadata for {successes} of {len(files)} files.")
        if failures:
            st.error("Some files could not be updated. See details below.")
            failure_df = pd.DataFrame(
                {
                    "file": [result.path.name for result in failures],
                    "path": [str(result.path) for result in failures],
                    "error": [result.message for result in failures],
                }
            )
            st.dataframe(failure_df, use_container_width=True)


if __name__ == "__main__":
    main()
