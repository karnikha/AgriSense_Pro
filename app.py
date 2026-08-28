from flask import Flask, render_template, request, session
from plant_data import plants
import requests

app = Flask(__name__)
app.secret_key = "agrisense_secret_key"

API_KEY = "d0879ffd7785eae5ce18f42ba0bce48f"

# Tamil Nadu District Coordinates
district_coordinates = {
    "Ariyalur": (11.1401, 79.0786),
    "Chengalpattu": (12.6916, 79.9787),
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Cuddalore": (11.7447, 79.7680),
    "Dharmapuri": (12.1211, 78.1582),
    "Dindigul": (10.3673, 77.9803),
    "Erode": (11.3410, 77.7172),
    "Kallakurichi": (11.7380, 78.9630),
    "Kanchipuram": (12.8342, 79.7036),
    "Kanyakumari": (8.0883, 77.5385),
    "Karur": (10.9601, 78.0766),
    "Krishnagiri": (12.5266, 78.2140),
    "Madurai": (9.9252, 78.1198),
    "Mayiladuthurai": (11.1035, 79.6550),
    "Nagapattinam": (10.7656, 79.8428),
    "Namakkal": (11.2194, 78.1674),
    "Nilgiris": (11.4064, 76.6932),
    "Perambalur": (11.2333, 78.8833),
    "Pudukkottai": (10.3797, 78.8208),
    "Ramanathapuram": (9.3716, 78.8301),
    "Ranipet": (12.9246, 79.3335),
    "Salem": (11.6643, 78.1460),
    "Sivaganga": (9.8472, 78.4800),
    "Tenkasi": (8.9590, 77.3152),
    "Thanjavur": (10.7867, 79.1378),
    "Theni": (10.0104, 77.4768),
    "Thoothukudi": (8.7642, 78.1348),
    "Tiruchirappalli": (10.7905, 78.7047),
    "Tirunelveli": (8.7139, 77.7567),
    "Tirupathur": (12.4956, 78.5670),
    "Tiruppur": (11.1085, 77.3411),
    "Tiruvallur": (13.1436, 79.9089),
    "Tiruvannamalai": (12.2253, 79.0747),
    "Tiruvarur": (10.7720, 79.6368),
    "Vellore": (12.9165, 79.1325),
    "Viluppuram": (11.9338, 79.4886),
    "Virudhunagar": (9.5680, 77.9624)
}

PUMP_CAPACITY = 1000  # liters per minute


@app.route("/", methods=["GET", "POST"])
def home():

    # 🔹 FIRST TIME SESSION INITIALIZATION
    if "initialized" not in session:
        session["water_history"] = []
        session["moisture_history"] = []
        session["days_history"] = []
        session["total_water_used"] = 0
        session["total_water_saved"] = 0
        session["day_counter"] = 0
        session["initialized"] = True

    decision = None
    reason = ""
    water_time = 0
    irrigation_display = ""
    temperature = 30
    rain_forecast = False
    rain_display = "No Rain Expected"
    water_saved = 0
    water_saved_percent = 0

    if request.method == "POST":

        city = request.form["city"]
        plant = request.form["plant"]
        stage = request.form["stage"]
        soil = int(request.form["soil"])
        acre = float(request.form["acre"])

        # WEATHER
        try:
            lat, lon = district_coordinates[city]
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                temperature = data["main"]["temp"]
                weather_main = data["weather"][0]["main"]

                if weather_main in ["Rain", "Drizzle", "Thunderstorm"]:
                    rain_forecast = True
                    rain_display = "Rain Expected (Irrigation Delayed)"
                else:
                    rain_display = "No Rain Expected"

        except:
            rain_display = "Weather Data Unavailable"

        # PLANT DATA
        required_moisture = plants[plant]["moisture"]
        daily_mm = plants[plant]["daily_mm"]
        coverage = plants[plant]["coverage"]

        stage_multiplier = {
            "Seed": 0.8,
            "Vegetative": 1.0,
            "Flowering": 1.2,
            "Harvest": 0.7
        }

        area_m2 = 4047 * acre * coverage
        liters_required = daily_mm * area_m2
        liters_required *= stage_multiplier[stage]

        if temperature > 35:
            liters_required *= 1.1

        # DECISION LOGIC
        if soil < required_moisture and not rain_forecast:
            decision = "Pump ON"
            reason = "Low soil moisture & no rain forecast."
            water_time = liters_required / PUMP_CAPACITY

            # Only update totals if pump ON
            session["total_water_used"] += liters_required
            session["day_counter"] += 1

            session["water_history"].append(round(water_time, 2))
            session["moisture_history"].append(soil)
            session["days_history"].append(f"Day {session['day_counter']}")

        else:
            decision = "Pump OFF"
            reason = "Soil sufficient or rain expected."
            water_time = 0
            liters_required = 0

        # DISPLAY TIME
        if acre > 0 and water_time > 60:
            irrigation_display = f"{round(water_time/acre,2)} minutes per acre"
        else:
            irrigation_display = f"{round(water_time,2)} minutes"

        # WATER SAVING
        traditional_mm = 8
        traditional_liters = traditional_mm * area_m2

        water_saved = max(traditional_liters - liters_required, 0)

        if water_time > 0:
            session["total_water_saved"] += water_saved

        if traditional_liters > 0:
            percent = (water_saved / traditional_liters) * 100
            water_saved_percent = round(min(max(percent, 0), 100), 2)
        else:
            water_saved_percent = 0

    # Convert to KL
    total_water_used_kl = round(session["total_water_used"] / 1000, 2)
    total_water_saved_kl = round(session["total_water_saved"] / 1000, 2)
    water_saved_kl = round(water_saved / 1000, 2)

    return render_template(
        "index.html",
        plants=plants.keys(),
        districts=district_coordinates.keys(),
        decision=decision,
        reason=reason,
        irrigation_display=irrigation_display,
        temperature=round(temperature, 2),
        rain_display=rain_display,
        water_history=session["water_history"],
        moisture_history=session["moisture_history"],
        days_history=session["days_history"],
        total_water_used=total_water_used_kl,
        water_saved=water_saved_kl,
        total_water_saved=total_water_saved_kl,
        water_saved_percent=water_saved_percent
    )


if __name__ == "__main__":
    app.run(debug=True)