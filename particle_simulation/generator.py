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
import logging


class GPSGenerator(G4VUserPrimaryGeneratorAction):
    def __init__(self, config: dict[str, Any]) -> None:
        """Initializes the GPS (General Particle Source) generator.

        Args:
            config (dict[str, Any]): The configuration dictionary.
        """
        super().__init__()
        self.config: dict[str, Any] = config["generator"]
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
    def __init__(self, config: dict[str, Any]) -> None:
        """Initializes the Particle Gun generator.

        Args:
            config (dict[str, Any]): The configuration dictionary.
        """
        super().__init__()
        self.config: dict[str, Any] = config["generator"]
        self.particle_gun = G4ParticleGun(self.config["parameters"]["n_events"])
        self.logger = logging.getLogger("main")

        # Particle type
        self.particle = G4ParticleTable.GetParticleTable().FindParticle(
            self.config["parameters"]["particle"]
        )
        self.particle_gun.SetParticleDefinition(self.particle)
        self.logger.debug(f"Particle: {self.particle.GetParticleName()}")
        # Direction and origin of the particle
        px, py, pz = self.config["parameters"]["direction"]
        x, y, z = self.config["parameters"]["position"]

        self.particle_gun.SetParticleMomentumDirection(G4ThreeVector(px, py, pz))
        self.particle_gun.SetParticlePosition(G4ThreeVector(x * km, y * km, z * km))
        self.logger.debug(f"Particle direction: {px} {py} {pz}")
        self.logger.debug(f"Particle position: {x} {y} {z}")

        # Energy of the particle
        self.particle_gun.SetParticleEnergy(self.config["parameters"]["energy"] * GeV)
        self.logger.debug(f"Particle energy: {self.config['parameters']['energy']} GeV")

    def GeneratePrimaries(self, arg0: G4Event) -> None:
        """Generates the primary particles.

        Args:
            arg0 (G4Event): Instance that represents an event.
        """
        self.particle_gun.GeneratePrimaryVertex(arg0)
