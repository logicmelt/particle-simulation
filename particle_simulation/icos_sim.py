from typing import Any
import argparse
import sys
import pathlib
import shutil
import datetime
import json
from uuid import uuid4

import pandas as pd
from environs import env
from influxdb_client import InfluxDBClient  # type: ignore
from influxdb_client.client.write_api import SYNCHRONOUS

from particle_simulation.runner import SimRunner
from particle_simulation.config import Config
from particle_simulation.utils import load_config, extract_latitude_longitude
from particle_simulation.results import ResultsIcos, ResultsInflux


def postprocess(
    output_paths: list[pathlib.Path],
    output_extra: list[
        tuple[datetime.datetime, datetime.datetime, float, float, int, Any]
    ],
    output_dir: pathlib.Path,
    run_id: list[str],
) -> list[ResultsIcos | ResultsInflux]:
    """
    Postprocess the output files and generate the timeseries of muons reaching the ground.
    Args:
        output_paths (list[pathlib.Path]): List of paths to the output files.
        output_extra (list[tuple[datetime.datetime, datetime.datetime, float, float, int, Any]]): List of tuples with the start_time, end_time,
                    latitude, longitude, density profile day idx and density profile of each simulation.
        output_dir (pathlib.Path): Directory where the output files are saved.
        run_id (list[str]): Identifier for the run, used to name the output files.
    Returns:
        list[ResultsIcos | ResultsInflux]: List of muons reaching the ground per second.
    """
    muon_count: list[ResultsIcos | ResultsInflux] = []
    # Each file corresponds to 1s of simulation
    for idx, path in enumerate(output_paths):
        output_file_path = output_dir / f"icos_output_{run_id[idx]}.json"
        if not path.is_file():
            parsed_results = ResultsIcos.model_validate(
                (pd.DataFrame(), output_extra[idx])
            )
            muon_count.append(parsed_results)
            with open(output_file_path, "w") as f:
                f.write(parsed_results.model_dump_json(indent=4))
            continue
        dataframe = pd.read_csv(path)
        parsed_results = ResultsIcos.model_validate((dataframe, output_extra[idx]))
        # Save the output file in the output directory
        with open(output_file_path, "w") as f:
            f.write(parsed_results.model_dump_json(indent=4))
        muon_count.append(parsed_results)
    return muon_count


def main(
    config_pyd: Config,
    sim_cycles: int,
    restart_checkpoint: bool = True,
) -> None:
    """Main function to run the simulation.

    Args:
        config_pyd (Config): Configuration settings.
        sim_cycles (int): Number of times the simulation should be run. Set -1 for continuous simulation.
        restart_checkpoint (bool, optional): Restart the simulation from the last configuration file. Defaults to True.
    """
    # Read environment
    env.read_env()

    # Get the current save directory for later use
    current_save_dir = config_pyd.save_dir

    # Check if there is a restart file
    if (current_save_dir / "last_config.json").is_file() and restart_checkpoint:
        print("Restart file found.")
        # Load the configuration file
        config_pyd = Config(**load_config(current_save_dir / "last_config.json"))

    # Create the output directory
    if not (current_save_dir / "output_jsons").exists():
        (current_save_dir / "output_jsons").mkdir(parents=True, exist_ok=True)
    output_dir = current_save_dir / "output_jsons"

    # The longitude and latitude can be provided in the configuration file or in a separate file
    if config_pyd.constructor.magnetic_field.mag_source == "file":
        latitude, longitude, date_mag = extract_latitude_longitude(
            config_pyd.constructor.magnetic_field.mag_file
        )
        start_time = date_mag
        config_pyd.constructor.magnetic_field.mag_time = start_time
        config_pyd.constructor.magnetic_field.latitude = latitude
        config_pyd.constructor.magnetic_field.longitude = longitude
    else:
        longitude = config_pyd.constructor.magnetic_field.longitude
        latitude = config_pyd.constructor.magnetic_field.latitude
        start_time = config_pyd.constructor.magnetic_field.mag_time

    # Open density profile file to store the Temperature, density and altitude used in the simulation
    with open(config_pyd.constructor.density_profile.density_file, "r") as f:
        density_profile = json.load(f)
    # List to store the path to the output files
    output_paths: list[pathlib.Path] = []
    # List to store the start_time, end_time, latitude and longitude of each simulation
    output_extra: list[
        tuple[datetime.datetime, datetime.datetime, float, float, int, dict[str, Any]]
    ] = []
    # Save the run_id to identify the output files
    run_id: list[str] = []
    # If sim_cycles is -1, the simulation will run continuously
    # Simulation is ran as many times as specified in sim_cycles

    influx_client_write_api = None
    if env.bool("INFLUX_ENABLED", default=False):
        influx_client = InfluxDBClient(
            url=f"http://{env.str("INFLUX_HOST")}:{env.str("INFLUX_PORT")}",
            token=env.str("INFLUX_TOKEN"),
            org=env.str("INFLUX_ORG"),
        )
        influx_client_write_api = influx_client.write_api(write_options=SYNCHRONOUS)

    detector_id = env.str("DETECTOR_ID", default=f"simulator-{uuid4()}")

    try:
        print(f"Running simulation - Detector Id: {detector_id}")
        while sim_cycles != 0:
            t_start = datetime.datetime.now()
            print(f"Starting simulation {abs(sim_cycles)} @ {t_start.isoformat()}")
            config_pyd.constructor.magnetic_field.mag_time = t_start
            config_pyd.constructor.density_profile.day_idx = (
                t_start.timetuple().tm_yday
            ) % 100

            # Create the simulation runner
            runner = SimRunner(config_pyd)
            run_id.append(str(runner.save_dir.name))
            # Run the simulation
            file_path, dataframe = runner.run()
            output_paths.append(file_path)

            # Send particle data to influx if enabled
            if influx_client_write_api:
                print("Publishing results to Influx")
                influx_df = dataframe.set_index("timestamp")
                # Add detector_id to the dataframe before writing to InfluxDB
                influx_df["detector_id"] = detector_id
                influx_client_write_api.write(
                    bucket=env.str("INFLUX_BUCKET"),
                    record=influx_df,
                    data_frame_measurement_name="particle",
                    write_precision="us",  # type: ignore
                    data_frame_tag_columns=["run_ID", "detector_type", "detector_id"],
                )

            # End time will be the current start time plus time_resolution microseconds
            end_time = (
                config_pyd.constructor.magnetic_field.mag_time
                + datetime.timedelta(microseconds=config_pyd.time_resolution)
            )
            # Append to the output_extra list
            output_extra.append(
                (
                    config_pyd.constructor.magnetic_field.mag_time,
                    end_time,
                    latitude,
                    longitude,
                    config_pyd.constructor.density_profile.day_idx,
                    density_profile[
                        str(config_pyd.constructor.density_profile.day_idx)
                    ],
                )
            )

            # Update the save directory in the configuration (Otherwise the new sim will be run in the same directory)
            config_pyd.save_dir = current_save_dir
            # Update the random seed to get different results
            config_pyd.random_seed += config_pyd.num_processes + 10

            # Postprocess the output files to get the timeseries of muons and save the results
            postprocess(output_paths, output_extra, output_dir, run_id)
            output_paths, output_extra, run_id = (
                [],
                [],
                [],
            )  # Reset the output paths and extra data for the next cycle
            t_end = datetime.datetime.now()
            print(
                f"Simulation {abs(sim_cycles)} completed @ {t_end.isoformat()} - Duration: {(t_end - t_start).total_seconds()} s"
            )
            sim_cycles -= 1
    except KeyboardInterrupt:
        print("Simulation interrupted by the user.")
        print("Writing restart file...")
        # Get the last folder created
        last_folder = max(current_save_dir.iterdir(), key=lambda x: x.stat().st_ctime)
        # Save the current state of the simulation
        config_pyd.save_dir = current_save_dir
        with open(current_save_dir / "last_config.json", "w") as f:
            f.write(config_pyd.model_dump_json(indent=4))
        # Remove the unfinished simulation (The last folder created is the one that was not finished)
        if len(output_paths) == 0:
            print("No output files were generated.")
            # Delete everything in the folder
            shutil.rmtree(current_save_dir / last_folder.name)
            return
        # Delete everything in the last folder
        shutil.rmtree(current_save_dir / last_folder.name)


def cli_entrypoint() -> None:
    parser = argparse.ArgumentParser(
        description="Particle simulation of a cosmic shower using Geant4 and Python."
    )
    parser.add_argument(
        "--config_file", type=str, help="Configuration yaml file", default=""
    )
    parser.add_argument(
        "--sim_cycles",
        type=int,
        help="Times the simulation should be run. Defaults to -1 (Continuous)",
        default=-1,
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart the simulation from the last configuration file.",
    )
    # Parse command line arguments and the unknown arguments
    args, unknown = parser.parse_known_args()
    # Remove --config_file from the list of arguments
    sys.argv = [sys.argv[0]] + unknown
    # Parse the configuration file (and overwrite the default values) if it is provided or use the input arguments + default values.
    if len(args.config_file) == 0:
        # No config file, use default and CLI arguments
        config_parser = Config.model_validate(
            {}
        )  # Workaround because type checkers cannot see the CLI arguments
    else:
        # Load the configuration file and overwrite the default values
        config_parser = Config(**load_config(args.config_file))
    # Call the main function
    main(config_parser, args.sim_cycles, args.restart)


if __name__ == "__main__":
    cli_entrypoint()
