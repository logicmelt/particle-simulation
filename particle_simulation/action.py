from geant4_pybind import (
    G4VUserActionInitialization,
    G4UserRunAction,
    G4Run,
    G4AnalysisManager,
    G4UserTrackingAction,
)
from particle_simulation.generator import GPSGenerator, ParticleGunGenerator
import logging
import pathlib

GENERATORS = {"gps": GPSGenerator, "particle_gun": ParticleGunGenerator}


class ActionInitialization(G4VUserActionInitialization):
    def __init__(self, config: dict, processNum: int):
        super().__init__()
        self.config = config
        # Create the generator
        self.generator = self.config["generator"]["type"]
        self.logger = logging.getLogger("main")
        self.processNum = processNum

    def Build(self):
        # In this function we can create Run, Event and Tracking actions (e.g.: Saving data per track, event, etc.)
        gen = GENERATORS[self.generator](self.config)
        self.logger.info(f"Using the generator: {self.generator}")
        # Set the generator as user action
        self.SetUserAction(gen)
        # Set the user run action
        self.SetUserAction(RunAct(self.config, self.processNum))
        # Set the user tracking action
        # self.SetUserAction(TrackingAction(self.config))


class RunAct(G4UserRunAction):
    def __init__(self, config: dict, processNum: int):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger("main")
        self.save_dir = pathlib.Path(self.config["save_dir"])
        self.processNum = processNum
        # Create an analysis manager
        # This is a singleton class, so we can access it from anywhere
        analysisManager = G4AnalysisManager.Instance()

        # Create N tuple
        analysisManager.CreateNtuple("hits", "Hits")

        # Event ID and track ID
        analysisManager.CreateNtupleIColumn("eventID")
        analysisManager.CreateNtupleIColumn("trackID")

        # Particle type and particle ID
        analysisManager.CreateNtupleSColumn("particle_type")
        analysisManager.CreateNtupleIColumn("particleID")

        # Momentum and Position
        analysisManager.CreateNtupleDColumn("px[MeV]")
        analysisManager.CreateNtupleDColumn("py[MeV]")
        analysisManager.CreateNtupleDColumn("pz[MeV]")
        analysisManager.CreateNtupleDColumn("x[mm]")
        analysisManager.CreateNtupleDColumn("y[mm]")
        analysisManager.CreateNtupleDColumn("z[mm]")

        # Create 1d Histogram for the energy spectrum
        # ih = analysisManager.CreateH1("0", "energy spectrum dN/dE = f(E)", 1000, 400, 340000)
        # analysisManager.SetH1Activation(ih, False)

    def BeginOfRunAction(self, run: G4Run):
        # Open an output file
        analysisManager = G4AnalysisManager.Instance()
        idrun = run.GetRunID()
        # Reset the analysis manager
        analysisManager.OpenFile(str(self.save_dir / f"hits_run_{idrun}_proc_{self.processNum}.csv"))
        self.logger.info(f"Creating the output file: {self.save_dir}/hits_{idrun}.csv")
        analysisManager.FinishNtuple(0)

    def EndOfRunAction(self, run: G4Run):
        # Save the data
        analysisManager = G4AnalysisManager.Instance()
        # Write the data
        analysisManager.Write()
        # Close the file
        analysisManager.CloseFile()
        self.logger.info("Finished writing the data to the output file")


class TrackingAction(G4UserTrackingAction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger("main")

    def PreUserTrackingAction(self, track):
        # Get the analysis manager
        analysisManager = G4AnalysisManager.Instance()
        # Fill the data
        kinetic_energy = track.GetKineticEnergy()
        analysisManager.FillH1(0, kinetic_energy)
