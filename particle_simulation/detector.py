from geant4_pybind import (
    G4VSensitiveDetector,
    G4Step,
    G4TouchableHistory,
    G4AnalysisManager,
    G4RunManager,
)
from typing import Any
from particle_simulation.config import ConstructorConfig
import logging


class SensDetector(G4VSensitiveDetector):
    def __init__(
        self, config_file: ConstructorConfig, name: str, correction_factor: float = 0.0
    ) -> None:
        """Initializes a sensitive detector that will be used to save data from the simulation.

        Args:
            config_file (ConstructorConfig): Configuration settings for the constructor.
            name (str): Name of the sensitive detector.
            correction_factor (float, optional): Correction factor to the z-axis of the particles due to the geometry. Defaults to 0.0.
        """
        super().__init__(name)
        self.config = config_file
        self.accepted_particles: set[str] = set(
            self.config.sensitive_detectors.particles
        )
        # Correction factor to the z-axis of the particles due to the geometry.
        self.correction_factor = correction_factor
        self.logger = logging.getLogger("main")
        self.logger.debug(self.accepted_particles)

    def ProcessHits(self, arg0: G4Step, arg1: G4TouchableHistory) -> bool:
        """This function is called when a particle hits the sensitive detector.

        Args:
            arg0 (G4Step): Steps of the particle from where we can extract information.
            arg1 (G4TouchableHistory): Touchable detector element (Physical volume, logical volume...).

        Returns:
            bool: True if the hit was processed successfully.
        """
        # Get the analysis manager (Singleton)
        analysisManager = G4AnalysisManager.Instance()

        # Get the track
        track = arg0.GetTrack()

        # From the track get particle type and ID
        particle = track.GetParticleDefinition().GetPDGEncoding()
        particle_type = track.GetParticleDefinition().GetParticleName()

        # Check if the particle is in the accepted particles
        if (particle_type not in self.accepted_particles) and (
            "all" not in self.accepted_particles
        ):
            return True
        # Get Event ID and Track ID
        event_id = G4RunManager.GetRunManager().GetCurrentEvent().GetEventID()
        track_id = track.GetTrackID()

        # Get the momentum and position
        momentum = arg0.GetPreStepPoint().GetMomentum()
        position = arg0.GetPreStepPoint().GetPosition()

        # Fill the N tuple
        analysisManager.FillNtupleIColumn(0, event_id)
        analysisManager.FillNtupleIColumn(1, track_id)
        analysisManager.FillNtupleSColumn(2, particle_type)
        analysisManager.FillNtupleIColumn(3, particle)
        analysisManager.FillNtupleDColumn(4, momentum.x)
        analysisManager.FillNtupleDColumn(5, momentum.y)
        analysisManager.FillNtupleDColumn(6, momentum.z)
        analysisManager.FillNtupleDColumn(7, position.x)
        analysisManager.FillNtupleDColumn(8, position.y)
        analysisManager.FillNtupleDColumn(9, position.z - self.correction_factor)

        # Add to the Ntuple
        analysisManager.AddNtupleRow(0)

        return True
