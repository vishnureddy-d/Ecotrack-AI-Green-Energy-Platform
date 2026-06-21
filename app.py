import json
import os
import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

# 1. CONFIGURATION & AI INITIALIZATION
st.set_page_config(
    page_title="EcoTrack - AI Green Energy Calc",
    page_icon="🌱",
    layout="wide"
)

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
api_key_source = None
if os.getenv("GOOGLE_API_KEY"):
    api_key_source = "GOOGLE_API_KEY"
elif os.getenv("GEMINI_API_KEY"):
    api_key_source = "GEMINI_API_KEY"

ai_configured = False
manual_key = st.text_input(
    "Gemini API key",
    value="",
    type="password",
    help="Paste a valid Gemini API key here to override environment settings."
)
if manual_key:
    api_key = manual_key
    api_key_source = "manual input"

if not api_key:
    st.error(
        "Gemini API key not found. Set the GOOGLE_API_KEY or GEMINI_API_KEY environment variable, "
        "or paste a valid key into the input field above."
    )
else:
    st.caption(f"Using API key from `{api_key_source}`")
    try:
        genai.configure(api_key=api_key)
        ai_configured = True
    except Exception as e:
        st.error(
            "Failed to configure Gemini API. The provided API key may be invalid or expired. "
            "Please verify your key and try again."
        )
        st.error(f"Configuration error: {e}")

# Prevent AI calls when configuration failed
if not ai_configured:
    st.warning("AI is not configured. The Analyze button will not execute without a valid API key.")

# Standard Scientific Emission Baselines (Global / India Averages)
EMISSION_FACTORS = {
    "grid_electricity_per_kwh": 0.82,  # kg CO2/kWh (Coal-heavy traditional grid)
    "solar_electricity_per_kwh": 0.05, # kg CO2/kWh (Lifecycle manufacturing emissions)
    "petrol_per_liter": 2.31,          # kg CO2/L
    "diesel_per_liter": 2.68,          # kg CO2/L
}

# 2. CORE LOGIC / AI PROMPT ENGINE

def parse_log_with_ai(user_text_input):
    """Uses Gemini to parse unstructured user logs into a strict JSON scheme."""
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    You are an environmental data processor. Analyze the user's daily activities text and extract metrics related to energy consumption and transport.
    
    User Log: "{user_text_input}"
    
    You MUST return ONLY a valid JSON object matching the exact keys below. Do not include markdown blocks (like ```json), backticks, or text before/after.
    {{
      "grid_electricity_kwh": float or 0,
      "solar_electricity_kwh": float or 0,
      "fuel_liters": float or 0,
      "fuel_type": "petrol" or "diesel" or "none"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean potential markdown wrapping if the model accidentally includes it
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data
    except Exception as e:
        st.error(f"Failed to parse AI response. Error: {e}")
        return None

# 3. USER INTERACTION & DRAWING THE UI

st.title("🌱 EcoTrack: AI Green Energy Platform")
st.markdown("### Understand, track, and optimize your carbon footprint using Generative AI.")
st.write("---")

# Layout columns for input and dashboard results
col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("📝 Log Your Daily Footprint")
    st.caption("Type out your day naturally. Mention your electricity use, solar energy production, or vehicle trips.")
    
    # Pre-filled example for quick hackathon judging/testing
    default_text = "Today I used about 12 kWh of electricity from the main grid, but generated 8 kWh from my rooftop solar setup. I also drove my petrol car for a short grocery run using roughly 3 liters of fuel."
    
    user_input = st.text_area(
        "Describe your energy and transit activities:",
        value=default_text,
        height=150
    )
    
    calculate_btn = st.button("Analyze Footprint with AI ✨", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 Dynamic Carbon Metrics")
    
    if calculate_btn and user_input:
        if not ai_configured:
            st.error(
                "AI is not configured because the Gemini API key is missing or invalid. "
                "Please fix GOOGLE_API_KEY or GEMINI_API_KEY in your environment and reload."
            )
        else:
            with st.spinner("AI parsing metrics and calculating environmental impacts..."):
                extracted = parse_log_with_ai(user_input)
                
                if extracted:
                    # Calculations Engine
                    grid_kwh = extracted.get("grid_electricity_kwh", 0)
                    solar_kwh = extracted.get("solar_electricity_kwh", 0)
                    fuel_L = extracted.get("fuel_liters", 0)
                    fuel_type = extracted.get("fuel_type", "none")
                    
                    grid_co2 = grid_kwh * EMISSION_FACTORS["grid_electricity_per_kwh"]
                    solar_co2 = solar_kwh * EMISSION_FACTORS["solar_electricity_per_kwh"]
                    
                    fuel_key = f"{fuel_type}_per_liter"
                    fuel_co2 = fuel_L * EMISSION_FACTORS.get(fuel_key, 0)
                    
                    total_emissions = grid_co2 + solar_co2 + fuel_co2
                    
                    # What if ALL electricity was solar? (Offset Potential)
                    theoretical_grid_co2_saved = solar_kwh * (EMISSION_FACTORS["grid_electricity_per_kwh"] - EMISSION_FACTORS["solar_electricity_per_kwh"])
                    
                    # Display high-level metric cards
                    m1, m2 = st.columns(2)
                    m1.metric(label="Total Carbon Footprint", value=f"{total_emissions:.2f} kg CO₂")
                    m2.metric(label="Green Energy Savings", value=f"{theoretical_grid_co2_saved:.2f} kg CO₂", delta="Offset Completed")
                    
                    st.write("---")
                    st.write("**AI Extracted Structural Values:**")
                    st.json(extracted)
                    
                    # Visualization breakdown via Plotly chart
                    categories = ['Grid Electricity', 'Solar Minimal Footprint', 'Vehicle Fuel']
                    values = [grid_co2, solar_co2, fuel_co2]
                    
                    fig = go.Figure(data=[
                        go.Pie(
                            labels=categories,
                            values=values,
                            hole=0.4,
                            hoverinfo='label+percent',
                            textinfo='value+label'
                        )
                    ])
                    fig.update_layout(
                        title_text="Carbon Footprint Breakdown by Activity Source (kg CO₂)",
                        margin=dict(t=40, b=0, l=0, r=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.warning("Please verify your input. The AI couldn't formulate structured data from the text.")
    else:
        st.info("Click the 'Analyze Footprint' button to visualize your impact models.")

# 4. HACKATHON VALUE-ADD FEAT: INTERACTIVE SIMULATOR

st.write("---")
st.subheader("⚡ The 'Green Energy Transition' Live Simulator")
st.write("See what happens to your structural carbon footprint if you shift away from coal/grid heavy power sources:")

sim_electricity = st.slider("Total Daily Electricity Needed (kWh)", min_value=5, max_value=50, value=20)
solar_percentage = st.slider("Percentage of Electricity Driven by Solar (%)", min_value=0, max_value=100, value=40)

# Simulate impact
sim_solar_kwh = sim_electricity * (solar_percentage / 100)
sim_grid_kwh = sim_electricity * (1 - (solar_percentage / 100))

sim_co2_total = (sim_grid_kwh * EMISSION_FACTORS["grid_electricity_per_kwh"]) + (sim_solar_kwh * EMISSION_FACTORS["solar_electricity_per_kwh"])
baseline_dirty_co2 = sim_electricity * EMISSION_FACTORS["grid_electricity_per_kwh"]
net_savings = baseline_dirty_co2 - sim_co2_total

sc1, sc2 = st.columns(2)
sc1.markdown(f"**Your Project Emissions Under This Setup:** `{sim_co2_total:.2f} kg CO₂`")
sc2.markdown(f"**Net Greenhouse Gas Removed vs Traditional Grid:** `{net_savings:.2f} kg CO₂` 🎉")