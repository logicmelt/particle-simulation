from geant4_pybind import G4VUserActionInitialization, G4UserRunAction, G4Run, G4AnalysisManager
from particle_simulation.generator import GPSGenerator, ParticleGunGenerator

GENERATORS = {
    "gps": GPSGenerator,
    "particle_gun": ParticleGunGenerator
}

class ActionInitialization(G4VUserActionInitialization):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        # Create the generator
        self.generator = self.config["generator"]["type"]

    def Build(self):
        # In this function we can create Run, Event and Tracking actions (e.g.: Saving data per track, event, etc.)
        gen = GENERATORS[self.generator](self.config)
        # Set the generator as user action
        self.SetUserAction(gen)
        # Set the user run action
        self.SetUserAction(RunAct(self.config))


class RunAct(G4UserRunAction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config

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
        analysisManager.CreateNtupleDColumn("px")
        analysisManager.CreateNtupleDColumn("py")
        analysisManager.CreateNtupleDColumn("pz")
        analysisManager.CreateNtupleDColumn("x")
        analysisManager.CreateNtupleDColumn("y")
        analysisManager.CreateNtupleDColumn("z")

    def BeginOfRunAction(self, run: G4Run):
        # Open an output file
        analysisManager = G4AnalysisManager.Instance()
        idrun = run.GetRunID()
        analysisManager.OpenFile(f"hits_{idrun}.csv")
        analysisManager.FinishNtuple(0)

    def EndOfRunAction(self, run: G4Run):
        # Save the data
        analysisManager = G4AnalysisManager.Instance()
        # Write the data
        analysisManager.Write()
        # Close the file
        analysisManager.CloseFile()