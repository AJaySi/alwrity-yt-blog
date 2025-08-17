## Alwrity: AI YouTube → Blog (Streamlit)

Transform any YouTube video into a clean, well‑structured markdown blog post.

### What it does
- Downloads audio from a YouTube URL
- Transcribes with AssemblyAI
- Rewrites and formats into a blog post with Google Gemini
- Displays the result in a polished Streamlit UI with copy/download options

### Requirements
- Python 3.9+
- API keys:
  - `ASSEMBLYAI_API_KEY` (for transcription)
  - `GEMINI_API_KEY` (for content generation)

### Install
```bash
git clone https://github.com/uniqueumesh/alwrity-yt-blog.git
cd alwrity-yt-blog
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -U pip
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

On macOS/Linux, replace the last two lines with:
```bash
source .venv/bin/activate
pip install -U pip -r requirements.txt
```

### Configure API keys
You can either:
- Create a `.env` file in the project root with:
  ```
  ASSEMBLYAI_API_KEY=your_assemblyai_key
  GEMINI_API_KEY=your_gemini_key
  ```
- Or paste keys directly in the app sidebar when running.

### Run
```bash
./.venv/Scripts/python.exe -m streamlit run alwrity_yt_blog.py
```

macOS/Linux:
```bash
streamlit run alwrity_yt_blog.py
```

### Usage
1. Open the app (Streamlit will print a local URL, e.g., `http://localhost:8501`).
2. In the sidebar, paste your `ASSEMBLYAI_API_KEY` and `GEMINI_API_KEY` (or use `.env`).
3. Paste a YouTube video URL.
4. Click “Generate Blog Post”.
5. Copy or download the generated blog as `.txt` or `.md`.

### Notes
- Supports most YouTube URL formats; validates and cleans the URL internally.
- Shows progress while transcribing; large/long videos may take time.
- Very long transcripts are truncated to keep generation reliable.

### Tech stack
- Streamlit UI
- pytubefix for YouTube audio
- AssemblyAI for transcription
- Google Gemini (`google-generativeai`) for blog generation

### Troubleshooting
- `ModuleNotFoundError: No module named 'dotenv'` → run `pip install -r requirements.txt` (we depend on `python-dotenv`).
- `pytube` errors → we use `pytubefix` which includes the latest cipher fixes; ensure it’s installed from `requirements.txt`.
- API errors → verify keys and quotas; check the app sidebar status indicators.

### License
MIT


