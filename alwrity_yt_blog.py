import os
import time
import requests
import streamlit as st
from pytubefix import YouTube  # Changed from pytube to pytubefix
import google.generativeai as genai
from dotenv import load_dotenv
import re

# Load environment variables from .env file (as fallback)
load_dotenv()

# Initialize session state for API keys if not already present
if 'api_keys_set' not in st.session_state:
    st.session_state.api_keys_set = False

if 'assemblyai_key' not in st.session_state:
    st.session_state.assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY', '')
    
if 'gemini_key' not in st.session_state:
    st.session_state.gemini_key = os.getenv('GEMINI_API_KEY', '')

def validate_api_keys():
    """Validate that required API keys are present in session state"""
    missing_keys = []
    
    # Check for AssemblyAI API key
    if not st.session_state.assemblyai_key:
        missing_keys.append("ASSEMBLYAI_API_KEY")
    
    # Check for Gemini API key
    if not st.session_state.gemini_key:
        missing_keys.append("GEMINI_API_KEY")
    
    return missing_keys

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    # Regular expressions to match different YouTube URL formats
    youtube_regex = (
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    
    youtube_match = re.match(youtube_regex, url)
    if youtube_match:
        return youtube_match.group(6)
    return None

def get_youtube_transcript(yt_url):
    """Extract transcript from YouTube video using AssemblyAI"""
    ASSEMBLYAI_API_KEY = st.session_state.assemblyai_key
    if not ASSEMBLYAI_API_KEY:
        st.error("AssemblyAI API key not set. Please set it in the API Keys section.")
        return None
        
    base_url = "https://api.assemblyai.com"
    headers = {"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"}
    temp_audio = 'temp_audio.mp4'
    
    try:
        # Validate YouTube URL
        if not yt_url:
            st.error("Please enter a YouTube URL.")
            return None
            
        # Extract video ID and create a clean URL
        video_id = extract_video_id(yt_url)
        if not video_id:
            st.error("Invalid YouTube URL format. Please enter a valid YouTube URL.")
            return None
            
        # Create a clean URL to avoid issues
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
            
        with st.status("Processing YouTube video...") as status:
            status.update(label="Downloading audio from YouTube...")
            # Download audio from YouTube with error handling
            try:
                # Apply the cipher fix for PyTube
                try:
                    # Create YouTube object with additional options
                    yt = YouTube(
                        clean_url,
                        use_oauth=False,
                        allow_oauth_cache=True
                    )
                except Exception as e:
                    st.error(f"Error initializing YouTube object: {str(e)}")
                    # Try alternative approach
                    yt = YouTube(clean_url)
                
                # Get video information
                try:
                    video_title = yt.title
                    video_length = yt.length  # Length in seconds
                except Exception as e:
                    st.warning(f"Could not get video metadata: {str(e)}. Continuing anyway...")
                    video_title = "Unknown Title"
                    video_length = 0
                
                # Check if video is too long (over 30 minutes)
                if video_length > 1800:  # 30 minutes in seconds
                    st.warning(f"⚠️ Video is {video_length//60} minutes long. Processing may take a while.")
                
                if video_title != "Unknown Title":
                    st.info(f"📹 Video: {video_title} ({video_length//60}:{video_length%60:02d})")
                
                # Try multiple approaches to get audio stream
                audio_stream = None
                stream_attempts = [
                    lambda: yt.streams.filter(only_audio=True, file_extension='mp4').first(),
                    lambda: yt.streams.filter(only_audio=True, file_extension='webm').first(),
                    lambda: yt.streams.filter(only_audio=True).first(),
                    lambda: yt.streams.filter(progressive=True).first(),
                    lambda: yt.streams.first()
                ]
                
                for attempt in stream_attempts:
                    try:
                        audio_stream = attempt()
                        if audio_stream:
                            # Update file extension if needed
                            if hasattr(audio_stream, 'subtype') and audio_stream.subtype:
                                temp_audio = f'temp_audio.{audio_stream.subtype}'
                            break
                    except Exception as e:
                        continue
                
                if not audio_stream:
                    st.error("Sorry, couldn't find any suitable stream for this video.")
                    return None
                    
                # Download the audio with a timeout
                try:
                    audio_stream.download(filename=temp_audio, timeout=60)
                except Exception as download_error:
                    st.error(f"Error downloading audio: {str(download_error)}")
                    # Try alternative download method
                    try:
                        st.info("Trying alternative download method...")
                        audio_stream.download(output_path=".", filename=temp_audio)
                    except Exception as alt_error:
                        st.error(f"Alternative download also failed: {str(alt_error)}")
                        return None
                
                # Verify the download
                if not os.path.exists(temp_audio):
                    st.error("Audio file was not downloaded.")
                    return None
                    
                if os.path.getsize(temp_audio) < 1000:  # Less than 1KB
                    st.error("Downloaded audio file is too small to be valid.")
                    os.remove(temp_audio)
                    return None
                    
                status.update(label="Uploading audio to transcription service...")
                # Upload audio file to AssemblyAI
                try:
                    with open(temp_audio, "rb") as f:
                        response = requests.post(
                            f"{base_url}/v2/upload",
                            headers={"authorization": ASSEMBLYAI_API_KEY},
                            data=f
                        )
                except Exception as upload_error:
                    st.error(f"Error uploading to AssemblyAI: {str(upload_error)}")
                    if os.path.exists(temp_audio):
                        os.remove(temp_audio)
                    return None
                    
                # Clean up temp file immediately after upload
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                    
                if response.status_code != 200:
                    st.error(f"AssemblyAI upload error: {response.text}")
                    return None
                    
                upload_url = response.json().get("upload_url")
                if not upload_url:
                    st.error("No upload_url returned from AssemblyAI.")
                    return None
                    
                # Request transcript
                status.update(label="Requesting transcription...")
                transcript_request = {
                    "audio_url": upload_url,
                    "language_detection": True,  # Auto-detect language
                    "speech_model": "universal"
                }
                
                transcript_response = requests.post(
                    f"{base_url}/v2/transcript",
                    json=transcript_request,
                    headers=headers
                )
                
                if transcript_response.status_code != 200:
                    st.error(f"AssemblyAI transcript request error: {transcript_response.text}")
                    return None
                    
                transcript_id = transcript_response.json().get('id')
                if not transcript_id:
                    st.error("No transcript ID returned from AssemblyAI.")
                    return None
                    
                # Poll for transcription results
                polling_endpoint = f"{base_url}/v2/transcript/{transcript_id}"
                status.update(label="Transcribing audio... This may take a few minutes.")
                
                # Initialize progress based on video length
                progress_bar = st.progress(0)
                start_time = time.time()
                estimated_time = max(video_length * 0.5, 30)  # Rough estimate: half of video length or at least 30 seconds
                
                while True:
                    polling_response = requests.get(polling_endpoint, headers=headers)
                    if polling_response.status_code != 200:
                        st.error(f"Error checking transcription status: {polling_response.text}")
                        return None
                        
                    transcription_result = polling_response.json()
                    status_value = transcription_result.get('status')
                    
                    # Update progress bar
                    elapsed = time.time() - start_time
                    progress = min(elapsed / estimated_time, 0.95)  # Cap at 95% until complete
                    progress_bar.progress(progress)
                    
                    if status_value == 'completed':
                        progress_bar.progress(1.0)
                        status.update(label="Transcription completed!", state="complete")
                        return transcription_result.get('text')
                    elif status_value == 'error':
                        st.error(f"Transcription failed: {transcription_result.get('error')}")
                        return None
                    else:
                        # Wait before polling again
                        time.sleep(3)
                        
            except Exception as e:
                st.error(f"Error processing YouTube video: {str(e)}")
                return None
                
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        # Clean up temp file if it exists
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        return None

def generate_yt_blog(yt_url):
    """Generate a blog post from a YouTube video"""
    transcript = get_youtube_transcript(yt_url)
    if not transcript:
        return None
        
    # Check transcript length
    if len(transcript.split()) < 50:  # Less than 50 words
        st.warning("⚠️ The transcript is very short. The generated blog may not be comprehensive.")
        
    return summarize_youtube_video(transcript)

def summarize_youtube_video(yt_transcript):
    """Use Gemini AI to transform transcript into a blog post"""
    # Truncate transcript if it's too long for the model
    max_transcript_length = 25000  # Characters
    if len(yt_transcript) > max_transcript_length:
        st.warning(f"⚠️ Transcript is very long ({len(yt_transcript)} characters). Truncating to {max_transcript_length} characters.")
        yt_transcript = yt_transcript[:max_transcript_length] + "..."
    
    prompt = f'''
    You are an expert content writer specializing in digital content writing. I will provide you with a transcript.
    Your task is to transform a given transcript into a well-formatted and informative blog article.

    Please follow the below guidelines:
    1. Master the Transcript: Understand main ideas, key points, and the core message.
    2. Sentence Structure: Rephrase while preserving logical flow and coherence. Don't quote anyone from video.
    3. Write Unique Content: Avoid direct copying; rewrite in your own words.
    4. REMEMBER to avoid direct quoting and maintain uniqueness.
    5. Proofread: Check for grammar, spelling, and punctuation errors.
    6. Use Creative and Human-like Style: Incorporate contractions, idioms, transitional phrases, interjections, and colloquialisms.
    7. Ensure Uniqueness: Guarantee the article is plagiarism-free.
    8. Punctuation: Use appropriate question marks at the end of questions.
    9. Pass AI Detection Tools: Create content that easily passes AI plagiarism detection tools.
    10. Rephrase words like 'video, youtube, channel' with 'article, blog' and such suitable words.

    Make sure that your response is well formatted, with headings, lists, bullet points etc. Respond in markdown style.
    Follow above guidelines to craft a blog content from the following transcript:

    Transcript: {yt_transcript}
    '''
    
    try:
        response = generate_text_with_exception_handling(prompt)
        return response
    except Exception as err:
        st.error(f"Failed to get response from LLM: {str(err)}")
        return None

def generate_text_with_exception_handling(prompt):
    """Generate text using Gemini AI with proper error handling"""
    api_key = st.session_state.gemini_key
    if not api_key:
        st.error("Gemini API key not set. Please set it in the API Keys section.")
        return None
        
    try:
        genai.configure(api_key=api_key)
        
        generation_config = {
            "temperature": 0.7,
            "top_k": 0,
            "max_output_tokens": 4096,
        }
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        # Try to use gemini-1.5-flash, fall back to gemini-1.0-pro if not available
        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
        except Exception as e:
            st.warning(f"Could not use gemini-1.5-flash: {str(e)}. Falling back to gemini-1.0-pro.")
            model = genai.GenerativeModel(
                model_name="gemini-1.0-pro",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
        with st.spinner("Generating blog content with AI..."):
            convo = model.start_chat(history=[])
            response = convo.send_message(prompt)
            return response.text
            
    except Exception as e:
        st.error(f"Error generating text with Gemini: {str(e)}")
        return None

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Alwrity - AI YouTube to Blog Generator",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🧕 Alwrity - AI Youtube link to Blog conversion")
    
    # API Keys Section in Sidebar
    st.sidebar.title("API Keys")
    st.sidebar.info("Enter your API keys below. These will be stored in your session and not saved permanently.")
    
    # AssemblyAI API Key input
    assemblyai_key = st.sidebar.text_input(
        "AssemblyAI API Key",
        value=st.session_state.assemblyai_key,
        type="password",
        help="Get your API key from https://www.assemblyai.com/"
    )
    
    # Gemini API Key input
    gemini_key = st.sidebar.text_input(
        "Gemini API Key",
        value=st.session_state.gemini_key,
        type="password",
        help="Get your API key from https://makersuite.google.com/app/apikey"
    )
    
    # Save API keys to session state
    if st.sidebar.button("Save API Keys"):
        st.session_state.assemblyai_key = assemblyai_key
        st.session_state.gemini_key = gemini_key
        st.session_state.api_keys_set = True
        st.sidebar.success("API keys saved for this session!")
    
    # Check for missing API keys
    missing_keys = validate_api_keys()
    if missing_keys:
        st.error(f"⚠️ Missing API key(s): {', '.join(missing_keys)}")
        st.info("Please enter your API keys in the sidebar.")
        
        # Add links to get API keys
        st.markdown("""  
        ### How to get API keys:
        - **AssemblyAI API Key**: Sign up at [AssemblyAI](https://www.assemblyai.com/)
        - **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
        """)
        return
    
    with st.expander("**PRO-TIP** - Better input yields better results", expanded=True):
        yt_url = st.text_input(
            '**Enter Full Youtube Video URL:**',
            help="A YouTube URL, preferably less than 30 minutes for best results",
            placeholder="https://www.youtube.com/watch?v=vQChW_jgCLM"
        )
        
        st.write("Contact us for processing long videos (duration of hours), local audio files & other AI solutions for your business needs.")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            generate_button = st.button('**Write YT Blog**', type="primary")
            
    if generate_button:
        if yt_url and (yt_url.startswith("https://www.youtube.com/") or yt_url.startswith("https://youtu.be/")):
            with st.spinner("Hang On, Generating AI Blog..."):
                yt_content = generate_yt_blog(yt_url)
                if yt_content:
                    st.subheader('**👩🔬👩🔬 Your Youtube Blog Content:**')
                    st.markdown(yt_content)
                    
                    # Add download button for the content
                    st.download_button(
                        label="Download Blog as Markdown",
                        data=yt_content,
                        file_name="youtube_blog.md",
                        mime="text/markdown"
                    )
                else:
                    st.error("💥 **Failed to generate blog content. Please try again!**")
        else:
            st.error("💥 **Please enter a valid YouTube URL!**")

if __name__ == "__main__":
    main()

