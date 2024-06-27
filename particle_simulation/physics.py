from geant4_pybind import G4VModularPhysicsList, G4EmStandardPhysics, G4OpticalPhysics


class MyPhysicsList(G4VModularPhysicsList):
    def __init__(self):
        super().__init__()
        self.RegisterPhysics(G4EmStandardPhysics())
