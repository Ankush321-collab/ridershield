import exifread
from datetime import datetime
from typing import Optional, Tuple

def get_if_exist(data, key):
    if key in data:
        return data[key]
    return None

def convert_to_degrees(value):
    """Helper function to convert the GPS coordinates stored in the EXIF to degrees in float"""
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)
    return d + (m / 60.0) + (s / 3600.0)

def extract_exif_data(file_path: str) -> dict:
    """
    Extracts GPS and Timestamp from an image file.
    """
    data = {
        "lat": None,
        "lon": None,
        "timestamp": None
    }

    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f)

            # 1. Extract Timestamp
            dt_tag = get_if_exist(tags, 'EXIF DateTimeOriginal') or get_if_exist(tags, 'Image DateTime')
            if dt_tag:
                try:
                    # Format is usually YYYY:MM:DD HH:MM:SS
                    data["timestamp"] = datetime.strptime(str(dt_tag), '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    pass

            # 2. Extract GPS
            gps_lat = get_if_exist(tags, 'GPS GPSLatitude')
            gps_lat_ref = get_if_exist(tags, 'GPS GPSLatitudeRef')
            gps_lon = get_if_exist(tags, 'GPS GPSLongitude')
            gps_lon_ref = get_if_exist(tags, 'GPS GPSLongitudeRef')

            if gps_lat and gps_lat_ref and gps_lon and gps_lon_ref:
                lat = convert_to_degrees(gps_lat)
                if gps_lat_ref.values[0] != 'N':
                    lat = 0 - lat

                lon = convert_to_degrees(gps_lon)
                if gps_lon_ref.values[0] != 'E':
                    lon = 0 - lon

                data["lat"] = lat
                data["lon"] = lon
    except Exception:
        # Non-fatal: claims can proceed without EXIF metadata.
        return data

    return data
