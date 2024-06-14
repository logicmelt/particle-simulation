import requests
import json
import pandas as pd
import itertools

def get_mag_field(lat: float, lon: float, alt: float, date: str) -> tuple:
    """
    Get the magnetic field at a given latitude, longitude and altitude

    Parameters
    ----------
    lat : float
        Latitude in degrees
    lon : float
        Longitude in degrees
    alt : float
        Altitude in kilometers
    date : str
        Date in the format YYYY-MM-DD

    Returns
    -------
    tuple
        Tuple with the magnetic field components (x, y, z)
    """
    url = f"https://geomag.bgs.ac.uk/web_service/GMModels/igrf/13/?latitude={lat}&longitude={lon}&altitude={alt}&date={date}&format=json"
    response = requests.get(url)
    data = json.loads(response.text)

    # There is a - sign in the vertical intensity because the z-axis is pointing down
    x, = data['geomagnetic-field-model-result']["field-value"]["north-intensity"]["value"], 
    y, = data['geomagnetic-field-model-result']["field-value"]["east-intensity"]["value"], 
    z = -data['geomagnetic-field-model-result']["field-value"]["vertical-intensity"]["value"]

    return x, y, z

def create_mag_file(lat: list[float], lon: list[float], alt: list[float], date: list[str], filename: str):
    """
    Create a magnetic field file based on the given latitude, longitude, and altitude values.

    Args:
        lat (list[float]): A list of latitude values.
        lon (list[float]): A list of longitude values.
        alt (list[float]): A list of altitude values.
        date (list[str]): A list of dates in the format YYYY-MM-DD.
        filename (str): The name of the file to save the magnetic field data.

    Returns:
        None
    """
    data = {"x": [], "y": [], "z": []}
    # We need to iterate over the lists of lat, lon and alt
    combinations = itertools.product(lat, lon, alt, date)
    for comb in combinations:
        x, y, z = get_mag_field(comb[0], comb[1], comb[2], comb[3])
        data["x"].append(x)
        data["y"].append(y)
        data["z"].append(z)
    # Create a DataFrame and save it to a CSV file
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)