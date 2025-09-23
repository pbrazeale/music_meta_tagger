"""Folder selection and session-state utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from metadata_logic import list_audio_files, reset_bulk_metadata_inputs

CACHE_KEY = "folder_cache"


def _reset_folder_cache(include_subfolders: bool) -> dict[str, Any]:
    cache = {
        "selected": "",
        "resolved": "",
        "include_subfolders": include_subfolders,
        "files": [],
    }
    st.session_state[CACHE_KEY] = cache
    return cache


def _get_folder_cache(include_subfolders: bool) -> dict[str, Any]:
    cache = st.session_state.get(CACHE_KEY)
    if not isinstance(cache, dict):
        return _reset_folder_cache(include_subfolders)
    # ensure expected keys exist
    cache.setdefault("selected", "")
    cache.setdefault("resolved", "")
    cache.setdefault("include_subfolders", include_subfolders)
    cache.setdefault("files", [])
    return cache


def normalize_folder_input(raw_value: str) -> str:
    """Normalize user input into a consistent folder path string."""
    value = raw_value.strip()
    if not value:
        return ""
    # Tkinter returns forward slashes even on Windows; convert UNC prefixes carefully
    if value.startswith(("\\\\", "//")):
        normalized = value.replace("/", "\\")
        if not normalized.startswith("\\\\"):
            normalized = "\\\\" + normalized.lstrip("\\")
        return normalized.rstrip("\\") or normalized
    return os.path.normpath(value)


def initialize_session_state() -> None:
    """Ensure the keys used by the folder workflow exist in session state."""
    if "folder_path" not in st.session_state:
        st.session_state["folder_path"] = ""
    if "folder_input" not in st.session_state:
        st.session_state["folder_input"] = st.session_state["folder_path"]
    if "include_subfolders" not in st.session_state:
        st.session_state["include_subfolders"] = True
    if "bulk_form_folder" not in st.session_state:
        st.session_state["bulk_form_folder"] = ""
    _get_folder_cache(st.session_state["include_subfolders"])


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
        normalized = normalize_folder_input(folder)
        st.session_state["folder_input"] = normalized
        st.session_state["folder_path"] = normalized
        # invalidate cache so contents are reloaded on next run
        _reset_folder_cache(st.session_state.get("include_subfolders", True))


def sync_folder_selection() -> tuple[str, Optional[Path]]:
    """Return the selected folder string and Path after syncing text input."""
    raw_input = st.session_state.get("folder_input", "")
    normalized_input = normalize_folder_input(raw_input)
    if normalized_input != st.session_state.get("folder_path", ""):
        st.session_state["folder_path"] = normalized_input
        _reset_folder_cache(st.session_state.get("include_subfolders", True))
    selected_folder = st.session_state["folder_path"]
    folder_path = Path(selected_folder) if selected_folder else None
    return selected_folder, folder_path


def load_folder_contents(folder: Optional[Path], include_subfolders: bool) -> tuple[List[Path], str]:
    """Load audio files for the folder and return their resolved path string."""
    cache = _get_folder_cache(include_subfolders)
    selected_folder = st.session_state.get("folder_path", "")

    if not selected_folder or folder is None:
        _reset_folder_cache(include_subfolders)
        return [], ""

    if (
        cache.get("selected") == selected_folder
        and cache.get("include_subfolders") == include_subfolders
        and isinstance(cache.get("files"), list)
    ):
        return list(cache["files"]), cache.get("resolved", selected_folder)

    path_str = selected_folder
    actual_folder = folder
    try:
        is_dir = actual_folder.is_dir()
    except OSError:
        is_dir = False

    if not is_dir and os.path.isdir(path_str):
        actual_folder = Path(os.path.normpath(path_str))
        is_dir = True

    if not is_dir:
        path_display = path_str.replace('\\', '\\\\')
        st.error(f"Folder not found or inaccessible: `{path_display}`")
        _reset_folder_cache(include_subfolders)
        return [], ""

    try:
        files = list_audio_files(actual_folder, include_subfolders)
    except Exception as exc:  # noqa: BLE001 - surface listing failure to UI
        st.error(f"Unable to read folder contents: {exc}")
        _reset_folder_cache(include_subfolders)
        return [], ""

    try:
        resolved_folder = str(actual_folder.resolve())
    except Exception:
        resolved_folder = path_str

    cache.update(
        {
            "selected": selected_folder,
            "resolved": resolved_folder,
            "include_subfolders": include_subfolders,
            "files": files,
        }
    )
    return list(files), resolved_folder


def handle_folder_change(resolved_folder: str) -> None:
    """Reset bulk form state when a different folder is loaded."""
    previous = st.session_state.get("bulk_form_folder", "")
    if resolved_folder:
        if resolved_folder != previous:
            reset_bulk_metadata_inputs()
            st.session_state["bulk_form_folder"] = resolved_folder
    elif previous:
        reset_bulk_metadata_inputs()
        st.session_state["bulk_form_folder"] = ""
