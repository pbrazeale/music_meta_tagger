# Music Metadata Tagger

![Music Metadata Tagger logo](https://pbrazeale.github.io/images/music_meta_tagger_logo_300.jpg)

Music Metadata Tagger is a Streamlit application for bulk-editing the metadata of audio files on Windows-friendly formats. It streamlines updating key tags—such as title, artist, album, year, rating, and comments—across large music libraries, including network shares.

## Key Features

- **Bulk updates**: Apply the same metadata values to every supported file in a selected directory (with optional recursion into subfolders).
- **Windows-friendly tags**: Writes metadata using Mutagen to match Windows Explorer fields, including 0–5 star ratings.
- **Wide audio support**: Handles MP3, MP4/M4A/M4V, FLAC, WMA/ASF, and more.
- **Network-ready**: Works with local paths, mapped drives, and UNC network shares.
- **Modern UI**: Dark blue/orange theme inspired by the project logo, with responsive tables and form layout.

## Quick Start

### Prerequisites

- Python 3.9+
- `pip` for installing dependencies

### Installation

```bash
python -m venv .venv
. .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you do not have a `requirements.txt`, the core packages are:

```bash
pip install streamlit mutagen pandas
```

### Run the App

```bash
streamlit run app.py
```

Once Streamlit starts, a browser tab will open automatically. If it does not, visit [http://localhost:8501](http://localhost:8501).

## Using the Application

1. **Select a folder**
   - Click **Select audio folder** to browse with File Explorer, or type/paste a path into the sidebar input.
   - UNC paths are supported (e.g., `\\NAS\share\Music`).
   - Toggle **Include subfolders** if you want files from nested directories.
2. **Review the overview**
   - The main panel shows a count of supported files and a preview table (first 200 rows).
3. **Enter metadata values**
   - In the **Bulk metadata update** form, fill in the fields you want to change. Leave others blank to skip.
   - Rating field offers Windows-style 0–5 star selections.
4. **Apply changes**
   - Click **Apply metadata to files**. A progress indicator runs, and success/error summaries appear when finished.

## File Support

Supported extensions are defined dynamically from Mutagen handlers and currently include:

- `.mp3`, `.flac`, `.m4a`, `.m4b`, `.m4p`, `.m4r`, `.m4v`, `.mp4`, `.asf`, `.wma`

The app reads existing metadata to populate the preview table, but fields are only written when values are supplied in the bulk form.

## Project Structure

```
app.py
# Streamlit entry point; wires modules together

style.py
# Theme CSS and page configuration helpers

ui.py
# Streamlit component renderers

folder_logic.py
# Folder selection and caching for local/UNC paths

metadata_logic.py
# Tag handlers, validation, and bulk update routines

music_meta_tagger_logo_300.jpg
# Branding asset displayed in the sidebar
```

## Troubleshooting

- **“Folder not found or inaccessible”**: Ensure the account running Streamlit can access the path. For UNC paths, confirm the formatting (`\\server\share`).
- **No files found**: Verify the directory actually contains supported audio file types and that subfolders are included if needed.
- **Permission errors when writing metadata**: Some files may be read-only or in use by other processes. Adjust file attributes or close conflicting applications.

## Development Tips

- The UI uses Streamlit’s session state to persist selections. When changing folder input, cached results reset automatically.
- `metadata_logic.py` centralizes Mutagen handlers and field validation; add new file formats or tag rules there.
- Theme adjustments live in `style.py`. The main gradient and accent colors match the project logo.

## License

See [LICENSE.txt](LICENSE.txt) for the MIT-style license.

## Credits

- Built with [Streamlit](https://streamlit.io/) and [Mutagen](https://mutagen.readthedocs.io/).
