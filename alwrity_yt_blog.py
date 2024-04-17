import time
import os
import json
from openai import OpenAI
import streamlit as st
from pytube import YouTube
from tenacity import retry, stop_after_attempt, wait_random_exponential

def main():
    set_page_config()
    custom_css()
    hide_elements()
    title_and_description()
    input_section()

def set_page_config():
    st.set_page_config(
        page_title="Alwrity - YouTube to Blog Generator",
        layout="wide",
    )

def custom_css():
    st.markdown("""
        <style>
            .block-container {
                padding-top: 0rem;
                padding-bottom: 0rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
            [class="st-emotion-cache-7ym5gk ef3psqc12"] {
                display: inline-block;
                padding: 5px 20px;
                background-color: #4681f4;
                color: #FBFFFF;
                width: 300px;
                height: 35px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                border-radius: 8px;
            }
        </style>
    """, unsafe_allow_html=True)

def hide_elements():
    hide_decoration_bar_style = '<style>header {visibility: hidden;}</style>'
    st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

    hide_streamlit_footer = '<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>'
    st.markdown(hide_streamlit_footer, unsafe_allow_html=True)


def title_and_description():
    st.title("🧕 Alwrity - AI Youtube link to Blog conversion.")
    with st.expander("**How to Use** Alwrity YT blog Generator? 📝❗"):
        st.markdown(
        '''---
            # How to Download Audio from YouTube Videos and Local Files

			How to download audio from YouTube videos and local files using Python. 
            Whether you're looking to extract audio for listening on the go or incorporating it into your projects, this guide has got you covered.
			
			## Step 1: Accessing YouTube URLs
			- Check if the provided URL is a YouTube link.
			- If it is, access the YouTube URL and fetch the highest quality audio stream available.
			
			## Step 2: Downloading Audio from YouTube
			- Filter for the audio-only stream of the YouTube video.
			- Download the audio file to the specified output path.
			- Display a progress bar to track the download process.
			
			## Step 3: Handling Local Audio Files
			- If the input is not a YouTube URL, check if it's a valid local audio file.
			- If it is, proceed with the provided local file path.
			
			## Step 4: Checking File Size
			- Ensure that the downloaded audio file does not exceed the maximum file size limit of 24MB.
			- If the file size exceeds the limit, log an error message and handle accordingly.
			
		---''')


def input_section():
    with st.expander("**PRO-TIP** - Better input yield, better results.", expanded=True):
        yt_url = st.text_input('**To get blog content, Enter Full Youtube Video URL:**',
                        help="A single YT URL, less than 25 minutes",
                               placeholder="https://www.youtube.com/watch?v=vQChW_jgCLM")

        st.write("Contact us, to input long videos(duration of hours), local audio files & other AI solutions for your business needs.")
        if st.button('**Write YT Blog**'):
            if yt_url.startswith("https://www.youtube.com/") or yt_url.strip():
                with st.spinner("Hang On, Generating AI Blog..."):
                    yt_content = generate_yt_blog(yt_url)
                    if yt_content:
                        st.subheader('**👩🔬👩🔬 Your Yourtube Blog Content:**')
                        st.markdown(yt_content)
                    else:
                        st.error("💥 **Enter valid youtube URL. Please try again!**")
            else:
                st.error("Input Title/Topic of content to outline, Required!")

    page_bottom()


def generate_yt_blog(yt_url):
        """ """
        audio_file = None
        yt = YouTube(yt_url)
        audio_stream = yt.streams.filter(only_audio=True).first()

        if audio_stream is None:
            st.error("Error: No audio stream found for this video.")
            return None

        with st.spinner(f"Downloading audio for: {yt.title}"):
            audio_file = audio_stream.download()
            if not audio_file:
                st.error(f"Failed to download audio file: {audio_file}")
                return None

        # Checking file size
        max_file_size = 24 * 1024 * 1024  # 24MB
        file_size = os.path.getsize(audio_file)
        # Convert file size to MB for logging
        file_size_MB = file_size / (1024 * 1024)  # Convert bytes to MB
        st.info(f"Downloaded Audio Size is: {file_size_MB:.2f} MB")
        if file_size > max_file_size:
            st.error("Error: File size exceeds 24MB limit.")
            return None

        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        with st.spinner("Initializing OpenAI client for transcription."):
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=open(audio_file, "rb"),
                response_format="text"
            )
        # Remove the downloaded, now that we have the transcription.
        if os.path.exists(audio_file):
            os.remove(audio_file)

        # Summarizing the content of the YouTube video
        return summarize_youtube_video(transcript)
        
#    return transcript, yt.title
#    return openai_chatgpt(prompt)


def page_bottom():
    """Display the bottom section of the web app."""
    with st.expander("Alwrity - Content outline generator - powered by AI (OpenAI, Gemini Pro)."):
        st.write('''
			
			[Get Started Now, Get custom AI solutions](https://alwrity.com)
			---	
			Youtube URL to Blog generator - powered by AI (OpenAI, Gemini Pro).	
			Implemented by [Alwrity](https://alwrity.com).
        ''')


def summarize_youtube_video(yt_transcript):
    """Generates a summary of a YouTube video using OpenAI GPT-3 and displays a progress bar. 
    Args:
      video_link: The URL of the YouTube video to summarize.
    Returns:
      A string containing the summary of the video.
    """

    st.info("Start summarize_youtube_video..")
    prompt = f"""
        You are an expert content writer specializing in digital content writing. I will provide you with a transcript. 
        Your task is to transform a given transcript into a well-formatted and informative blog article. 
        
        Please follow the below guidelines:

        1. Master the Transcript: Understand main ideas, key points, and the core message.
        2. Sentence Structure: Rephrase while preserving logical flow and coherence. Dont quote anyone from video.
        4. Write Unique Content: Avoid direct copying; rewrite in your own words. 
        5. REMEMBER to avoid direct quoting and maintain uniqueness.
        6. Proofread: Check for grammar, spelling, and punctuation errors.
        7. Use Creative and Human-like Style: Incorporate contractions, idioms, transitional phrases, interjections, and colloquialisms.
        9. Ensure Uniqueness: Guarantee the article is plagiarism-free.
        10. Punctuation: Use appropriate question marks at the end of questions.
        11. Pass AI Detection Tools: Create content that easily passes AI plagiarism detection tools.
        12. Rephrase words like 'video, youtube, channel' with 'article, blog' and such suitable words.

        Make sure that your response is well formatted, with headings, lists, bullet points etc. Respond in markdown style.
        Follow above guidelines to craft a blog content from the following transcript:
        \n\nTranscript: {yt_transcript}
        """
    return openai_chatgpt(prompt)


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def openai_chatgpt(prompt, model="gpt-3.5-turbo-0125", max_tokens=2048, top_p=0.6, n=3):
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                n=n,
                top_p=top_p
            )
        return response.choices[0].message.content
    except Exception as err:
        st.error(f"An error occurred: {err}")


if __name__ == "__main__":
    main()

