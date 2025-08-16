import os
import time
import requests
import streamlit as st
from pytubefix import YouTube  # Changed from pytube to pytubefix
import google.generativeai as genai
from dotenv import load_dotenv
import re
import base64

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

def add_custom_css():
    """Add custom CSS for better styling"""
    st.markdown("""
    <style>
    /* Main app styling */
    .main {
        padding-top: 2rem;
    }
    
    /* Header styling */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .header-subtitle {
        font-size: 1.2rem;
        opacity: 0.9;
        margin-bottom: 0;
    }
    
    /* Card styling */
    .info-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .success-card {
        background: #d4edda;
        border-left-color: #28a745;
        color: #155724;
    }
    
    .warning-card {
        background: #fff3cd;
        border-left-color: #ffc107;
        color: #856404;
    }
    
    .error-card {
        background: #f8d7da;
        border-left-color: #dc3545;
        color: #721c24;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e9ecef;
        padding: 0.75rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    
    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-success {
        background-color: #28a745;
    }
    
    .status-error {
        background-color: #dc3545;
    }
    
    .status-warning {
        background-color: #ffc107;
    }
    
    /* Copy button styling */
    .copy-button {
        background: #28a745;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        cursor: pointer;
        font-size: 0.9rem;
        margin-top: 1rem;
    }
    
    .copy-button:hover {
        background: #218838;
    }
    
    /* Animation for loading */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .loading {
        animation: pulse 2s infinite;
    }
    </style>
    """, unsafe_allow_html=True)

def create_header():
    """Create an attractive header section"""
    st.markdown("""
    <div class="header-container">
        <div class="header-title">🎬 Alwrity</div>
        <div class="header-subtitle">Transform YouTube Videos into Engaging Blog Posts with AI</div>
    </div>
    """, unsafe_allow_html=True)

def create_info_card(content, card_type="info"):
    """Create styled info cards"""
    card_class = f"info-card {card_type}-card" if card_type != "info" else "info-card"
    st.markdown(f"""
    <div class="{card_class}">
        {content}
    </div>
    """, unsafe_allow_html=True)

def create_status_indicator(status, text):
    """Create status indicators with colored dots"""
    status_class = f"status-{status}"
    return f'<span class="status-indicator {status_class}"></span>{text}'

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Alwrity - AI YouTube to Blog Generator",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS
    add_custom_css()
    
    # Create header
    create_header()
    
    # API Keys Section in Sidebar
    st.sidebar.markdown("### 🔐 API Configuration")
    st.sidebar.markdown("""
    <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <small>🔒 Your API keys are stored securely in your session and are never saved permanently.</small>
    </div>
    """, unsafe_allow_html=True)
    
    # AssemblyAI API Key input
    st.sidebar.markdown("#### 🎙️ AssemblyAI (Transcription)")
    assemblyai_key = st.sidebar.text_input(
        "API Key",
        value=st.session_state.assemblyai_key,
        type="password",
        placeholder="Enter your AssemblyAI API key",
        help="Get your API key from https://www.assemblyai.com/",
        key="assemblyai_input"
    )
    
    # Show status for AssemblyAI
    if assemblyai_key:
        st.sidebar.markdown(create_status_indicator("success", "AssemblyAI Connected"), unsafe_allow_html=True)
    else:
        st.sidebar.markdown(create_status_indicator("error", "AssemblyAI Not Connected"), unsafe_allow_html=True)
    
    st.sidebar.markdown("#### 🤖 Google Gemini (AI Generation)")
    gemini_key = st.sidebar.text_input(
        "API Key",
        value=st.session_state.gemini_key,
        type="password",
        placeholder="Enter your Gemini API key",
        help="Get your API key from https://makersuite.google.com/app/apikey",
        key="gemini_input"
    )
    
    # Show status for Gemini
    if gemini_key:
        st.sidebar.markdown(create_status_indicator("success", "Gemini Connected"), unsafe_allow_html=True)
    else:
        st.sidebar.markdown(create_status_indicator("error", "Gemini Not Connected"), unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Save API keys to session state
    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.button("💾 Save Keys", use_container_width=True):
            st.session_state.assemblyai_key = assemblyai_key
            st.session_state.gemini_key = gemini_key
            st.session_state.api_keys_set = True
            st.sidebar.success("✅ Keys saved!")
    
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.assemblyai_key = ""
            st.session_state.gemini_key = ""
            st.session_state.api_keys_set = False
            st.rerun()
    
    # Check for missing API keys
    missing_keys = validate_api_keys()
    if missing_keys:
        create_info_card(
            f"""<h4>🔑 API Keys Required</h4>
            <p>Please configure the following API keys in the sidebar:</p>
            <ul>
            {''.join([f'<li><strong>{key}</strong></li>' for key in missing_keys])}
            </ul>""", 
            "warning"
        )
        
        # Create two columns for API key information
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 🎙️ AssemblyAI Setup
            1. Visit [AssemblyAI](https://www.assemblyai.com/)
            2. Create a free account
            3. Get your API key from the dashboard
            4. Paste it in the sidebar
            
            **Features:** High-quality transcription with language detection
            """)
        
        with col2:
            st.markdown("""
            #### 🤖 Google Gemini Setup
            1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
            2. Sign in with your Google account
            3. Generate a new API key
            4. Paste it in the sidebar
            
            **Features:** Advanced AI for blog content generation
            """)
        
        return
    
    # Main content area
    st.markdown("### 🎯 Convert YouTube Video to Blog")
    
    # Create input section with better styling
    with st.container():
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                    padding: 2rem; border-radius: 15px; margin: 1rem 0; 
                    border: 1px solid #dee2e6;">
        """, unsafe_allow_html=True)
        
        st.markdown("#### 📹 Enter YouTube Video URL")
        
        # URL input with validation
        yt_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            help="📝 Paste any YouTube video URL here. Supports all YouTube URL formats.",
            label_visibility="collapsed"
        )
        
        # URL validation feedback
        if yt_url:
            video_id = extract_video_id(yt_url)
            if video_id:
                st.success(f"✅ Valid YouTube URL detected (Video ID: {video_id})")
            else:
                st.error("❌ Invalid YouTube URL format. Please check your URL.")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Pro tips section
    with st.expander("💡 Pro Tips for Better Results", expanded=False):
        st.markdown("""
        **🎯 For best results:**
        - Choose videos with clear audio and speech
        - Educational or tutorial content works exceptionally well
        - Videos between 5-30 minutes are optimal
        - Avoid videos with too much background music
        
        **📊 Supported content:**
        - Tutorials and how-to videos
        - Interviews and podcasts
        - Educational content
        - Product reviews
        - Webinars and presentations
        """)
    
    # Generate button with enhanced styling
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_clicked = st.button(
            "🚀 Generate Blog Post", 
            type="primary", 
            use_container_width=True,
            disabled=not yt_url or not extract_video_id(yt_url) if yt_url else True
        )
    
    # Processing and results
    if generate_clicked:
        if not yt_url:
            st.error("Please enter a YouTube URL.")
        else:
            # Create a results container
            results_container = st.container()
            
            with results_container:
                with st.spinner("🔄 Processing your request..."):
                    blog_content = generate_yt_blog(yt_url)
                    
                if blog_content:
                    # Success message with animation
                    st.balloons()
                    create_info_card(
                        "<h4>🎉 Success!</h4><p>Your blog post has been generated successfully!</p>",
                        "success"
                    )
                    
                    # Display the blog content in a nice container
                    st.markdown("---")
                    st.markdown("## 📝 Generated Blog Post")
                    
                    # Blog content display
                    with st.container():
                        st.markdown("""
                        <div style="background: white; padding: 2rem; border-radius: 10px; 
                                    border: 1px solid #e9ecef; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
                        """, unsafe_allow_html=True)
                        
                        st.markdown(blog_content)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Action buttons
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    with col1:
                        if st.button("📋 Copy to Clipboard", use_container_width=True):
                            # JavaScript to copy to clipboard
                            st.markdown("""
                            <script>
                            navigator.clipboard.writeText(`{}`).then(function() {{
                                console.log('Content copied to clipboard');
                            }});
                            </script>
                            """.format(blog_content.replace('`', '\\`')), unsafe_allow_html=True)
                            st.success("Content copied to clipboard!")
                    
                    with col2:
                        # Download as text file
                        st.download_button(
                            label="💾 Download as TXT",
                            data=blog_content,
                            file_name="youtube_blog_post.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    
                    with col3:
                        # Download as markdown
                        st.download_button(
                            label="📄 Download as MD",
                            data=blog_content,
                            file_name="youtube_blog_post.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                    
                    # Raw content for manual copying
                    with st.expander("📋 Raw Content (for manual copying)"):
                        st.text_area(
                            "Blog content:",
                            value=blog_content,
                            height=300,
                            help="Select all (Ctrl+A) and copy (Ctrl+C) this content.",
                            label_visibility="collapsed"
                        )
                else:
                    create_info_card(
                        "<h4>❌ Generation Failed</h4><p>Unable to generate blog content. Please check your YouTube URL and API keys.</p>",
                        "error"
                    )

    # Add footer with enhanced styling
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; text-align: center; 
                color: white; margin-top: 2rem;">
        <h4 style="margin-bottom: 1rem; color: white;">🚀 Alwrity - AI Content Generator</h4>
        <p style="margin-bottom: 1rem; opacity: 0.9;">Transform your YouTube content into engaging blog posts with the power of AI</p>
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <div style="text-align: center;">
                <div style="font-size: 2rem;">🎬</div>
                <div style="font-size: 0.9rem;">YouTube Integration</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem;">🎙️</div>
                <div style="font-size: 0.9rem;">AI Transcription</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem;">✍️</div>
                <div style="font-size: 0.9rem;">Smart Blog Generation</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem;">📱</div>
                <div style="font-size: 0.9rem;">User-Friendly Interface</div>
            </div>
        </div>
        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.2);">
            <small>Made with ❤️ using Streamlit • Powered by AssemblyAI & Google Gemini</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
