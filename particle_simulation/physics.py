from geant4_pybind import G4VModularPhysicsList, G4EmStandardPhysics, G4OpticalPhysics


class MyPhysicsList(G4VModularPhysicsList):
    def __init__(self) -> None:
        """Initializes the physics list for the simulation."""
        super().__init__()
        self.RegisterPhysics(G4EmStandardPhysics())
