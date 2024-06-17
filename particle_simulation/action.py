from geant4_pybind import G4VUserActionInitialization
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