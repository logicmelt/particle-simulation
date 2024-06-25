from geant4_pybind import G4VSensitiveDetector, G4Step, G4TouchableHistory, G4AnalysisManager, G4RunManager
import logging

class SensDetector(G4VSensitiveDetector):
    def __init__(self, config: dict, name: str, correction_factor: float = 0.0):
        super().__init__(name)
        self.config = config
        self.accepted_particles = self.config["sensitive_detectors"]["particles"]
        self.accepted_particles.append("all")
        # Correction factor to the z-axis of the particles due to the geometry.
        self.correction_factor = correction_factor
        self.track_list = set()
        self.logger = logging.getLogger("main")

    def ProcessHits(self, step: G4Step, history: G4TouchableHistory):
        # Get the analysis manager (Singleton)
        analysisManager = G4AnalysisManager.Instance()

        # Get the track
        track = step.GetTrack()

        # From the track get particle type and ID
        particle = track.GetParticleDefinition().GetPDGEncoding()
        particle_type = track.GetParticleDefinition().GetParticleName()

        # Check if the particle is in the accepted particles
        if particle_type not in self.accepted_particles:
            return True

        # Get Event ID and Track ID
        event_id = G4RunManager.GetRunManager().GetCurrentEvent().GetEventID()
        track_id = track.GetTrackID()

        # To avoid duplicates check if the track ID is already in the list. We only care about the first hit
        if track_id in self.track_list:
            return True
        # Add the track ID to the list
        self.track_list.add(track_id)
        
        # Get the momentum and position
        momentum = step.GetPreStepPoint().GetMomentum()
        position = step.GetPreStepPoint().GetPosition()

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