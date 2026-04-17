"""
OpenWeatherMap client — polls real weather API every 5 minutes.
Falls back to realistic mock data if API key is absent / quota exceeded.
"""

import os
import httpx
import random
from datetime import datetime

OWM_API_KEY = os.getenv("OWM_API_KEY", "")   # set in .env to get real data
OWM_BASE = "https://api.openweathermap.org/data/2.5/weather"
OWM_AIR_POLLUTION_BASE = "https://api.openweathermap.org/data/2.5/air_pollution"


async def fetch_weather(zone: dict) -> dict:
    """Return weather snapshot for a zone. Uses real OWM if key present."""
    lat, lon = zone["lat"], zone["lon"]
    zone_id   = zone["id"]
    zone_name = zone["name"]

    if OWM_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(OWM_BASE, params={
                    "lat": lat, "lon": lon,
                    "appid": OWM_API_KEY,
                    "units": "metric",
                })
                if resp.status_code == 200:
                    data = resp.json()
                    rain_1h = data.get("rain", {}).get("1h", 0.0)
                    aqi = None
                    pm2_5 = None
                    pm10 = None
                    air_resp = await client.get(OWM_AIR_POLLUTION_BASE, params={
                        "lat": lat,
                        "lon": lon,
                        "appid": OWM_API_KEY,
                    })
                    if air_resp.status_code == 200:
                        air_data = air_resp.json()
                        air_list = air_data.get("list") or []
                        if air_list:
                            current_air = air_list[0]
                            owm_aqi = current_air.get("main", {}).get("aqi")
                            pm2_5 = current_air.get("components", {}).get("pm2_5")
                            pm10 = current_air.get("components", {}).get("pm10")
                            aqi = _map_owm_aqi_to_indian_proxy(owm_aqi)
                    return {
                        "zone_id":      zone_id,
                        "zone_name":    zone_name,
                        "temperature":  data["main"]["temp"],
                        "rainfall_mm":  rain_1h,
                        "humidity":     data["main"]["humidity"],
                        "wind_speed":   data["wind"]["speed"] * 3.6,   # m/s → km/h
                        "aqi":          aqi,
                        "pm2_5":        pm2_5,
                        "pm10":         pm10,
                        "heat_index":   _heat_index(data["main"]["temp"], data["main"]["humidity"]),
                        "source":       "openweathermap_live",
                        "time":         datetime.utcnow(),
                    }
        except Exception as exc:
            print(f"[WeatherClient] OWM fetch failed for {zone_name}: {exc}. Using mock.")

    # ── Mock fallback ────────────────────────────────────────────────────────
    return _mock_weather(zone_id, zone_name)


def _mock_weather(zone_id: str, zone_name: str) -> dict:
    """Statistically realistic mock weather — NOT fully random."""
    hour = datetime.utcnow().hour
    # Evening / monsoon simulation: higher rain between 14-20 UTC (≈ 19-01 IST)
    rain_base = 5.0 if 14 <= hour <= 20 else 1.0
    rain_mm   = max(0.0, random.gauss(rain_base, 8.0))

    temp      = round(random.gauss(28, 4), 1)
    humidity  = random.randint(50, 90)
    wind_kmh  = max(0.0, round(random.gauss(15, 10), 1))
    aqi       = _mock_aqi()

    return {
        "zone_id":      zone_id,
        "zone_name":    zone_name,
        "temperature":  temp,
        "rainfall_mm":  round(rain_mm, 2),
        "humidity":     humidity,
        "wind_speed":   wind_kmh,
        "aqi":          aqi,
        "heat_index":   _heat_index(temp, humidity),
        "source":       "mock",
        "time":         datetime.utcnow(),
    }


def _map_owm_aqi_to_indian_proxy(owm_aqi: int | None) -> int | None:
    if owm_aqi is None:
        return None
    return min(500, max(0, int(owm_aqi) * 60))


def _mock_aqi() -> int:
    # Keep AQI usually moderate but allow occasional GRAP stage 3/4 demo values.
    if random.random() < 0.15:
        return random.randint(301, 450)
    return random.randint(50, 220)


def _heat_index(temp_c: float, humidity: int) -> float:
    """Simplified heat index (Rothfusz approximation, metric)."""
    T = temp_c * 9 / 5 + 32   # °C → °F for formula
    RH = humidity
    HI = (-42.379
          + 2.04901523 * T
          + 10.14333127 * RH
          - 0.22475541 * T * RH
          - 0.00683783 * T ** 2
          - 0.05481717 * RH ** 2
          + 0.00122874 * T ** 2 * RH
          + 0.00085282 * T * RH ** 2
          - 0.00000199 * T ** 2 * RH ** 2)
    return round((HI - 32) * 5 / 9, 1)   # back to °C
