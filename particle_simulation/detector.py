from geant4_pybind import (
    G4VSensitiveDetector,
    G4Step,
    G4TouchableHistory,
    G4AnalysisManager,
    G4RunManager,
    fStopAndKill,
    rad,
    second,
)
from particle_simulation.config import ConstructorConfig
import numpy as np
import logging


class SensDetector(G4VSensitiveDetector):
    def __init__(
        self,
        config_file: ConstructorConfig,
        name: str,
        process_num: int,
        correction_factor: float = 0.0,
    ) -> None:
        """Initializes a sensitive detector that will be used to save data from the simulation.

        Args:
            config_file (ConstructorConfig): Configuration settings for the constructor.
            name (str): Name of the sensitive detector.
            process_num (int): Process number. Used to tag the detected particles.
            correction_factor (float, optional): Correction factor to the z-axis of the particles due to the geometry. Defaults to 0.0.
        """
        super().__init__(name)
        self.config = config_file
        self.process_num = process_num
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

        # The time since the beginning of the EVENT in SECONDS
        global_time = arg0.GetPreStepPoint().GetGlobalTime() / second

        # Estimate the angles
        touchable = arg0.GetPreStepPoint().GetTouchable()
        mom_dir = arg0.GetPreStepPoint().GetMomentumDirection()
        local_position = touchable.GetHistory().GetTopTransform().TransformPoint(position)
        theta = mom_dir.getTheta() / rad
        phi = mom_dir.getPhi() / rad

        self.logger.debug(f"Theta: {theta} Phi: {phi} Position: {position} Local_position: {local_position} Mom_dir: {mom_dir}")

        # If the particle has reached the ground level, stop the track
        # Otherwise we might have double counting of particles
        z_pos = position.z - self.correction_factor
        if z_pos <= 5000:  # In mm
            track.SetTrackStatus(fStopAndKill)

        # Fill the N tuple
        analysisManager.FillNtupleIColumn(0, event_id)
        analysisManager.FillNtupleIColumn(1, track_id)
        analysisManager.FillNtupleIColumn(2, self.process_num)
        analysisManager.FillNtupleSColumn(3, particle_type)
        analysisManager.FillNtupleIColumn(4, particle)
        analysisManager.FillNtupleDColumn(5, momentum.x)
        analysisManager.FillNtupleDColumn(6, momentum.y)
        analysisManager.FillNtupleDColumn(7, momentum.z)
        analysisManager.FillNtupleDColumn(8, position.x)
        analysisManager.FillNtupleDColumn(9, position.y)
        analysisManager.FillNtupleDColumn(10, position.z - self.correction_factor)
        analysisManager.FillNtupleDColumn(13, global_time)

        # Add to the Ntuple
        analysisManager.AddNtupleRow(0)

        return True
