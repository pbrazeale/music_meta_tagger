"""Streamlit-based bulk metadata editor for audio files.

Run with:
    streamlit run app.py
"""

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import streamlit as st

from folder_logic import (
    browse_for_audio_folder,
    handle_folder_change,
    initialize_session_state,
    load_folder_contents,
    sync_folder_selection,
)
from metadata_logic import (
    collect_updates,
    apply_metadata_to_files,
    SUPPORTED_EXTENSIONS,
)
from style import apply_theme
from ui import (
    render_bulk_metadata_form,
    render_folder_overview,
    render_sidebar,
    render_update_results,
    show_empty_state,
)


def main() -> None:
    logo_src = apply_theme()
    st.title("Music Metadata Tagger")
    st.caption(
        "Bulk-apply Windows-friendly metadata (Title, Rating, Artists, etc.) to every audio file in a folder."
    )

    initialize_session_state()
    render_sidebar(logo_src, SUPPORTED_EXTENSIONS, browse_for_audio_folder)

    selected_folder, folder_path = sync_folder_selection()
    include_subfolders = st.session_state["include_subfolders"]

    files, resolved_folder = load_folder_contents(folder_path, include_subfolders)
    handle_folder_change(resolved_folder)

    if not selected_folder:
        show_empty_state()
        return

    render_folder_overview(folder_path, files)

    apply_clicked, raw_inputs = render_bulk_metadata_form(files)

    if not files:
        return

    if apply_clicked:
        updates, errors = collect_updates(raw_inputs)
        for error in errors:
            st.error(error)
        if errors:
            return
        if not updates:
            st.warning("No changes to apply - enter at least one value.")
            return
        with st.spinner("Updating metadata..."):
            results = apply_metadata_to_files(files, updates)
        render_update_results(results, len(files))


if __name__ == "__main__":
    main()
