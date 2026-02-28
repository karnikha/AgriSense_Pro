from flask import Flask, render_template, request
from plant_data import plants
import requests

app = Flask(__name__)

# 🌦 Weather API
API_KEY = "d0879ffd7785eae5ce18f42ba0bce48f"
CITY = "Erode"

# 📊 Data storage
water_history = []
moisture_history = []
days_history = []
total_water_used = 0
total_water_saved = 0
day_counter = 0

# 🚰 Pump capacity (Liters per minute)
PUMP_CAPACITY = 1000  

@app.route("/", methods=["GET", "POST"])
def home():
    global total_water_used, total_water_saved, day_counter
    global water_history, moisture_history, days_history

    decision = None
    reason = ""
    water_time = 0
    temperature = 35
    rain_forecast = False
    water_saved = 0

    # 🌦 Weather Fetch
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        data = response.json()

        if response.status_code == 200:
            temperature = data["main"]["temp"]
            weather_main = data["weather"][0]["main"]

            if weather_main in ["Rain", "Drizzle", "Thunderstorm"]:
                rain_forecast = True
    except:
        temperature = 35
        rain_forecast = False

    if request.method == "POST":

        day_counter += 1

        plant = request.form["plant"]
        stage = request.form["stage"]
        soil = int(request.form["soil"])
        acre = float(request.form["acre"])

        required_moisture = plants[plant]["moisture"]
        daily_mm = plants[plant]["daily_mm"]
        coverage = plants[plant]["coverage"]

        # 🌱 Growth stage multiplier
        stage_multiplier = {
            "Seed": 0.8,
            "Vegetative": 1.0,
            "Flowering": 1.2,
            "Harvest": 0.7
        }

        # 🌾 Convert Acre → Effective Area (with coverage factor)
        area_m2 = 4047 * acre * coverage

        # 💧 Smart irrigation liters calculation
        liters_required = daily_mm * area_m2
        liters_required *= stage_multiplier[stage]

        # 🌡 Temperature adjustment
        if temperature > 35:
            liters_required *= 1.1  # 10% extra

        # 🚰 Smart Decision Logic
        if soil < required_moisture and not rain_forecast:
            decision = "Pump ON"
            reason = "Low soil moisture & no rain forecast."

            water_time = liters_required / PUMP_CAPACITY
            total_water_used += liters_required

        else:
            decision = "Pump OFF"
            water_time = 0
            liters_required = 0
            reason = "Soil sufficient or rain expected."

        # 💧 Traditional Irrigation (Flooding Method Assumption)
        traditional_mm = 8  # typical flooding
        traditional_liters = traditional_mm * area_m2

        smart_liters = liters_required

        water_saved = max(traditional_liters - smart_liters, 0)
        total_water_saved += water_saved

        # 📊 Graph Data
        water_history.append(round(water_time, 2))
        moisture_history.append(soil)
        days_history.append(f"Day {day_counter}")

    return render_template(
        "index.html",
        plants=plants.keys(),
        decision=decision,
        reason=reason,
        water_time=round(water_time, 2),
        temperature=round(temperature, 2),
        rain_forecast=rain_forecast,
        water_history=water_history,
        moisture_history=moisture_history,
        days_history=days_history,
        total_water_used=round(total_water_used, 2),
        water_saved=round(water_saved, 2),
        total_water_saved=round(total_water_saved, 2)
    )

if __name__ == "__main__":
    app.run(debug=True)