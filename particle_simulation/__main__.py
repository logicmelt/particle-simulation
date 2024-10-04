from particle_simulation.runner import SimRunner
from particle_simulation.config import Config
from particle_simulation.utils import load_config
import argparse
import sys


def main(config_pyd: Config) -> None:
    """Main function to run the simulation."""
    # Create the simulation runner
    runner = SimRunner(config_pyd)
    # Run the simulation
    runner.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Particle simulation of a cosmic shower using Geant4 and Python."
    )
    parser.add_argument(
        "--config_file", type=str, help="Configuration yaml file", default=""
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
    main(config_parser)
