from geant4_pybind import (
    G4UImanager,
    G4RunManagerFactory,
    G4RunManagerType,
    G4VisExecutive,
    QGSP_BERT_HP,
    G4Random,
)
from particle_simulation.construction import DetectorConstruction
from particle_simulation.action import ActionInitialization
from particle_simulation.utils import (
    create_logger,
    load_config,
    create_incremental_outdir,
)
import argparse, multiprocessing, datetime, pathlib, itertools


def main(config: dict, processNum: int = 1):
    save_dir = pathlib.Path(config["save_dir"])
    # Create a logger
    logger = create_logger(
        "main",
        save_dir / f"running_{processNum}.log",
        config.get("logger_level", "INFO"),
    )
    logger.info(f"Running process: {processNum}/{config.get('n_processes', 1)}")

    # Set the random seed
    random_seed = config.get("random_seed", datetime.datetime.now().timestamp())
    G4Random.getTheEngine().setSeed(int(processNum + random_seed), 0)
    logger.info(f"Random seed: {int(processNum + random_seed)}")

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
    runManager.SetUserInitialization(ActionInitialization(config, processNum))

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

    # Load the configuration file
    config = load_config(args.config_file)

    # Create the save directory if it does not exist
    save_dir = pathlib.Path(config["save_dir"])
    save_dir = create_incremental_outdir(save_dir)
    # Update the save directory in the configuration
    config["save_dir"] = save_dir

    # Get the number of processes
    n_processes = config.get("n_processes", 1)
    if n_processes == 1:
        main(config, n_processes)
    else:
        list_processes = list(range(1, n_processes + 1))
        # Zip the configuration with the process number
        params = zip(itertools.repeat(config), list_processes)
        with multiprocessing.Pool(n_processes) as pool:
            pool.starmap(main, params)
