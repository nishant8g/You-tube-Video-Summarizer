import streamlit as st
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Prompt for bullet-point summarization
prompt = """
You are a YouTube video summarizer.
You will take the transcript text and summarize the entire video.
Provide the summary as clear and concise bullet points, with each point representing a key idea or topic from the video.
Ensure the summary is within 250 words.
Please provide the bullet-pointed summary for the text given: .
"""

# Function to extract video ID from various YouTube URL formats
def extract_video_id(youtube_url):
    try:
        parsed_url = urlparse(youtube_url)
        if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]
        elif parsed_url.hostname == "youtu.be":
            return parsed_url.path.lstrip("/")
        else:
            raise ValueError("Invalid YouTube URL format")
    except Exception as e:
        raise ValueError("Error parsing YouTube URL: " + str(e))

# Function to fetch transcript details
def extract_transcript_details(video_id):
    try:
        available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try to fetch the English transcript
        if 'en' in [transcript.language_code for transcript in available_transcripts]:
            transcript_data = available_transcripts.find_transcript(['en']).fetch()
        elif 'hi' in [transcript.language_code for transcript in available_transcripts]:
            # Fall back to Hindi if English is unavailable
            transcript_data = available_transcripts.find_transcript(['hi']).fetch()
        else:
            raise Exception("Neither English nor Hindi transcript is available for this video.")

        # Combine transcript data into a single string
        transcript = " ".join([item["text"] for item in transcript_data])
        return transcript, 'hi' if 'hi' in [transcript.language_code for transcript in available_transcripts] else 'en'

    except TranscriptsDisabled:
        raise Exception(f"Transcripts are disabled for the video: {video_id}")
    except NoTranscriptFound:
        raise Exception(f"No transcript found for the video: {video_id}")
    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")

# Function to translate Hindi to English using Google Generative AI
def translate_to_english(text):
    translation_prompt = f"""
    Translate the following text to English:
    {text}
    """
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(translation_prompt)
    return response.text

# Function to generate summary using Google Gemini Pro
def generate_gemini_content(transcript_text, prompt, is_hindi=False):
    if is_hindi:
        # Translate the Hindi transcript to English
        transcript_text = translate_to_english(transcript_text)
    
    # Generate a summary using the translated English text
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt + transcript_text)
    return response.text

# Inject custom CSS for background
def add_custom_css():
    st.markdown(
        """
        <style>
        body {
            background: linear-gradient(to right, #ff7e5f, #feb47b); /* Gradient background */
            color: #ffffff; /* White text for better contrast */
        }
        .main {
            background-color: rgba(0, 0, 0, 0.7); /* Semi-transparent black box */
            padding: 20px;
            border-radius: 10px;
        }
        h1, h2, h3, .markdown-text-container {
            color: #ffffff; /* Adjust header colors */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Apply custom CSS
add_custom_css()

# Streamlit UI
st.title("YouTube Transcript to Bullet-Pointed Notes Converter")
youtube_link = st.text_input("Enter YouTube Video Link:")

if youtube_link:
    try:
        video_id = extract_video_id(youtube_link)
        if video_id:
            st.image(f"https://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)
        else:
            st.error("Invalid YouTube Video URL")
    except ValueError as e:
        st.error(str(e))

if st.button("Get Detailed Notes"):
    try:
        if not youtube_link:
            st.error("Please enter a YouTube video link!")
        else:
            video_id = extract_video_id(youtube_link)
            if not video_id:
                st.error("Unable to extract video ID. Please check the URL.")
            else:
                transcript_text, language_used = extract_transcript_details(video_id)
                is_hindi = language_used == 'hi'  # Detect if the text is in Hindi
                summary = generate_gemini_content(transcript_text, prompt, is_hindi=is_hindi)
                st.markdown("## Detailed Notes:")
                st.markdown(summary)  # Render as markdown for bullet points
    except Exception as e:
        st.error(str(e))
