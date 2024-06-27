from geant4_pybind import (
    G4UImanager,
    G4RunManagerFactory,
    G4RunManagerType,
    G4VisExecutive,
    QGSP_BERT_HP,
)
from particle_simulation.construction import DetectorConstruction
from particle_simulation.action import ActionInitialization
from particle_simulation.utils import create_logger, load_config
import argparse


def main(config_file: str):
    # Load the configuration file
    config = load_config(config_file)

    # Create a logger
    logger = create_logger(
        "main", config["save_dir"] + "running.log", config.get("logger_level", "INFO")
    )

    # Macro files
    macro_files = config["macro_files"]

    # Create an instance of the run manager
    runManager = G4RunManagerFactory.CreateRunManager(G4RunManagerType.Serial)

    # Load the geometry
    logger.info("Loading the geometry")
    runManager.SetUserInitialization(DetectorConstruction(config))
    # Physics list
    logger.info("Loading the physics list")
    # runManager.SetUserInitialization(MyPhysicsList())
    runManager.SetUserInitialization(QGSP_BERT_HP())
    # Run action
    logger.info("Loading the user action initialization")
    runManager.SetUserInitialization(ActionInitialization(config))

    # Initialize the run manager
    runManager.Initialize()

    visManager = G4VisExecutive()
    visManager.Initialize()
    # Create an instance of the UI manager
    uiManager = G4UImanager.GetUIpointer()

    # Apply the commands in the macro file
    logger.info(f"Running the macro files")
    if isinstance(macro_files, str):
        logger.info(f"Applying the commands in the macro file: {macro_files}")
        uiManager.ApplyCommand(f"/control/execute {macro_files}")
    else:
        for macro in macro_files:
            logger.info(f"Applying the commands in the macro file: {macro}")
            uiManager.ApplyCommand(f"/control/execute {macro}")
    logger.info("Finished running the macro files")


if __name__ == "__main__":
    # Get the configuration file from the command line
    parser = argparse.ArgumentParser(
        description="Particle simulation of a cosmic shower using Geant4 and Python."
    )
    parser.add_argument("config_file", type=str, help="Configuration yaml file")
    args = parser.parse_args()
    # Run the main function
    main(args.config_file)
