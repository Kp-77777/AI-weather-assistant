import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st
import geocoder
from io import BytesIO

# --- Load Environment Variables ---
load_dotenv()
gemini_apikey = os.getenv("gemini_api")
weather_apikey = os.getenv("weather_api")
ELEVENLABS_API_KEY = os.getenv("elevenlabs_api")

# --- Configure Gemini API ---
genai.configure(api_key=gemini_apikey)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Weather Fetching ---
def weather_report(city_name):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,
        "appid": weather_apikey,
        "units": "metric"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Weather API Error: {str(e)}")
        return None

# --- Gemini: Generate Summary ---
def generate_weather_summary(weather_data, user_input):
    try:
        prompt = (
            f"user asked: {user_input}\n"
            f"Create a direct answer to the user's weather query, followed by a concise summary for {weather_data['name']} with this data:\n"
            f"Temperature: {weather_data['main']['temp']}°C\n"
            f"Feels like: {weather_data['main']['feels_like']}°C\n"
            f"Pressure: {weather_data['main']['pressure']} hPa\n"
            f"Conditions: {weather_data['weather'][0]['description']}\n"
            f"Humidity: {weather_data['main']['humidity']}%\n"
            f"Wind: {weather_data['wind']['speed']} km/h\n"
            "Answer the user's question directly first, then provide a clean, factual summary in words"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

# --- Gemini: Extract City ---
def extract_city_name(user_input):
    try:
        prompt = (
            f"Extract only the city name from this input: \"{user_input}\". "
            "Return just the city name or 'no_valid_city'."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"⚠️ City extraction error: {str(e)}")
        return "no_valid_city"

# --- ElevenLabs Text-to-Speech ---
def text_to_speech(text, voice_id="21m00Tcm4TlvDq8ikWAM"):
    if not ELEVENLABS_API_KEY:
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.85
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        st.error(f"🔊 TTS Error: {e}")
        return None

# --- Streamlit UI Setup ---
st.set_page_config(page_title="🌤️ Weather Assistant", page_icon="🌦️", layout="centered")

st.markdown("""
    <h1 style='text-align: center; color: #4f8bf9;'>🌤️ Weather Assistant</h1>
    <p style='text-align: center; font-size: 18px;'>Your AI-powered weather sidekick ☁️</p>
    """, unsafe_allow_html=True)

# --- Sidebar Settings ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1779/1779940.png", width=100)
    st.header("🔧 Voice Settings")
    voice_option = st.selectbox("🗣️ Choose Voice", ("Rachel", "Bella", "Antoni", "Daniel"))
    voice_map = {
        "Rachel": "21m00Tcm4TlvDq8ikWAM",
        "Bella": "EXAVITQu4vr4xnSDxMaL",
        "Antoni": "AZnzlk1XvdvUeBnXmlld",
        "Daniel": "IKne3meq5aSn9XLyUdCD"
    }
    st.caption("🌍 Powered by ElevenLabs")

# --- User Input ---
#st.markdown("## 📍 Mention City or Use Location")

st.markdown("""
    <h3 style='text-align: left; ;'>📍 Mention City or Use Location</h3>
    <p style='text-align: left; font-size: 18px;'>please ask only about weather</p>
    """, unsafe_allow_html=True)
col1, col2 = st.columns([3, 1])
with col1:
    user_input = st.text_input("", placeholder="e.g. What's the weather in Tokyo?")
with col2:
    if st.button("📍 Detect My Location"):
        try:
            g = geocoder.ip('me')
            if g.city:
                st.session_state.location = g.city
                st.rerun()
            else:
                st.error("⚠️ Couldn't detect location.")
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")

# --- Determine City ---
city_name = None
if "location" not in st.session_state:
    st.session_state.location = ""

if st.session_state.location:
    city_name = st.session_state.location
elif user_input:
    extracted_city = extract_city_name(user_input)
    if extracted_city != "no_valid_city":
        city_name = extracted_city

# --- Weather Display ---
if city_name:
    with st.spinner(f"🌍 Fetching weather for **{city_name}**..."):
        weather_data = weather_report(city_name)

    if weather_data:
        summary = generate_weather_summary(weather_data, user_input)
        csummary=""
        l="!@#$%&*"
        for i in summary:
            if i not in l:
                csummary+=i


        st.markdown("## 📊 Weather Details")
        st.markdown(f"### 📌 {weather_data['name']}, {weather_data['sys']['country']}")
        st.markdown(f"**Condition**: {weather_data['weather'][0]['main']} - {weather_data['weather'][0]['description']}")

        col1, col2, col3 = st.columns(3)
        col1.metric("🌡️ Temp", f"{weather_data['main']['temp']}°C")
        col2.metric("🤗 Feels Like", f"{weather_data['main']['feels_like']}°C")
        col3.metric("💧 Humidity", f"{weather_data['main']['humidity']}%")

        col4, col5 = st.columns(2)
        col4.metric("🌬️ Wind", f"{weather_data['wind']['speed']} km/h")
        col5.metric("📈 Pressure", f"{weather_data['main']['pressure']} hPa")

        st.markdown("### 📝Summary")
        st.info(summary)

        if ELEVENLABS_API_KEY and st.button("🔊 Listen"):
            with st.spinner("🎧 Generating audio..."):
                audio = text_to_speech(csummary, voice_map[voice_option])
                if audio:
                    st.audio(audio, format="audio/mp3")
    else:
        st.error("⚠️ Couldn't fetch weather data.")
elif user_input:
    st.warning("⚠️ Please specify a valid city or use location detection.")

# --- Footer ---
st.markdown("---")
st.markdown("<p style='text-align: center;'>Powered by Google Gemini, OpenWeatherMap & ElevenLabs</p>", unsafe_allow_html=True)
