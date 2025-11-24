import os
import requests
import random
import time
from flask import Flask, render_template, request, jsonify
from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Function to get trending keywords
def get_trending_keywords(topic):
    pytrends = TrendReq(hl='en-US', tz=360)
    retries = 3
    delay = 1
    for i in range(retries):
        try:
            pytrends.build_payload([topic], cat=0, timeframe='today 5-y', geo='', gprop='')
            related_queries = pytrends.related_queries()
            trending_keywords = []
            if related_queries[topic]['top'] is not None:
                trending_keywords = related_queries[topic]['top']['query'].tolist()
            return trending_keywords, True
        except TooManyRequestsError:
            print(f"Google Trends API rate limit reached. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2
    print("Warning: Google Trends API rate limit reached after multiple retries. Proceeding without trending keywords.")
    return [], False

# Function to generate post content
def generate_post_content(topic, keywords):
    model = genai.GenerativeModel('gemini-2.5-flash')
    # First, generate better keywords
    keyword_prompt = f"Generate a list of 5-10 highly relevant and engaging keywords for the topic: '{topic}'. Focus on broader concepts and avoid overly specific or local queries. For example, for 'Hyderabad', good keywords would be 'Hyderabad history', 'charminar', 'hyderabadi biryani', 'telangana tourism'. Return as a comma-separated list."
    keyword_response = model.generate_content(keyword_prompt)
    generated_keywords = [kw.strip() for kw in keyword_response.text.split(',')]
    
    # Then, generate the post with the new keywords
    prompt = f"Topic: '{topic}'. Keywords: {', '.join(generated_keywords)}. Generate exactly three distinct social media posts, each under 280 characters. Separate each post with '---'. Output only the raw post text. No other text, headings, or explanations."
    response = model.generate_content(prompt)
    
    # Return both the posts and the keywords used
    return response.text.split('---'), generated_keywords

# Function to get image keyword from topic
def get_image_keyword_from_topic(topic):
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"Extract the most visually relevant keywords from the following topic for an image search. Focus on the core subject. For example, from 'new google data center in vizag', extract 'google data center'. From 'latest advancements in AI technology', extract 'AI technology'. Topic: '{topic}'. Output only the keywords."
    response = model.generate_content(prompt)
    return response.text.strip()

# Function to get an image from Unsplash
def get_unsplash_image(query):
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    url = f"https://api.unsplash.com/photos/random?query={query}&client_id={access_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        # Check if the response contains the 'urls' key and its 'regular' subkey
        if data and 'urls' in data and 'regular' in data['urls']:
            return data['urls']['regular']
        else:
            print("Warning: Unsplash API response did not contain a valid image URL.")
            # Fallback will be triggered below
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from Unsplash: {e}")
    
    # Return a fallback image if anything goes wrong
    return "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"

# Function to post to social media using Ayrshare
def post_to_social_media(post_content, image_url, platforms):
    api_key = os.getenv("AYRSHARE_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "post": post_content,
        "platforms": platforms,
        "media_urls": [image_url]
    }
    url = "https://app.ayrshare.com/api/post"
    response = requests.post(url, json=data, headers=headers)
    return response.json()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    topic = data['topic']

    # 1. Get keyword from topic
    image_keyword = get_image_keyword_from_topic(topic)
    print(f"Using keyword for Trends & Unsplash: {image_keyword}")

    # 2. Get trending keywords based on the extracted keyword
    keywords, trends_ok = get_trending_keywords(image_keyword)

    # 3. Generate post content
    post_suggestions_text, generated_keywords = generate_post_content(topic, keywords)
    # The original 'keywords' from pytrends are now replaced by our generated ones for display
    keywords = generated_keywords

    # 3. Get an image for each suggestion
    suggestions_with_images = []
    for i, post_text in enumerate(post_suggestions_text):
        # Use the same keyword for the image query
        image_url = get_unsplash_image(image_keyword)
        suggestions_with_images.append({"post": post_text.strip(), "image_url": image_url})

    return jsonify({
        "suggestions": suggestions_with_images,
        "trends_ok": trends_ok,
        "keywords": keywords
    })

@app.route('/post', methods=['POST'])
def post():
    data = request.get_json()
    post_content = data['post']
    platforms = data['platforms']
    image_url = data['image_url']

    # 1. Post to social media
    result = post_to_social_media(post_content, image_url, platforms)

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)