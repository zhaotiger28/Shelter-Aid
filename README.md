# Shelter Ranker GUI

A simple Streamlit GUI to upload a CSV, run the ranking in `algov1.py` and download the ranked CSV.

Quick start

1. Create and activate a Python environment (recommended).

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run gui_streamlit.py
```

4. In the browser UI, drag-and-drop or choose your CSV file. After processing you can preview the ranked results and download `ranked_shelters.csv`.

Notes
- The GUI uses `process_csv` from `algov1.py`, so existing processing logic is reused.
- If your CSV uses different column names, adjust `algov1.py` or pre-process the file accordingly.

Desktop (Tkinter) option

1. Install optional drag-and-drop dependency (optional):

```bash
pip install tkinterdnd2
```

2. Run the desktop app:

```bash
python gui_tkinter.py
```

The desktop app opens a local popup where you can open a CSV (and drop it if `tkinterdnd2` is installed). After processing you can save the ranked CSV from the UI.
