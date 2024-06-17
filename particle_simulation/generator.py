from geant4_pybind import G4ParticleGun, G4GeneralParticleSource, G4VUserPrimaryGeneratorAction, G4ParticleTable, G4ParticleDefinition, G4ThreeVector
# Units
from geant4_pybind import GeV, km

class GPSGenerator(G4VUserPrimaryGeneratorAction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config["generator"]
        self.particle_source = G4GeneralParticleSource()

    def GeneratePrimaries(self, event):
        self.particle_source.GeneratePrimaryVertex(event)


class ParticleGunGenerator(G4VUserPrimaryGeneratorAction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config["generator"]
        self.particle_gun = G4ParticleGun(self.config["parameters"]["n_events"])

        # Particle type
        self.particle = G4ParticleTable.GetParticleTable().FindParticle(self.config["parameters"]["particle"])
        self.particle_gun.SetParticleDefinition(self.particle)

        # Direction and origin of the particle
        px, py, pz = self.config["parameters"]["direction"]
        x, y, z = self.config["parameters"]["position"]

        self.particle_gun.SetParticleMomentumDirection(G4ThreeVector(px, py, pz))
        self.particle_gun.SetParticlePosition(G4ThreeVector(x*km, y*km, z*km))

        # Energy of the particle
        self.particle_gun.SetParticleEnergy(self.config["parameters"]["energy"] * GeV)


    def GeneratePrimaries(self, event):
        self.particle_gun.GeneratePrimaryVertex(event)