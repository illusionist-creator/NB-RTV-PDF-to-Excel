import streamlit as st
import re
from PyPDF2 import PdfReader
import pandas as pd
from io import BytesIO
import time
from typing import Dict, Any, List

# Streamlit app configuration (must be the first Streamlit command)
st.set_page_config(page_title="Nature's Basket PDF Parser", layout="wide", page_icon="📑")

# Custom CSS for better UI and dark theme consistency
st.markdown("""
    <style>
    .main { padding: 20px; background-color: #0e1117; }
    .stButton>button { 
        width: 100%; 
        background-color: #262730; 
        color: #ffffff; 
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .stButton>button:hover { 
        background-color: #3a3a4a; 
        border-color: #5a5a5a;
    }
    .stFileUploader { 
        border: 2px dashed #4a4a4a; 
        padding: 20px; 
        border-radius: 10px; 
        background-color: #1e1e2e; 
        transition: all 0.3s ease;
    }
    .stFileUploader:hover { 
        border-color: #6a6a6a; 
        background-color: #252535;
    }
    .stFileUploader label { color: #ffffff; font-weight: 500; }
    .stProgress { margin: 20px 0; background-color: #262730; border-radius: 10px; }
    .stProgress > div > div { background-color: #4dabf7; border-radius: 8px; }
    .success-box { 
        background: linear-gradient(135deg, #e6ffed, #ccf7d0); 
        padding: 15px; 
        border-radius: 10px; 
        color: #0d4f1c; 
        border-left: 4px solid #28a745;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .error-box { 
        background: linear-gradient(135deg, #fff5f5, #fed7d7); 
        padding: 15px; 
        border-radius: 10px; 
        color: #742a2a; 
        border-left: 4px solid #e53e3e;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .info-box { 
        background: linear-gradient(135deg, #e6f3ff, #bee3f8); 
        padding: 15px; 
        border-radius: 10px; 
        color: #2a4a6b; 
        border-left: 4px solid #3182ce;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .summary-box { 
        background-color: #262730; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 20px; 
        color: #ffffff; 
        border: 1px solid #4a4a4a;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #1e1e2e;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #4a4a4a;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4dabf7;
        margin-bottom: 5px;
    }
    .metric-label {
        color: #a0a0a0;
        font-size: 0.9rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #262730;
        border-radius: 8px 8px 0 0;
        border: 1px solid #4a4a4a;
        padding: 10px 20px;
        color: #ffffff;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4dabf7;
        color: #ffffff;
        border-color: #4dabf7;
    }
    </style>
""", unsafe_allow_html=True)

# GRN Parser Functions
def extract_text_from_pdf_bytes(pdf_bytes) -> str:
    """Extract text content from PDF bytes"""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return ""

def parse_grn_text(text: str) -> Dict[str, Any]:
    """Parse GRN text content and extract metadata and product details"""
    
    # Initialize result dictionary
    result = {
        'metadata': {},
        'products': []
    }
    
    # Extract store name/location - look for "NB " followed by location
    store_patterns = [
        r'NB ([^\n]+?)(?=\n|Nature\'s Basket)',
        r'NB ([^\n]+)',
        r'(NB [^\n]+)'
    ]
    
    for pattern in store_patterns:
        store_match = re.search(pattern, text, re.IGNORECASE)
        if store_match:
            result['metadata']['store_name'] = store_match.group(1).strip()
            break
    
    # Extract vendor code
    vendor_code_match = re.search(r'Vendor Code\s*:([^\n]+)', text)
    if vendor_code_match:
        result['metadata']['vendor_code'] = vendor_code_match.group(1).strip()
    
    # Extract vendor name
    vendor_name_match = re.search(r'Vendor Name\s*:([^\n]+)', text)
    if vendor_name_match:
        result['metadata']['vendor_name'] = vendor_name_match.group(1).strip()
    
    # Extract vendor address
    address_match = re.search(r'Address\s*:([^\n]+(?:\n[^\n]+)*?)(?=Status|Inv\.No)', text, re.DOTALL)
    if address_match:
        address_lines = [line.strip() for line in address_match.group(1).split('\n') if line.strip() and not line.strip().startswith(':')]
        result['metadata']['vendor_address'] = ' '.join(address_lines)
    
    # Extract invoice number
    inv_no_match = re.search(r'Inv\.No\s*:([^\n\s]+)', text)
    if inv_no_match:
        result['metadata']['invoice_no'] = inv_no_match.group(1).strip()
    
    # Extract invoice date
    inv_date_match = re.search(r'Inv\.Date\s*:([^\n\s]+)', text)
    if inv_date_match:
        result['metadata']['invoice_date'] = inv_date_match.group(1).strip()
    
    # Extract invoice value
    inv_value_match = re.search(r'Inv\.Value\s*:([^\n\s]+)', text)
    if inv_value_match:
        result['metadata']['invoice_value'] = inv_value_match.group(1).strip()
    
    # Extract invoice tax value
    inv_tax_val_match = re.search(r'Inv\.Tax Val\s*:([^\n\s]+)', text)
    if inv_tax_val_match:
        result['metadata']['invoice_tax_value'] = inv_tax_val_match.group(1).strip()
    
    # Extract GIN number
    gin_no_match = re.search(r'GIN No\s*:([^\n\s]+)', text)
    if gin_no_match:
        result['metadata']['gin_no'] = gin_no_match.group(1).strip()
    
    # Extract GIN date
    gin_date_match = re.search(r'GIN Date\s*:([^\n\s]+)', text)
    if gin_date_match:
        result['metadata']['gin_date'] = gin_date_match.group(1).strip()
    
    # Extract GRN number
    grn_no_match = re.search(r'GRN No\s*:([^\n\s]+)', text)
    if grn_no_match:
        result['metadata']['grn_no'] = grn_no_match.group(1).strip()
    
    # Extract GRN date
    grn_date_match = re.search(r'GRN Date\s*:([^\n\s]+)', text)
    if grn_date_match:
        result['metadata']['grn_date'] = grn_date_match.group(1).strip()
    
    # Extract PO number
    po_no_match = re.search(r'PO\.No\s*:([^\n\s]+)', text)
    if po_no_match:
        result['metadata']['po_no'] = po_no_match.group(1).strip()
    
    # Extract PO date
    po_date_match = re.search(r'PO\.Date\s*:([^\n\s]+)', text)
    if po_date_match:
        result['metadata']['po_date'] = po_date_match.group(1).strip()
    
    # Extract P.SLIP.No
    p_slip_match = re.search(r'P\.SLIP\.No\s*:([^\n\s]+)', text)
    if p_slip_match:
        result['metadata']['p_slip_no'] = p_slip_match.group(1).strip()
    
    # Extract Vendor GST IN
    vendor_gst_match = re.search(r'Vendor GST IN\s*:([^\n\s]+)', text)
    if vendor_gst_match:
        result['metadata']['vendor_gst_in'] = vendor_gst_match.group(1).strip()
    
    # Extract company GST number
    company_gst_match = re.search(r'GST NO\s*:([^\n\s]+)', text)
    if company_gst_match:
        result['metadata']['company_gst_no'] = company_gst_match.group(1).strip()
    
    # Extract totals from the TOTAL line
    total_match = re.search(r'TOTAL\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', text)
    if total_match:
        result['metadata']['total_gst_value'] = total_match.group(1).strip()
        result['metadata']['total_received_qty'] = total_match.group(2).strip()
        result['metadata']['total_accepted_qty'] = total_match.group(3).strip()
        result['metadata']['total_rejected_qty'] = total_match.group(4).strip()
        result['metadata']['total_cost_value'] = total_match.group(5).strip()
    
    # Extract gross value
    gross_value_match = re.search(r'Gross Value\s+([\d.]+)', text)
    if gross_value_match:
        result['metadata']['gross_value'] = gross_value_match.group(1).strip()
    
    # Extract product details
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if line starts with a number followed by a 7-digit article code
        if re.match(r'^\d+\s+\d{7}', line):
            try:
                # Split the line into parts
                parts = line.split()
                
                # Make sure we have enough parts for a valid product line
                if len(parts) >= 9:
                    # Initialize product dictionary
                    product = {
                        'serial_no': parts[0],
                        'article_code': parts[1],
                        'ean_code': parts[2],
                        'gst_value': parts[3],
                        'received_qty': parts[4],
                        'accepted_qty': parts[5],
                        'rejected_qty': parts[6],
                        'uom': parts[7],
                        'mrp': parts[8],
                        'total_cost_value': parts[9] if len(parts) > 9 else "",
                        'description': "",
                        'hsn_code': ""
                    }
                    
                    # Look for the description line (starts with "TBD")
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.startswith("TBD"):
                            # Parse the description line
                            desc_parts = next_line.split()
                            if len(desc_parts) >= 2:
                                # The last part is usually the HSN code (if it's all digits)
                                if desc_parts[-1].isdigit() and len(desc_parts[-1]) >= 6:
                                    product['hsn_code'] = desc_parts[-1]
                                    # Everything between TBD and HSN code is the description
                                    product['description'] = ' '.join(desc_parts[1:-1])
                                else:
                                    # No HSN code found, everything after TBD is description
                                    product['description'] = ' '.join(desc_parts[1:])
                    
                    result['products'].append(product)
                    
            except (IndexError, ValueError) as e:
                continue
        
        i += 1
    
    return result

# PRN Parser Functions
def parse_prn_documents(text: str) -> List[Dict[str, Any]]:
    """Parse PRN documents from text"""
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
    
    # Split the text into individual delivery challans
    documents = text.split("GOODS RETURN DELIVERY CHALLAN")
    
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
    
    return all_records

# Initialize session state
def init_session_state():
    if 'grn_files' not in st.session_state:
        st.session_state.grn_files = []
    if 'prn_files' not in st.session_state:
        st.session_state.prn_files = []
    if 'grn_processed' not in st.session_state:
        st.session_state.grn_processed = False
    if 'prn_processed' not in st.session_state:
        st.session_state.prn_processed = False
    if 'grn_data' not in st.session_state:
        st.session_state.grn_data = None
    if 'prn_data' not in st.session_state:
        st.session_state.prn_data = None
    if 'grn_errors' not in st.session_state:
        st.session_state.grn_errors = []
    if 'prn_errors' not in st.session_state:
        st.session_state.prn_errors = []

def process_grn_files(files):
    """Process GRN files and return DataFrame"""
    all_data = []
    errors = []
    
    for uploaded_file in files:
        try:
            # Extract text from PDF
            text = extract_text_from_pdf_bytes(uploaded_file.read())
            
            if not text:
                errors.append(f"Could not extract text from {uploaded_file.name}")
                continue
            
            # Parse the text
            parsed_data = parse_grn_text(text)
            
            # Convert to rows for DataFrame
            for product in parsed_data['products']:
                row = {
                    'filename': uploaded_file.name,
                    'store_name': parsed_data['metadata'].get('store_name', ''),
                    'vendor_code': parsed_data['metadata'].get('vendor_code', ''),
                    'vendor_name': parsed_data['metadata'].get('vendor_name', ''),
                    'vendor_address': parsed_data['metadata'].get('vendor_address', ''),
                    'vendor_gst_in': parsed_data['metadata'].get('vendor_gst_in', ''),
                    'company_gst_no': parsed_data['metadata'].get('company_gst_no', ''),
                    'invoice_no': parsed_data['metadata'].get('invoice_no', ''),
                    'invoice_date': parsed_data['metadata'].get('invoice_date', ''),
                    'invoice_value': parsed_data['metadata'].get('invoice_value', ''),
                    'invoice_tax_value': parsed_data['metadata'].get('invoice_tax_value', ''),
                    'gin_no': parsed_data['metadata'].get('gin_no', ''),
                    'gin_date': parsed_data['metadata'].get('gin_date', ''),
                    'grn_no': parsed_data['metadata'].get('grn_no', ''),
                    'grn_date': parsed_data['metadata'].get('grn_date', ''),
                    'po_no': parsed_data['metadata'].get('po_no', ''),
                    'po_date': parsed_data['metadata'].get('po_date', ''),
                    'p_slip_no': parsed_data['metadata'].get('p_slip_no', ''),
                    'total_gst_value': parsed_data['metadata'].get('total_gst_value', ''),
                    'total_received_qty': parsed_data['metadata'].get('total_received_qty', ''),
                    'total_accepted_qty': parsed_data['metadata'].get('total_accepted_qty', ''),
                    'total_rejected_qty': parsed_data['metadata'].get('total_rejected_qty', ''),
                    'total_cost_value': parsed_data['metadata'].get('total_cost_value', ''),
                    'gross_value': parsed_data['metadata'].get('gross_value', ''),
                    'serial_no': product.get('serial_no', ''),
                    'article_code': product.get('article_code', ''),
                    'ean_code': product.get('ean_code', ''),
                    'description': product.get('description', ''),
                    'hsn_code': product.get('hsn_code', ''),
                    'gst_value': product.get('gst_value', ''),
                    'received_qty': product.get('received_qty', ''),
                    'accepted_qty': product.get('accepted_qty', ''),
                    'rejected_qty': product.get('rejected_qty', ''),
                    'uom': product.get('uom', ''),
                    'mrp': product.get('mrp', ''),
                    'product_total_cost_value': product.get('total_cost_value', '')
                }
                all_data.append(row)
                
        except Exception as e:
            errors.append(f"Error processing {uploaded_file.name}: {str(e)}")
    
    return pd.DataFrame(all_data) if all_data else None, errors

def process_prn_files(files):
    """Process PRN files and return DataFrame"""
    all_records = []
    errors = []
    
    for uploaded_file in files:
        try:
            # Read the PDF file
            text = extract_text_from_pdf_bytes(uploaded_file.read())
            
            if not text:
                errors.append(f"Could not extract text from {uploaded_file.name}")
                continue
            
            # Parse PRN documents
            records = parse_prn_documents(text)
            
            # Add filename to each record
            for record in records:
                record['filename'] = uploaded_file.name
                all_records.append(record)
            
        except Exception as e:
            errors.append(f"Error processing {uploaded_file.name}: {str(e)}")
    
    return pd.DataFrame(all_records) if all_records else None, errors

# Main App
def main():
    init_session_state()
    
    # Header
    st.title("🏪 Nature's Basket Document Parser")
    st.markdown("Transform your PDF documents into organized Excel spreadsheets with ease!")
    
    # Create tabs
    tab1, tab2 = st.tabs(["📦 GRN Parser", "🔄 PRN Parser"])
    
    # GRN Tab
    with tab1:
        st.header("Goods Receipt Note (GRN) Parser")
        st.markdown("Upload GRN PDF files to extract product receipt information")
        
        # File uploader for GRN
        grn_files = st.file_uploader(
            "Choose GRN PDF files", 
            type="pdf", 
            accept_multiple_files=True, 
            key="grn_uploader",
            help="Select multiple GRN PDF files to process them together"
        )
        
        if grn_files:
            st.session_state.grn_files = grn_files
            st.session_state.grn_processed = False
            
            # Display file summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(grn_files)}</div>
                    <div class="metric-label">Files Uploaded</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                total_size = sum([file.size for file in grn_files]) / (1024 * 1024)  # MB
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_size:.1f}</div>
                    <div class="metric-label">MB Total Size</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Process and Clear buttons
        col1, col2 = st.columns([3, 1])
        with col1:
            process_grn = st.button("🚀 Process GRN Files", disabled=not grn_files, key="process_grn")
        with col2:
            if st.button("🗑️ Clear", key="clear_grn"):
                st.session_state.grn_files = []
                st.session_state.grn_processed = False
                st.session_state.grn_data = None
                st.session_state.grn_errors = []
                st.rerun()
        
        # Process GRN files
        if process_grn and grn_files:
            with st.spinner("Processing GRN files..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process files
                df, errors = process_grn_files(grn_files)
                
                progress_bar.progress(100)
                status_text.text("Processing complete!")
                
                st.session_state.grn_data = df
                st.session_state.grn_errors = errors
                st.session_state.grn_processed = True
        
        # Display GRN results
        if st.session_state.grn_processed and st.session_state.grn_data is not None:
            df = st.session_state.grn_data
            
            # Success metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(df)}</div>
                    <div class="metric-label">Records Extracted</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                unique_vendors = df['vendor_name'].nunique() if 'vendor_name' in df.columns else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{unique_vendors}</div>
                    <div class="metric-label">Unique Vendors</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                unique_stores = df['store_name'].nunique() if 'store_name' in df.columns else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{unique_stores}</div>
                    <div class="metric-label">Unique Stores</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f'<div class="success-box">✅ Successfully processed {len(st.session_state.grn_files)} GRN file(s) and extracted {len(df)} product records!</div>', unsafe_allow_html=True)
            
            # Data preview
            with st.expander("📊 View Extracted GRN Data", expanded=True):
                st.dataframe(df, use_container_width=True, height=400)
            
            # Download Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='GRN_Data')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download GRN Excel File",
                data=excel_data,
                file_name=f"grn_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_grn_excel"
            )
            
        elif st.session_state.grn_processed and st.session_state.grn_data is None:
            st.markdown('<div class="error-box">❌ No valid GRN data could be extracted from the uploaded files.</div>', unsafe_allow_html=True)
        
        # Display GRN errors
        if st.session_state.grn_errors:
            with st.expander("⚠️ Processing Errors", expanded=False):
                for error in st.session_state.grn_errors:
                    st.error(error)
    
    # PRN Tab
    with tab2:
        st.header("Purchase Return Note (PRN) Parser")
        st.markdown("Upload PRN PDF files to extract goods return delivery challan information")
        
        # File uploader for PRN
        prn_files = st.file_uploader(
            "Choose PRN PDF files", 
            type="pdf", 
            accept_multiple_files=True, 
            key="prn_uploader",
            help="Select multiple PRN files to process them together"
            )
        
        if prn_files:
            st.session_state.prn_files = prn_files
            st.session_state.prn_processed = False
            
            # Display file summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(prn_files)}</div>
                    <div class="metric-label">Files Uploaded</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                total_size = sum([file.size for file in prn_files]) / (1024 * 1024)  # MB
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_size:.1f}</div>
                    <div class="metric-label">MB Total Size</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Process and Clear buttons
        col1, col2 = st.columns([3, 1])
        with col1:
            process_prn = st.button("🚀 Process PRN Files", disabled=not prn_files, key="process_prn")
        with col2:
            if st.button("🗑️ Clear", key="clear_prn"):
                st.session_state.prn_files = []
                st.session_state.prn_processed = False
                st.session_state.prn_data = None
                st.session_state.prn_errors = []
                st.rerun()
        
        # Process PRN files
        if process_prn and prn_files:
            with st.spinner("Processing PRN files..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process files
                df, errors = process_prn_files(prn_files)
                
                progress_bar.progress(100)
                status_text.text("Processing complete!")
                
                st.session_state.prn_data = df
                st.session_state.prn_errors = errors
                st.session_state.prn_processed = True
        
        # Display PRN results
        if st.session_state.prn_processed and st.session_state.prn_data is not None:
            df = st.session_state.prn_data
            
            # Success metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(df)}</div>
                    <div class="metric-label">Records Extracted</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                unique_vendors = df['vendor_name'].nunique() if 'vendor_name' in df.columns else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{unique_vendors}</div>
                    <div class="metric-label">Unique Vendors</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                unique_stores = df['store'].nunique() if 'store' in df.columns else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{unique_stores}</div>
                    <div class="metric-label">Unique Stores</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f'<div class="success-box">✅ Successfully processed {len(st.session_state.prn_files)} PRN file(s) and extracted {len(df)} return records!</div>', unsafe_allow_html=True)
            
            # Data preview
            with st.expander("📊 View Extracted PRN Data", expanded=True):
                st.dataframe(df, use_container_width=True, height=400)
            
            # Download Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='PRN_Data')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download PRN Excel File",
                data=excel_data,
                file_name=f"prn_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_prn_excel"
            )
            
        elif st.session_state.prn_processed and st.session_state.prn_data is None:
            st.markdown('<div class="error-box">❌ No valid PRN data could be extracted from the uploaded files.</div>', unsafe_allow_html=True)
        
        # Display PRN errors
        if st.session_state.prn_errors:
            with st.expander("⚠️ Processing Errors", expanded=False):
                for error in st.session_state.prn_errors:
                    st.error(error)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p>🏪 Nature's Basket PDF Parser | Built with Streamlit</p>
        <p>Upload your PDF documents and get organized Excel data in seconds!</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()