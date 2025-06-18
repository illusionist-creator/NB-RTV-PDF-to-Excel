import streamlit as st
import re
from PyPDF2 import PdfReader
import pandas as pd
from io import BytesIO
import time

# Streamlit app configuration (must be the first Streamlit command)
st.set_page_config(page_title="PDF to Excel Converter", layout="wide")

# Custom CSS for better UI and dark theme consistency
st.markdown("""
    <style>
    .main { padding: 20px; background-color: #1a1a1a; }
    .stButton>button { width: 100%; background-color: #2a2a2a; color: #ffffff; border: 1px solid #444; }
    .stButton>button:hover { background-color: #3a3a3a; }
    .stFileUploader { border: 2px dashed #d3d3d3; padding: 20px; border-radius: 10px; background-color: #1a1a1a; }
    .stFileUploader label { color: #ffffff; }
    .stFileUploader div[role="listbox"] { background-color: #1a1a1a; }
    .stFileUploader div[role="listbox"] span { color: #ffffff; }
    .stProgress { margin: 20px 0; background-color: #2a2a2a; }
    .stProgress > div > div { background-color: #4dabf7; }
    .stProgress span { color: #ffffff !important; }
    .success-box { background-color: #e6ffed; padding: 10px; border-radius: 5px; color: #000000; }
    .error-box { background-color: #ffe6e6; padding: 10px; border-radius: 5px; color: #000000; }
    .summary-box { background-color: #2a2a2a; padding: 15px; border-radius: 5px; margin-bottom: 20px; color: #ffffff; }
    .stDataFrame { background-color: #1a1a1a; }
    .stDataFrame table { background-color: #1a1a1a; color: #ffffff; border: 1px solid #444; }
    .stDataFrame th { background-color: #2a2a2a; color: #ffffff; }
    .stDataFrame td { background-color: #1a1a1a; color: #ffffff; border: 1px solid #444; }
    .stTextArea textarea { background-color: #2a2a2a; color: #ffffff; border: 1px solid #444; }
    </style>
""", unsafe_allow_html=True)

st.title("📑 Goods Return Delivery Challan Converter")
st.markdown("Upload multiple PDF files to extract delivery challan data into a single Excel file.")

# Initialize session state for file management
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'error_log' not in st.session_state:
    st.session_state.error_log = []

# File uploader
with st.container():
    st.subheader("Upload PDF Files")
    uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True, key="pdf_uploader")
    
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        st.session_state.processed = False
    
    # Display number of uploaded files
    if st.session_state.uploaded_files:
        st.markdown(f"<div class='summary-box'>Uploaded {len(st.session_state.uploaded_files)} PDF file(s)</div>", unsafe_allow_html=True)

# Process button and reset button
col1, col2 = st.columns([1, 1])
with col1:
    process_button = st.button("Process PDFs", disabled=not st.session_state.uploaded_files)
with col2:
    reset_button = st.button("Clear Files")

# Reset functionality
if reset_button:
    st.session_state.uploaded_files = []
    st.session_state.processed = False
    st.session_state.error_log = []
    st.rerun()

# Batch processing logic
if process_button and st.session_state.uploaded_files:
    # Metadata extraction patterns
    meta_patterns = {
        "store": re.compile(r"(NB [^\n]+)"),
        "vendor_code": re.compile(r"Vendor Code\s*:([^\n]+)"),
        "vendor_name": re.compile(r"Vendor Name\s*:([^\n]+)"),
        "doc_no": re.compile(r"Doc No\s*:([^\n]+)"),
        "invoice_date": re.compile(r"Invoice Date\s*:([^\n]+)"),
        "order_no": re.compile(r"Order No\s*:([^\n]+)"),
        "order_date": re.compile(r"Order Date\s*:([^\n]+)"),
        "pslip_no": re.compile(r"P\.Slip No\.\s*:([^\n]+)")
    }
    
    # Line item pattern
    line_item_pattern = re.compile(
        r"(?P<sno>\d+)\s+(?P<article_code>\d+)\s+(?P<ean_code>\d+)\s+(?P<ref_po>\d+)\s+"
        r"(?P<qty>\d+\.\d+)\s+(?P<uom>\w+)\s+(?P<mrp>\d+\.\d+)\s+(?P<cost>\d+\.\d+)\s+"
        r"(?P<value>\d+\.\d+)\s+(?P<reason>\d+)\s+(?P<sgst>\d+\.\d+)\s+(?P<cgst>\d+\.\d+)\s+(?P<netval>\d+\.\d+)\s+"
        r"TBD (?P<desc>.+?)\s+(?P<hsn>\d{8})\s+Date expired", re.DOTALL
    )
    
    all_records = []
    st.session_state.error_log = []
    batch_size = 10  # Process 10 PDFs at a time
    total_files = len(st.session_state.uploaded_files)
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Process files in batches
    for i in range(0, total_files, batch_size):
        batch = st.session_state.uploaded_files[i:i + batch_size]
        for j, uploaded_file in enumerate(batch):
            file_index = i + j + 1
            status_text.text(f"Processing file {file_index}/{total_files}: {uploaded_file.name}")
            
            try:
                # Read the PDF file
                reader = PdfReader(uploaded_file)
                
                # Extract text from all pages
                all_text = ""
                for page in reader.pages:
                    all_text += page.extract_text() + "\n"
                
                # Split the text into individual delivery challans
                documents = all_text.split("GOODS RETURN DELIVERY CHALLAN")
                
                # Process each document
                for doc in documents[1:]:  # Skip the initial header
                    # Extract metadata
                    metadata = {}
                    for key, pattern in meta_patterns.items():
                        match = pattern.search(doc)
                        metadata[key] = match.group(1).strip() if match else None
                    
                    # Extract line items
                    for match in line_item_pattern.finditer(doc):
                        item_data = match.groupdict()
                        record = {**metadata, **item_data}
                        all_records.append(record)
            
            except Exception as e:
                st.session_state.error_log.append(f"Error processing {uploaded_file.name}: {str(e)}")
            
            # Update progress
            progress = min(file_index / total_files, 1.0)
            progress_bar.progress(progress)
    
    status_text.text("Processing complete!")
    
    # Display results
    if all_records:
        df = pd.DataFrame(all_records)
        
        # Summary
        st.markdown(f"<div class='summary-box'>"
                    f"Processed {total_files} PDF file(s)<br>"
                    f"Extracted {len(all_records)} record(s)"
                    f"</div>", unsafe_allow_html=True)
        
        # Display data preview
        with st.expander("View Extracted Data", expanded=True):
            st.dataframe(df, use_container_width=True)
        
        # Convert DataFrame to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        
        # Download button for Excel
        st.download_button(
            label="Download Excel File",
            data=excel_data,
            file_name="goods_return_delivery_challans.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel"
        )
        
        # Success message
        st.markdown(f"<div class='success-box'>Successfully processed {total_files} file(s) and extracted {len(all_records)} record(s)!</div>", unsafe_allow_html=True)
    
    else:
        st.markdown("<div class='error-box'>No valid data extracted from the uploaded PDFs. Check the error log below.</div>", unsafe_allow_html=True)
    
    # Display and download error log if any
    if st.session_state.error_log:
        st.subheader("Error Log")
        error_log_text = "\n".join(st.session_state.error_log)
        st.text_area("Errors encountered during processing:", error_log_text, height=150)
        st.download_button(
            label="Download Error Log",
            data=error_log_text,
            file_name="error_log.txt",
            mime="text/plain",
            key="download_error_log"
        )
    
    st.session_state.processed = True

elif st.session_state.uploaded_files and st.session_state.processed:
    st.markdown("<div class='success-box'>Files already processed. Clear files to upload new ones.</div>", unsafe_allow_html=True)
else:
    st.info("Please upload one or more PDF files to begin.")