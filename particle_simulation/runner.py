import pathlib
import itertools
import multiprocessing

from typing import Any
from particle_simulation import config

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
    create_incremental_outdir,
)


# TODO: Multiprocessing and the random seed might be a problem. If we use the time.time() as the seed,
# we might have the same seed for two different runs (in different computers). Also, given that in the same computer the seed
# is estimated as the random_seed + process_num, we might have the same seed for two different runs if they are close in time.
# (This is unlikely to happen as the time is in seconds and the simulations are long, but it is possible).


class SimRunner:
    def __init__(self, config_data: config.Config) -> None:
        # The configuration data
        self.config = config_data
        # Create the output directory
        self.save_dir = create_incremental_outdir(pathlib.Path(self.config.save_dir))
        # Update the save directory in the configuration
        self.config.save_dir = str(self.save_dir)
        # Save config in the output directory
        with open(self.save_dir / f"sim_config.json", "w") as f:
            f.write(self.config.model_dump_json(indent=4))
        # Get the number of processes
        self.num_processes = self.config.num_processes

    def run(self) -> None:
        # Run the simulation in parallel if the number of processes is greater than 1
        if self.num_processes == 1:
            self.simulation(1)
        else:
            list_processes = iter(range(1, self.num_processes + 1))
            with multiprocessing.Pool(self.num_processes) as pool:
                pool.map(self.simulation, list_processes)

    def simulation(self, process_num: int) -> int:
        # Create a logger
        logger = create_logger(
            "main",
            self.save_dir / f"running_{process_num}.log",
            self.config.logger_level,
        )
        logger.info(f"Running process: {process_num}/{self.num_processes}")

        # Set the random seed
        G4Random.getTheEngine().setSeed(process_num + self.config.random_seed, 0)
        logger.info(f"Random seed: {process_num + self.config.random_seed}")

        # Macro files
        macro_files = self.config.macro_files

        # Create an instance of the run manager
        runManager = G4RunManagerFactory.CreateRunManager(G4RunManagerType.Serial)

        # Load the geometry
        logger.info("Loading the geometry")
        runManager.SetUserInitialization(DetectorConstruction(self.config))
        # Physics list
        logger.info("Loading the physics list")
        # runManager.SetUserInitialization(MyPhysicsList())
        runManager.SetUserInitialization(QGSP_BERT_HP())
        # Run action
        logger.info("Loading the user action initialization")
        runManager.SetUserInitialization(ActionInitialization(self.config, process_num))

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

        return 0
