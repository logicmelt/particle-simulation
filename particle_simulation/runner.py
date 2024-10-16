import pathlib
import multiprocessing
import warnings
import pandas as pd

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
        self.save_dir = create_incremental_outdir(self.config.save_dir)
        # Update the save directory in the configuration
        self.config.save_dir = self.save_dir
        # Save config in the output directory
        with open(self.save_dir / f"sim_config.json", "w") as f:
            f.write(self.config.model_dump_json(indent=4))
        # Get the number of processes
        self.num_processes = self.config.num_processes
        # Create the header for the output file
        self.header = [
            "EventID",
            "TrackID",
            "process_ID",
            "Particle",
            "ParticleID",
            "px",
            "py",
            "pz",
            "x",
            "y",
            "z",
        ]
        self.new_header = {
            "x": "x[mm]",
            "y": "y[mm]",
            "z": "z[mm]",
            "px": "px[MeV]",
            "py": "py[MeV]",
            "pz": "pz[MeV]",
        }

    def run(self) -> pathlib.Path:
        """ Run the simulation.
        
        Returns:
            pathlib.Path: The path to the output file.
        """
        # Run the simulation in parallel if the number of processes is greater than 1
        if self.num_processes == 1:
            self.simulation(1)
        else:
            list_processes = iter(range(1, self.num_processes + 1))
            with multiprocessing.Pool(self.num_processes) as pool:
                pool.map(self.simulation, list_processes)

        # Now, we need to merge the output files into a single one
        output_files = [p for p in self.save_dir.rglob("*.csv")]
        if (
            len(output_files) == 0
        ):  # No files were generated so no particles reached the sensitive detectors
            warnings.warn("No particles were generated with the given configuration")
            return pathlib.Path("")

        data = pd.concat(
            [
                pd.read_csv(file_x, skiprows=15, names=self.header)
                for file_x in output_files
            ],
            ignore_index=True,
        )
        # Save the data as csv after sorting it by process_ID, EventID, and TrackID (Priority order)
        data.rename(self.new_header, axis="columns", inplace=True)
        data.sort_values(by=["process_ID", "EventID", "TrackID"], inplace=True)
        data.to_csv(self.save_dir / "output.csv", index=False)
        # Remove the individual files
        for file_x in output_files:
            file_x.unlink()

        return self.save_dir/"output.csv"

    def simulation(self, process_num: int) -> int:
        # Create a logger
        logger = create_logger(
            "main",
            self.save_dir / f"running_{process_num}.log",
            self.config.logger_level,
        )
        logger.info(f"Running process: {process_num}/{self.num_processes}")

        # Set the random seed. process_num starts at 1 so we need to subtract 1 to have
        # the original seed as the first one.
        G4Random.getTheEngine().setSeed(process_num - 1 + self.config.random_seed, 0)
        logger.info(f"Random seed: {process_num + self.config.random_seed}")

        # Macro files
        macro_files = self.config.macro_files

        # Create an instance of the run manager
        runManager = G4RunManagerFactory.CreateRunManager(G4RunManagerType.Serial)

        # Load the geometry
        logger.info("Loading the geometry")
        runManager.SetUserInitialization(DetectorConstruction(self.config, process_num))
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
        if isinstance(macro_files, pathlib.Path):
            logger.info(f"Applying the commands in the macro file: {macro_files}")
            uiManager.ApplyCommand(f"/control/execute {macro_files}")
        else:
            for macro in macro_files:
                logger.info(f"Applying the commands in the macro file: {macro}")
                uiManager.ApplyCommand(f"/control/execute {macro}")
        # Shoot the particles
        logger.info(f"Shooting {self.config.particles_per_run} particles")
        uiManager.ApplyCommand(f"/run/beamOn {self.config.particles_per_run}")
        uiManager.ApplyCommand("/vis/viewer/refresh")

        logger.info("Finished running the macro files")

        return 0
