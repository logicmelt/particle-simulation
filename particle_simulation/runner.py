import pathlib
import multiprocessing
import warnings
import pandas as pd
import contextlib
import uuid
import numpy as np

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
        # assert self.num_processes > 1, "The number of processes must be greater than 1 or geant4 will crash due to"
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
            "theta[rad]",
            "phi[rad]",
            "time[s]",
            "local_time[s]",
        ]
        self.new_header = {
            "x": "x[mm]",
            "y": "y[mm]",
            "z": "z[mm]",
            "px": "px[MeV]",
            "py": "py[MeV]",
            "pz": "pz[MeV]",
        }

    def run(self) -> tuple[pathlib.Path, pd.DataFrame]:
        """Run the simulation.

        Returns:
            pathlib.Path: The path to the output file.
        """
        # Run the simulation in parallel.
        # This is used even for num_processes = 1 because Geant4 has trouble with the Manager being created twice
        # in the main thread https://geant4-forum.web.cern.ch/t/problem-calling-twice-to-runmanger/1288.
        # It's easier to just use multiprocessing.Pool
        with contextlib.redirect_stdout(None):  # Suppress the output of the simulation
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
                pd.read_csv(file_x, skiprows=19, names=self.header)
                for file_x in output_files
            ],
            ignore_index=True,
        )
        # Sorting it by process_ID, EventID, and TrackID (Priority order)
        data.rename(self.new_header, axis="columns", inplace=True)
        data.sort_values(by=["process_ID", "EventID", "TrackID"], inplace=True)
        # Add the detector type as virtual
        data["detector_type"] = "virtual"
        # Add the latitude and longitude columns
        data["latitude"] = self.config.constructor.magnetic_field.latitude
        data["longitude"] = self.config.constructor.magnetic_field.longitude
        # Add a timestamp to the simulation.
        # This timestamp will be constructed from the start time + a linspace between 0 and config.time_resolution
        delta_time = np.linspace(
            0, self.config.time_resolution, len(data), endpoint=False
        )
        sim_time = self.config.constructor.magnetic_field.mag_time
        sim_timestamp = sim_time.timestamp()
        # Add the timestamp to the data
        # The timestamp is the start time + the delta time
        data["timestamp"] = sim_timestamp + delta_time
        # Save the start time in the ISO format
        data["start_time"] = sim_time.strftime("%Y-%m-%dT%H:%M:%S")
        # Last, add the ref idx to the density profile
        data["density_day_idx"] = self.config.constructor.density_profile.day_idx
        # Add run_ID so that the output can be traced back to the run
        data["run_ID"] = str(uuid.uuid4())  # Generate a unique ID for the run
        data.to_csv(self.save_dir / "output.csv", index=False)
        # Remove the individual files
        for file_x in output_files:
            file_x.unlink()

        return self.save_dir / "output.csv", data

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
