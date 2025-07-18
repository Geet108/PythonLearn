import streamlit as st
import pandas as pd
from io import StringIO
import tabula
import tempfile

def read_table(file, filetype, closing_col="Closing", date_col="Date"):
    # Try to read table from CSV or PDF
    if filetype == "csv":
        df = pd.read_csv(file)
    elif filetype == "pdf":
        # Save file to a temp location
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tfile.write(file.read())
        tfile.close()
        # Attempt extraction (may need adjustment for your PDFs)
        dfs = tabula.read_pdf(tfile.name, pages="all", multiple_tables=True)
        df = pd.DataFrame()
        for table in dfs:
            if closing_col in table.columns and date_col in table.columns:
                df = pd.concat([df, table[[date_col, closing_col]]])
        if df.empty:
            st.warning(f"No '{closing_col}' or '{date_col}' columns found. Check your PDF or extraction logic.")
            return None
    else:
        st.error("Unsupported file type")
        return None
    # Parse dates
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[date_col, closing_col])
    df = df.sort_values(date_col)
    return df

st.title("Bank & ERP Closing Balance Reconciliation")

bank = st.file_uploader("Upload Bank Statement (PDF or CSV)", type=["pdf", "csv"])
erp = st.file_uploader("Upload ERP Statement (PDF or CSV)", type=["pdf", "csv"])

if st.button("Reconcile") and bank and erp:
    bank_ext = bank.name.split(".")[-1].lower()
    erp_ext = erp.name.split(".")[-1].lower()
    bank_df = read_table(bank, bank_ext)
    erp_df = read_table(erp, erp_ext)
    if bank_df is not None and erp_df is not None:
        # Merge on Date
        merged = pd.merge(bank_df, erp_df, left_on="Date", right_on="Date", suffixes=('_Bank', '_ERP'))
        merged["Difference"] = pd.to_numeric(merged["Closing_ERP"], errors="coerce") - pd.to_numeric(merged["Closing_Bank"], errors="coerce")
        diffs = merged[merged["Difference"].abs() > 1]  # Tolerance of 1
        if diffs.empty:
            st.success("All closing balances match!")
        else:
            st.error("Mismatch found on the following dates:")
            st.dataframe(diffs[["Date", "Closing_Bank", "Closing_ERP", "Difference"]])
    else:
        st.error("Failed to extract tables. Please check file contents/columns.")

st.markdown("""
- **Note:** Adjust `closing_col` and `date_col` in the code if your actual column/header names are different.
- For unstructured PDFs, you may need to first export as CSV (using Excel, or an online converter).
""")
