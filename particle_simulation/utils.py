import requests
import json
import pandas as pd
import itertools
import logging
import yaml
import pathlib
import os
import re
from typing import Any

LOGGER_LEVEL: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def load_config(config_file: str) -> dict[str, Any]:
    """Loads a configuration file in YAML or JSON format.

    Args:
        config_file (str): The path to the configuration file.

    Returns:
        dict[str, Any]: The configuration file read as a dictionary.
    """
    file_extension = pathlib.Path(config_file).suffix
    if file_extension == ".json":
        with open(config_file, "r") as f:
            config = json.load(f)
    elif file_extension == ".yaml":
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    else:
        raise ValueError("The configuration file must be in JSON or YAML format.")
    return config


def create_logger(
    name: str, log_file: str | pathlib.Path, level: str = "INFO"
) -> logging.Logger:
    """
    Create a logger with the given name and log file.

    Args:
        name (str): The name of the logger.
        log_file (str | pathlib.Path): Path to the log file.
        level (str): The logging level ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]. Defaults to "INFO".

    Returns:
        logging.Logger: The logger instance.
    """
    # Get the logging level
    level_log = LOGGER_LEVEL[level]
    # Create the logger and set it to the desired level
    logger = logging.getLogger(name)
    logger.setLevel(level_log)
    # Output file and log format
    FORMAT = logging.Formatter(
        "%(asctime)s - %(filename)s->%(funcName)s():%(lineno)s - [%(levelname)s] - %(message)s"
    )
    file_handler = logging.FileHandler(log_file, mode="w", encoding=None, delay=False)
    file_handler.setFormatter(FORMAT)
    logger.addHandler(file_handler)
    # Return the logger
    return logger


def get_mag_field(lat: float, lon: float, alt: float, date: str) -> tuple[float, ...]:
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
    tuple[float, ...]
        Tuple with the magnetic field components (x, y, z)
    """
    url = f"https://geomag.bgs.ac.uk/web_service/GMModels/igrf/13/?latitude={lat}&longitude={lon}&altitude={alt}&date={date}&format=json"
    response = requests.get(url)
    data = json.loads(response.text)

    # There is a - sign in the vertical intensity because the z-axis is pointing down
    (x,) = (
        data["geomagnetic-field-model-result"]["field-value"]["north-intensity"][
            "value"
        ],
    )
    (y,) = (
        data["geomagnetic-field-model-result"]["field-value"]["east-intensity"][
            "value"
        ],
    )
    z = -data["geomagnetic-field-model-result"]["field-value"]["vertical-intensity"][
        "value"
    ]

    return x, y, z


def create_mag_file(
    lat: list[float], lon: list[float], alt: list[float], date: list[str], filename: str
):
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
    data = {
        "x": [],
        "y": [],
        "z": [],
        "altitude": [],
        "latitude": [],
        "longitude": [],
        "date": [],
    }
    # We need to iterate over the lists of lat, lon and alt
    combinations = itertools.product(lat, lon, alt, date)
    for comb in combinations:
        x, y, z = get_mag_field(comb[0], comb[1], comb[2], comb[3])
        data["x"].append(x)
        data["y"].append(y)
        data["z"].append(z)
        data["latitude"].append(comb[0])
        data["longitude"].append(comb[1])
        data["altitude"].append(comb[2])
        data["date"].append(comb[3])
    # Create a DataFrame and save it to a CSV file
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)


def create_incremental_outdir(
    outdir: pathlib.Path, structure: str = ""
) -> pathlib.Path:
    """Creates a folder and increases the number by 1. Used to create folders for different runs.

    Args:
        outdir (pathlib.Path): Output path
        structure (str, optional): Structure that the folders should follow, it will be added a number. Defaults to ''.

    Returns:
        new_outdir (pathlib.Path): New output dir
    """
    create_outdir(outdir)
    # Get all folders that match the structure string
    folders = [f for f in os.listdir(outdir) if re.match(rf"{structure}\d+", f)]
    if len(folders) == 0:
        create_outdir(outdir / f"{structure}1")
        new_outdir = outdir / f"{structure}1"
        return new_outdir
    if structure == "":
        numbers = [int(f) for f in folders]
    else:
        numbers = [int(f.split(structure)[-1]) for f in folders]
    create_outdir(outdir / f"{structure}{max(numbers)+1}")
    new_outdir = outdir / f"{structure}{max(numbers)+1}"
    return new_outdir


def create_outdir(outdir: pathlib.Path):
    """Creates a folder if it doesn't exist

    Args:
        outdir (pathlib.Path): Path to folder
    """
    if not outdir.exists():
        outdir.mkdir(parents=True)
    return outdir
