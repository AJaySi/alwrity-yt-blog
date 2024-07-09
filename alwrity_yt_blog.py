import time
import os
import json
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_random_exponential
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re


def get_youtube_transcript(yt_url):
	"""
	Fetches the transcript of a YouTube video given its URL.
	
	Args:
	    yt_url (str): The URL of the YouTube video.
	
	Returns:
	    list: A list of dictionaries representing the transcript segments,
	          or None if the transcript is not available.
	"""
	video_id = re.search(r'v=([^&]+)', yt_url).group(1)
	try:
	    transcript = YouTubeTranscriptApi.get_transcript(video_id)
	    return transcript
	except:
	    print("Error: Transcript not available for this video.")
	    return None


def main():
    set_page_config()
    custom_css()
    hide_elements()
    title_and_description()
    input_section()

def set_page_config():
    st.set_page_config(
        page_title="Alwrity - AI YouTube to Blog Generator",
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
                    ::-webkit-scrollbar-track {
        background: #e1ebf9;
        }

        ::-webkit-scrollbar-thumb {
            background-color: #90CAF9;
            border-radius: 10px;
            border: 3px solid #e1ebf9;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #64B5F6;
        }

        ::-webkit-scrollbar {
            width: 16px;
        }
        div.stButton > button:first-child {
            background: #1565C0;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 10px 2px;
            cursor: pointer;
            transition: background-color 0.3s ease;
            box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
            font-weight: bold;
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


def input_section():
    with st.expander("**PRO-TIP** - Better input yield, better results.", expanded=True):
        yt_url = st.text_input('**Enter Full Youtube Video URL:**',
                help="A single YT URL, less than 10 minutes",
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


def generate_yt_blog(yt_url):
        """Use Gemini Flash to get transcript from youtube URL """
        with st.spinner(f"Transcribing youtube URL: {yt_url}"):
            try:
                transcript = get_youtube_transcript(yt_url)
                return summarize_youtube_video(transcript)
            except Exception as err:
                st.error(f"Exit: Failed to get response from LLM: {err}")
                exit(1)
            

def summarize_youtube_video(yt_transcript):
    """Generates a summary of a YouTube video using OpenAI GPT-3 and displays a progress bar. 
    Args:
      video_link: The URL of the YouTube video to summarize.
    Returns:
      A string containing the summary of the video.
    """
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
    
    try:
        response = generate_text_with_exception_handling(prompt)
        return response
    except Exception as err:
        st.error(f"Exit: Failed to get response from LLM: {err}")
        exit(1)


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def generate_text_with_exception_handling(prompt):
    """
    Generates text using the Gemini model with exception handling.

    Args:
        api_key (str): Your Google Generative AI API key.
        prompt (str): The prompt for text generation.

    Returns:
        str: The generated text.
    """

    try:
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

        generation_config = {
            "temperature": 0.7,
            "top_k": 0,
            "max_output_tokens": 4096,
        }

        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]

        model = genai.GenerativeModel(model_name="gemini-1.5-flash",
                                      generation_config=generation_config,
                                      safety_settings=safety_settings)

        convo = model.start_chat(history=[])
        convo.send_message(prompt)
        return convo.last.text

    except Exception as e:
        st.exception(f"An unexpected error occurred: {e}")
        return None


if __name__ == "__main__":
    main()

