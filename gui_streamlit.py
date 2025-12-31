import streamlit as st
import tempfile
import io
import csv
import pandas as pd
import os

from algov1 import process_csv


st.set_page_config(page_title="Shelter Ranker", layout="wide")

st.title("Shelter CSV Ranker")
st.markdown("Drag & drop a CSV below (or click) to upload, then the app will process and return a ranked CSV.")

uploaded = st.file_uploader("Upload CSV file", type=["csv"], accept_multiple_files=False)

if uploaded is not None:
    # Save uploaded file to a temporary path because process_csv expects a file path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name

    try:
        shelters = process_csv(tmp_path)

        # Build a DataFrame for display
        display_fields = ['rank', 'name', 'niche', 'score', 'finance', 'supply', 'population', 'urgency', 'capacity']
        rows = [{k: s.get(k) for k in display_fields} for s in shelters]
        df = pd.DataFrame(rows)

        st.subheader('Ranked results')
        st.dataframe(df)

        # Build CSV for download
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=display_fields)
        writer.writeheader()
        for s in shelters:
            writer.writerow({k: s.get(k) for k in display_fields})

        st.download_button('Download ranked CSV', csv_buffer.getvalue(), file_name='ranked_shelters.csv', mime='text/csv')

    except Exception as e:
        st.error(f"Processing failed: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
