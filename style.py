"""Styling utilities for the Music Metadata Tagger Streamlit app."""

from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

LOGO_PATH = Path(__file__).resolve().parent / "music_meta_tagger_logo_300.jpg"

THEME_CSS = """
<style>
:root {
    --brand-navy-900: #050c1a;
    --brand-navy-800: #0b1f3d;
    --brand-blue-500: #1f6dff;
    --brand-blue-400: #3aa0ff;
    --brand-cyan-400: #25d5ff;
    --brand-orange-500: #ff8c32;
    --brand-orange-400: #ffab47;
    --text-primary: #f5f7ff;
    --text-muted: #9aa9c7;
}

.stApp, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 12% 12%, rgba(31, 109, 255, 0.16), transparent 55%), radial-gradient(circle at 85% 10%, rgba(255, 140, 50, 0.14), transparent 50%), var(--brand-navy-800);
    color: var(--text-primary);
}

.stApp h1 {
    font-weight: 800;
    letter-spacing: 0.01em;
    color: var(--text-primary);
    background: linear-gradient(135deg, var(--brand-cyan-400), var(--brand-orange-500));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: var(--text-primary);
    letter-spacing: 0.01em;
}

[data-testid="stCaption"] {
    color: var(--text-muted) !important;
}

a {
    color: var(--brand-cyan-400);
    text-decoration: none;
}

a:hover {
    color: var(--brand-orange-500);
}

div[data-testid="stSidebar"] {
    background: linear-gradient(185deg, rgba(5, 12, 26, 0.98) 0%, rgba(11, 31, 61, 0.98) 100%);
    border-right: 1px solid rgba(58, 160, 255, 0.3);
}

div[data-testid="stSidebar"] .stMarkdown p,
div[data-testid="stSidebar"] .stMarkdown li,
div[data-testid="stSidebar"] label {
    color: var(--text-primary);
}

div[data-testid="stSidebar"] img {
    border-radius: 1rem;
    box-shadow: 0 18px 32px rgba(3, 10, 24, 0.45);
    border: 1px solid rgba(58, 160, 255, 0.35);
}

.stButton>button {
    background: linear-gradient(135deg, var(--brand-blue-500), var(--brand-cyan-400));
    color: var(--text-primary);
    border: none;
    border-radius: 0.6rem;
    font-weight: 600;
    padding: 0.55rem 1.1rem;
    box-shadow: 0 12px 24px rgba(10, 30, 70, 0.35);
}

.stButton>button:hover {
    background: linear-gradient(135deg, var(--brand-orange-500), var(--brand-blue-500));
    box-shadow: 0 16px 28px rgba(255, 140, 50, 0.4);
}

.stButton>button:focus:not(:active) {
    outline: 2px solid rgba(37, 213, 255, 0.6);
    outline-offset: 2px;
}

form[data-testid="stForm"] {
    background: rgba(5, 16, 34, 0.85);
    border: 1px solid rgba(31, 109, 255, 0.35);
    border-radius: 1rem;
    padding: 1.6rem;
    box-shadow: 0 28px 60px rgba(4, 12, 28, 0.52);
}

form[data-testid="stForm"] .stButton>button {
    background: linear-gradient(135deg, var(--brand-orange-500), var(--brand-blue-500));
}

div[data-testid="stAlert"] {
    border-radius: 0.75rem;
    border: 1px solid rgba(31, 109, 255, 0.35);
    box-shadow: 0 18px 36px rgba(4, 12, 28, 0.42);
    color: var(--text-primary);
}

div[data-testid="stAlert"] p {
    color: var(--text-primary);
}

div[data-testid="stAlert"].stAlert--info {
    background: linear-gradient(135deg, rgba(31, 109, 255, 0.22), rgba(37, 213, 255, 0.18));
}

div[data-testid="stAlert"].stAlert--warning {
    background: linear-gradient(135deg, rgba(255, 140, 50, 0.28), rgba(255, 171, 71, 0.22));
    border-color: rgba(255, 171, 71, 0.5);
}

div[data-testid="stAlert"].stAlert--error {
    background: linear-gradient(135deg, rgba(255, 82, 82, 0.32), rgba(255, 140, 50, 0.24));
    border-color: rgba(255, 82, 82, 0.55);
}

div[data-testid="stAlert"].stAlert--success {
    background: linear-gradient(135deg, rgba(48, 209, 88, 0.28), rgba(31, 109, 255, 0.18));
    border-color: rgba(48, 209, 88, 0.5);
}

.stTextInput>div>div>input,
.stTextArea textarea,
div[data-baseweb="input"] > div > input {
    background: rgba(8, 22, 52, 0.8);
    color: var(--text-primary);
    border: 1px solid rgba(31, 109, 255, 0.4);
    border-radius: 0.6rem;
}

.stTextInput>div>div>input::placeholder,
.stTextArea textarea::placeholder {
    color: var(--text-muted);
    opacity: 1;
}

div[data-baseweb="select"] > div {
    background: rgba(8, 22, 52, 0.85);
    border: 1px solid rgba(31, 109, 255, 0.4);
    border-radius: 0.6rem;
    color: var(--text-primary);
}

div[data-baseweb="select"] span {
    color: var(--text-primary);
}

div[data-testid="stDataFrame"] {
    background: rgba(5, 16, 34, 0.85);
    border: 1px solid rgba(31, 109, 255, 0.25);
    border-radius: 1rem;
    padding: 0.5rem;
    box-shadow: 0 20px 45px rgba(3, 10, 24, 0.45);
}

div[data-testid="stDataFrame"] thead {
    background: linear-gradient(135deg, rgba(31, 109, 255, 0.4), rgba(37, 213, 255, 0.3));
    color: var(--text-primary);
}

div[data-testid="stDataFrame"] tbody tr:nth-child(even) {
    background: rgba(8, 25, 52, 0.45);
}

div[data-testid="stDataFrame"] tbody td,
div[data-testid="stDataFrame"] thead th {
    color: var(--text-primary);
}

div[data-testid="stCheckbox"] input[type="checkbox"] {
    accent-color: var(--brand-orange-500);
}
</style>
"""


def apply_theme() -> Optional[str]:
    """Set the Streamlit page configuration and apply the brand theme.

    Returns
    -------
    Optional[str]
        Absolute path to the logo image if it exists, otherwise ``None``.
    """
    logo_src = str(LOGO_PATH) if LOGO_PATH.exists() else None
    page_config: Dict[str, Any] = {
        "page_title": "Music Metadata Tagger",
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }
    if logo_src:
        page_config["page_icon"] = logo_src
    st.set_page_config(**page_config)
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    return logo_src
