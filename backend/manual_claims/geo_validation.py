"""
Dev 5: Geo-Validation + Spam Detection utilities

These are imported by manual_claims/router.py during claim processing.
"""

from math import radians, sin, cos, sqrt, atan2


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance in meters between two GPS coordinates.
    """
    R = 6371000  # Earth radius in meters
    if any(v is None for v in [lat1, lon1, lat2, lon2]):
        return 9999999.0
        
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)

    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def calculate_spam_score(
    gps_distance_m: float,
    time_delta_min: float,
    disruption_type: str,
    weather_match: bool = False,
    traffic_match: bool = False,
    exif_gps_available: bool = True,
    exif_timestamp_available: bool = True,
) -> int:
    """
    Calculate composite spam score (0-100).
    
    Weights:
    - Location mismatch (>500m): 35%
    - Time anomaly (>30 min): 25%
    - Weather/Traffic mismatch (Dev 3 corroboration): 40%
    
    Auto-reject if score >= 70.
    """
    score = 0

    # 1. Location mismatch (35% weight)
    # Web uploads often lack EXIF GPS entirely, which should flag for review,
    # not auto-reject a legitimate claim by itself.
    if exif_gps_available:
        if gps_distance_m > 500:
            score += 35
    else:
        score += 10

    # 2. Time anomaly (25% weight)
    if exif_timestamp_available:
        if time_delta_min > 30:
            score += 25
    else:
        score += 10

    # 3. Weather/Traffic match (40% weight total)
    confirmed = False
    if disruption_type == "weather" and weather_match:
        confirmed = True
    elif disruption_type == "traffic" and traffic_match:
        confirmed = True
    elif disruption_type not in ["weather", "traffic"] and (weather_match or traffic_match):
        confirmed = True
        
    if not confirmed:
        score += 40

    return min(score, 100)


def explain_spam_rejection(
    gps_distance_m: float | None,
    time_delta_min: float,
    disruption_type: str,
    weather_match: bool = False,
    traffic_match: bool = False,
) -> list[str]:
    """
    Return human-readable reasons that contributed to a high spam score.
    """
    reasons: list[str] = []

    if gps_distance_m is not None and gps_distance_m > 500:
        reasons.append(f"Photo GPS is {int(gps_distance_m)}m away from the reported incident location.")

    if time_delta_min > 30:
        if time_delta_min >= 900:
            reasons.append("Photo metadata is missing or unusable, so the capture time could not be verified.")
        else:
            reasons.append(f"Photo capture time differs from the reported incident time by {int(time_delta_min)} minutes.")

    confirmed = False
    if disruption_type == "weather" and weather_match:
        confirmed = True
    elif disruption_type == "traffic" and traffic_match:
        confirmed = True
    elif disruption_type not in ["weather", "traffic"] and (weather_match or traffic_match):
        confirmed = True

    if not confirmed:
        if disruption_type == "weather":
            reasons.append("Historical weather data did not confirm the reported weather disruption.")
        elif disruption_type == "traffic":
            reasons.append("Traffic data did not confirm unusual congestion for the reported incident.")
        else:
            reasons.append("Independent validation signals did not corroborate the reported disruption.")

    return reasons
