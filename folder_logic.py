"""Folder selection and session-state utilities."""

from pathlib import Path
from typing import List, Optional, Tuple

import streamlit as st

from metadata_logic import list_audio_files, reset_bulk_metadata_inputs


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


def sync_folder_selection() -> Tuple[str, Optional[Path]]:
    """Return the selected folder string and Path after syncing text input."""
    current_input = st.session_state.get("folder_input", "").strip()
    if current_input != st.session_state.get("folder_path", ""):
        st.session_state["folder_path"] = current_input
    selected_folder = st.session_state["folder_path"].strip()
    folder_path = Path(selected_folder) if selected_folder else None
    return selected_folder, folder_path


def load_folder_contents(folder: Optional[Path], include_subfolders: bool) -> Tuple[List[Path], str]:
    """Load audio files for the folder and return their resolved path string."""
    files: List[Path] = []
    resolved_folder = ""
    if folder:
        if folder.is_dir():
            files = list_audio_files(folder, include_subfolders)
            try:
                resolved_folder = str(folder.resolve())
            except Exception:
                resolved_folder = str(folder)
        else:
            st.error(f"Folder not found: {folder}")
    return files, resolved_folder


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
