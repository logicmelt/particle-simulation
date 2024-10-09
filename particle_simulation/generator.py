from geant4_pybind import (
    G4ParticleGun,
    G4GeneralParticleSource,
    G4VUserPrimaryGeneratorAction,
    G4ParticleTable,
    G4ParticleDefinition,
    G4ThreeVector,
    G4Event,
)

# Units
from geant4_pybind import GeV, km
from typing import Any
from particle_simulation.config import GeneratorConfig
import logging


class GPSGenerator(G4VUserPrimaryGeneratorAction):
    def __init__(self, config_gen: GeneratorConfig) -> None:
        """Initializes the GPS (General Particle Source) generator.

        Args:
            config_gen (GeneratorConfig): Generator configuration parameters.
        """
        super().__init__()
        self.config = config_gen
        self.particle_source = G4GeneralParticleSource()
        self.logger = logging.getLogger("main")

    def GeneratePrimaries(self, arg0: G4Event) -> None:
        """Generates the primary particles.

        Args:
            arg0 (G4Event): Instance that represents an event.
        """
        self.logger.debug(
            f"Shooting a {self.particle_source.GetParticleDefinition().GetParticleName()}"
        )
        self.particle_source.GeneratePrimaryVertex(arg0)


class ParticleGunGenerator(G4VUserPrimaryGeneratorAction):
    def __init__(self, config_gen: GeneratorConfig) -> None:
        """Initializes the particle gun generator.

        Args:
            config_gen (GeneratorConfig): Generator configuration parameters.
        """
        super().__init__()
        self.config = config_gen
        self.particle_gun = G4ParticleGun(self.config.n_events)
        self.logger = logging.getLogger("main")

        # Particle type
        self.particle = G4ParticleTable.GetParticleTable().FindParticle(
            self.config.particle
        )
        self.particle_gun.SetParticleDefinition(self.particle)
        self.logger.debug(f"Particle: {self.particle.GetParticleName()}")
        # Direction and origin of the particle
        px, py, pz = self.config.direction
        x, y, z = self.config.position

        self.particle_gun.SetParticleMomentumDirection(G4ThreeVector(px, py, pz))
        self.particle_gun.SetParticlePosition(G4ThreeVector(x * km, y * km, z * km))
        self.logger.debug(f"Particle direction: {px} {py} {pz}")
        self.logger.debug(f"Particle position: {x} {y} {z}")

        # Energy of the particle
        self.particle_gun.SetParticleEnergy(self.config.energy * GeV)
        self.logger.debug(f"Particle energy: {self.config.energy} GeV")

    def GeneratePrimaries(self, arg0: G4Event) -> None:
        """Generates the primary particles.

        Args:
            arg0 (G4Event): Instance that represents an event.
        """
        self.particle_gun.GeneratePrimaryVertex(arg0)
