from particle_simulation.runner import SimRunner
from particle_simulation.config import Config
from particle_simulation.utils import load_config
import argparse
import sys
import pathlib
import pandas as pd
import matplotlib.pyplot as plt
import shutil


def postprocess(output_paths: list[pathlib.Path]) -> list[int]:
    """
    Postprocess the output files and generate the timeseries of muons reaching the ground.
    Args:
        output_paths (list[pathlib.Path]): List of paths to the output files.
    Returns:
        list[int]: List of muons reaching the ground per second.
    """
    muon_count: list[int] = []
    # Each file corresponds to 1s of simulation
    for path in output_paths:
        # Check if the file exists
        if path.is_file() == False:
            # If that is the case then no muons were generated
            muon_count.append(0)
            continue
        dataframe = pd.read_csv(path)
        # Get the number of muons
        num_muons = len(dataframe[dataframe["Particle"] == "mu-"])
        muon_count.append(num_muons)

    return muon_count


def main(config_pyd: Config, sim_cycles: int, time_resolution: int) -> None:
    """Main function to run the simulation.

    Args:
        config_pyd (Config): Configuration settings.
        sim_cycles (int): Number of times the simulation should be run. Set -1 for continuous simulation.
        time_resolution (int): Time resolution of the simulation in seconds.
    """
    # Get the current save directory for later use
    current_save_dir = config_pyd.save_dir

    # Check if there is a restart file
    if (current_save_dir / "last_config.json").is_file():
        print("Restart file found.")
        # Load the configuration file
        config_pyd = Config(**load_config(current_save_dir / "last_config.json"))

    # List to store the path to the output files
    output_paths: list[pathlib.Path] = []

    # If sim_cycles is -1, the simulation will run continuously
    # Simulation is ran as many times as specified in sim_cycles
    try:
        print("Running simulation...")
        while sim_cycles != 0:
            # Create the simulation runner
            runner = SimRunner(config_pyd)
            # Run the simulation
            file_path = runner.run()
            output_paths.append(file_path)
            # Update the save directory in the configuration (Otherwise the new sim will be run in the same directory)
            config_pyd.save_dir = current_save_dir
            # Update the random seed to get different results
            config_pyd.random_seed += config_pyd.num_processes + 10
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
    muon_time = postprocess(output_paths)
    # Plot the timeseries
    plt.plot(muon_time)
    plt.show()


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
        "--time_resolution",
        type=int,
        help="Time resolution of the simulation in seconds",
        default=1,
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
    main(config_parser, args.sim_cycles, args.time_resolution)
