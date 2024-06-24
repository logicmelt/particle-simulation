from geant4_pybind import G4UImanager, G4UIExecutive, G4RunManagerFactory, G4RunManagerType, G4VisExecutive, QGSP_BERT_HP
from particle_simulation.construction import DetectorConstruction
from particle_simulation.action import ActionInitialization
from particle_simulation.physics import MyPhysicsList
from particle_simulation.utils import create_logger
import logging
import yaml

def load_config(config_file: str):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config

def main():
    # Load the configuration file
    config = load_config("additional_files/simulation_config.yaml")

    # Create a logger
    logger = create_logger("main", config["save_dir"]+"running.log", logging.INFO)

    # Macro files
    macro_files = config["macro_files"]

    # Create an instance of the run manager
    runManager = G4RunManagerFactory.CreateRunManager(G4RunManagerType.Serial)

    # Load the geometry
    logger.info("Loading the geometry")
    runManager.SetUserInitialization(DetectorConstruction(config))
    # Physics list
    logger.info("Loading the physics list")
    #runManager.SetUserInitialization(MyPhysicsList())
    runManager.SetUserInitialization(QGSP_BERT_HP())
    # Run action
    logger.info("Loading the user action initialization")
    runManager.SetUserInitialization(ActionInitialization(config))

    # Initialize the run manager
    runManager.Initialize()

    ui = G4UIExecutive(1, ['vis.mac'])
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
    main()