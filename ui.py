"""UI helpers for the Music Metadata Tagger app."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from metadata_logic import (
    FIELD_DEFS,
    RATING_CHOICES,
    RATING_LABEL_TO_VALUE,
    UpdateResult,
    build_metadata_table,
)


def render_sidebar(
    logo_src: Optional[str],
    supported_extensions: str,
    browse_callback: Callable[[], None],
) -> None:
    """Render the persistent sidebar controls."""
    with st.sidebar:
        if logo_src:
            st.image(logo_src, use_container_width=True)
        st.header("Setup")
        st.caption(f"Supported extensions: {supported_extensions}")
        st.button(
            "Select audio folder",
            on_click=browse_callback,
            use_container_width=True,
        )
        st.text_input(
            "Audio folder",
            key="folder_input",
            placeholder="Choose or enter a folder path",
        )
        st.checkbox("Include subfolders", key="include_subfolders")


def show_empty_state() -> None:
    """Display the empty-state guidance when no folder is selected."""
    st.info(
        "Use the Setup sidebar to choose an audio folder (the 'Select audio folder' button opens File Explorer)."
    )


def render_folder_overview(folder: Optional[Path], files: List[Path]) -> None:
    """Summarize the folder contents in the main view."""
    st.subheader("Folder overview")
    if files:
        folder_label = str(folder) if folder else st.session_state.get("folder_path", "")
        folder_display = folder_label.replace('\\', '\\\\')
        st.write(f"Found **{len(files)}** audio files in `{folder_display}`.")
        if len(files) > 200:
            st.write("Preview limited to first 200 entries.")
        table = build_metadata_table(files)
        st.dataframe(table, use_container_width=True)
    else:
        st.warning("No supported audio files were found in the selected folder.")


def render_bulk_metadata_form(files: List[Path]) -> Tuple[bool, Dict[str, Any]]:
    """Render the bulk metadata form and return the submission state and inputs."""
    raw_inputs: Dict[str, Any] = {}
    with st.form("bulk_metadata"):
        st.subheader("Bulk metadata update")
        st.caption("Provide only the fields you want to change; leave others blank to skip them.")
        cols = st.columns(2)
        for index, field_config in enumerate(FIELD_DEFS):
            target_col = cols[index % len(cols)]
            with target_col:
                raw_inputs[field_config["name"]] = render_field(field_config, disabled=not files)
        apply_clicked = st.form_submit_button("Apply metadata to files", disabled=not files)
    return apply_clicked, raw_inputs


def render_update_results(results: List[UpdateResult], total_files: int) -> None:
    """Display success and error feedback after metadata writes."""
    successes = sum(1 for result in results if result.success)
    failures = [result for result in results if not result.success]
    if successes:
        st.success(f"Updated metadata for {successes} of {total_files} files.")
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


def render_field(field_config: Dict[str, Any], disabled: bool = False) -> Any:
    """Render a single input field based on the field configuration."""
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
