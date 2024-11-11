from particle_simulation.runner import SimRunner
from particle_simulation.config import Config
from particle_simulation.utils import load_config, extract_latitude_longitude
from particle_simulation.results import ResultsIcos
from pydantic_settings import CliSettingsSource
import argparse
import sys
import pathlib
import pandas as pd
import shutil
import datetime

#TODO: Add support to no particles reaching the ground. Right now this situation is skipped 
# but it should add a 0 to the muon_time list as it is a valid result.

def postprocess(
    output_paths: list[pathlib.Path],
    output_extra: list[tuple[datetime.datetime, datetime.datetime, float, float]],
) -> list[int]:
    """
    Postprocess the output files and generate the timeseries of muons reaching the ground.
    Args:
        output_paths (list[pathlib.Path]): List of paths to the output files.
        output_extra (list[tuple[datetime.datetime, datetime.datetime, float, float]]): List of tuples with the start_time, end_time,
                    latitude and longitude of each simulation.
    Returns:
        list[int]: List of muons reaching the ground per second.
    """
    muon_count: list[int] = []
    # Each file corresponds to 1s of simulation
    for idx, path in enumerate(output_paths):
        dataframe = pd.read_csv(path)
        parsed_results = ResultsIcos.model_validate((dataframe, output_extra[idx]))

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
    # Get the current save directory for later use
    current_save_dir = config_pyd.save_dir

    # Check if there is a restart file
    if (current_save_dir / "last_config.json").is_file() and restart_checkpoint:
        print("Restart file found.")
        # Load the configuration file
        config_pyd = Config(**load_config(current_save_dir / "last_config.json"))

    # The longitude and latitude can be provided in the configuration file or in a separate file
    if config_pyd.constructor.magnetic_field.mag_source == "file":
        latitude, longitude = extract_latitude_longitude(
            config_pyd.constructor.magnetic_field.mag_file
        )
    else:
        longitude = config_pyd.constructor.magnetic_field.longitude
        latitude = config_pyd.constructor.magnetic_field.latitude

    # List to store the path to the output files
    output_paths: list[pathlib.Path] = []
    # List to store the start_time, end_time, latitude and longitude of each simulation
    output_extra: list[tuple[datetime.datetime, datetime.datetime, float, float]] = []
    # If sim_cycles is -1, the simulation will run continuously
    # Simulation is ran as many times as specified in sim_cycles
    try:
        print("Running simulation...")
        while sim_cycles != 0:
            if sim_cycles % 10 == 0:
                print(f"Starting simulation: {sim_cycles}")
            # Create the simulation runner
            runner = SimRunner(config_pyd)
            # Run the simulation
            file_path = runner.run()
            if not file_path.is_file():
                # No particles reached the sensitive detectors for this simulation. That means no csv filee
                config_pyd.random_seed += config_pyd.num_processes + 10
                config_pyd.save_dir = current_save_dir
                # Update the time to the new start time
                config_pyd.constructor.magnetic_field.mag_time += datetime.timedelta(
                    seconds=1
                )
                sim_cycles -= 1
                continue
            output_paths.append(file_path)
            # End time will be the current start time plus one second
            end_time = (
                config_pyd.constructor.magnetic_field.mag_time
                + datetime.timedelta(seconds=1)
            )
            # Append to the output_extra list
            output_extra.append(
                (
                    config_pyd.constructor.magnetic_field.mag_time,
                    end_time,
                    latitude,
                    longitude,
                )
            )
            # Update the save directory in the configuration (Otherwise the new sim will be run in the same directory)
            config_pyd.save_dir = current_save_dir
            # Update the random seed to get different results
            config_pyd.random_seed += config_pyd.num_processes + 10
            # Update the time to the new start time
            config_pyd.constructor.magnetic_field.mag_time = end_time
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
    # Postprocess the output files to get the timeseries of muons
    muon_time = postprocess(output_paths, output_extra)


if __name__ == "__main__":
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
        default=True,
        help="Restart the simulation from the last configuration file.",
    )

    # Connect the CliSettingsSource to the argparser so that the --help message is generated correctly.
    cli_settings = CliSettingsSource(Config, root_parser=parser)

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
