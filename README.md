## Alwrity:  AI-Powered YouTube to Blog Conversion

This Streamlit app leverages the power of Google's Gemini AI model to transform YouTube videos into informative and engaging blog posts. It's a quick and easy way to repurpose your video content and reach a wider audience through written articles.

### Features:

* **Automatic Transcription:**  Quickly transcribes YouTube videos using the `youtube_transcript_api`.
* **AI-Powered Summarization and Formatting:** Uses Gemini to analyze the transcript, summarize key points, and generate a well-structured blog article with headings, lists, and appropriate formatting.
* **Human-like Writing Style:** The AI output avoids direct quoting and uses contractions, idioms, and other elements to create a more natural and engaging writing style. 
* **Plagiarism Prevention:**  The AI incorporates safeguards to ensure that the generated blog content is unique and passes AI plagiarism detection tools. 

### Getting Started:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/alwrity-youtube-to-blog.git
   ```
2. **Install Dependencies:**
   ```bash
   cd alwrity-youtube-to-blog
   pip install -r requirements.txt
   ```
3. **Create a `.env` File:**
   - Create a file named `.env` in the project directory.
   - Add your Google Gemini API key:
     ```
     GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
     ```
4. **Run the App:**
   ```bash
   streamlit run main.py
   ```

### Usage:

1. **Enter the YouTube URL:**  Paste the full URL of the YouTube video you want to convert. Make sure the video is less than 10 minutes long for optimal results.
2. **Click "Write YT Blog":**  The app will automatically fetch the video transcript and use Gemini AI to generate a blog post.
3. **Review and Edit:** The generated blog content will appear in a markdown format, ready for you to review and edit.

**Additional Notes:**

*  This app requires a Google Gemini API key. 
*  You can customize the AI's behavior by adjusting the prompt in the `summarize_youtube_video` function.
*  The app currently supports YouTube videos under 10 minutes.  For longer videos, consider breaking them into shorter segments or contacting the developer for custom solutions.

### Contributing:

Contributions are welcome! Feel free to open an issue or submit a pull request.

### License:

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


### Example Usage:

```
Enter Full Youtube Video URL: https://www.youtube.com/watch?v=vQChW_jgCLM

# Output:

👩🔬👩🔬 Your Yourtube Blog Content:

## The Power of AI:  A Comprehensive Guide 

This article delves into the fascinating world of artificial intelligence (AI), exploring its capabilities and potential impact on various aspects of our lives.  AI is rapidly transforming industries and society as a whole, bringing about a new era of technological advancements. 

### What is AI?

AI refers to the simulation of human intelligence processes by computer systems. It encompasses various technologies, including machine learning, deep learning, natural language processing, and computer vision. AI algorithms are trained on massive datasets to learn patterns and make predictions, enabling machines to perform tasks that typically require human intelligence.

### Applications of AI:

AI has numerous applications across diverse domains, including:

* **Healthcare:** AI-powered systems can assist in disease diagnosis, drug discovery, and personalized treatment plans.
* **Finance:** AI algorithms can help in fraud detection, risk assessment, and algorithmic trading.
* **Transportation:**  Autonomous vehicles are being developed using AI for self-driving capabilities. 
* **Education:**  AI tutors can provide personalized learning experiences and adaptive learning platforms. 

### Benefits of AI:

* **Increased Efficiency:** AI can automate tasks, freeing up human time for more complex and creative endeavors.
* **Improved Accuracy:** AI algorithms can make predictions and decisions with greater precision than humans.
* **Enhanced Customer Experiences:** AI chatbots and virtual assistants can provide personalized customer support and recommendations.
* **Innovation and Discovery:**  AI is enabling new breakthroughs in science, technology, and medicine.

### Conclusion:

The rise of AI is reshaping our world in profound ways. By understanding its capabilities and potential, we can harness its power for a better future.

```
This is just an example, the actual content will be generated from the video you provide.

