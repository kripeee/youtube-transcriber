import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from fpdf import FPDF
import re
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Bulk YouTube Transcript Extractor", layout="wide")
st.title("Bulk YouTube Transcript Extractor")

def get_video_id(url):
    match = re.search(r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})", url.strip())
    return match.group(1) if match else None

def fetch_transcript(url):
    video_id = get_video_id(url)
    if not video_id:
        return url, "Invalid YouTube URL"
    try:
        # Handles youtube-transcript-api v1.2+ as well as older versions
        try:
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id)
        except (AttributeError, TypeError):
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)

        # Extract text safely from items
        text_pieces = []
        for item in transcript_data:
            if hasattr(item, 'text'):
                text_pieces.append(item.text)
            elif isinstance(item, dict) and 'text' in item:
                text_pieces.append(item['text'])
            else:
                text_pieces.append(str(item))

        full_text = " ".join(text_pieces)
        return url, full_text
    except Exception as e:
        return url, f"Error: Could not retrieve transcript ({str(e)})"

def generate_pdf(transcripts):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    for url, text in transcripts.items():
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Source: {url}", ln=True)
        pdf.ln(2)
        pdf.set_font("Helvetica", size=10)
        cleaned_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, cleaned_text)
        pdf.ln(10)
        
    return pdf.output()

urls_input = st.text_area(
    "Paste YouTube URLs (one per line):", 
    placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/...",
    height=200
)

if st.button("Extract Transcripts"):
    url_list = [u.strip() for u in urls_input.split("\n") if u.strip()]
    
    if not url_list:
        st.warning("Please provide at least one URL.")
    else:
        results = {}
        with st.spinner(f"Extracting {len(url_list)} transcripts in parallel..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_url = {executor.submit(fetch_transcript, url): url for url in url_list}
                for future in future_to_url:
                    url, text = future.result()
                    results[url] = text

        st.success("Extraction complete!")

        # Combine text for download
        combined_text = "\n\n" + "="*50 + "\n\n"
        full_txt_export = combined_text.join([f"URL: {u}\n\n{t}" for u, t in results.items()])

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download as Text File (.txt)",
                data=full_txt_export,
                file_name="bulk_transcripts.txt",
                mime="text/plain"
            )
        with col2:
            pdf_bytes = generate_pdf(results)
            st.download_button(
                label="Download as PDF (.pdf)",
                data=bytes(pdf_bytes),
                file_name="bulk_transcripts.pdf",
                mime="application/pdf"
            )
            