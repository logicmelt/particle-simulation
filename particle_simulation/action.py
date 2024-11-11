from geant4_pybind import (
    G4ClassificationOfNewTrack,
    G4VUserActionInitialization,
    G4UserRunAction,
    G4Run,
    G4Track,
    G4Event,
    G4AnalysisManager,
    G4UserTrackingAction,
    G4UserStackingAction,
    G4UserEventAction,
    G4ClassificationOfNewTrack,
    G4Electron,
    G4Positron,
    MeV,
)
from particle_simulation.generator import GPSGenerator, ParticleGunGenerator
from particle_simulation.config import Config

import logging

GENERATORS = {"gps": GPSGenerator, "particle_gun": ParticleGunGenerator}


class ActionInitialization(G4VUserActionInitialization):
    def __init__(self, config_pyd: Config, processNum: int) -> None:
        """
        Initializes an instance of the G4VUserActionInitialization class that allows to create the user actions.
        Args:
            config_pyd (Config): Configuration settings.
            processNum (int): The process number. Used to create unique output files.
        Returns:
            None
        """

        super().__init__()
        self.config = config_pyd
        # Create the generator
        self.generator: str = self.config.generator.gen_type
        self.logger = logging.getLogger("main")
        self.processNum = processNum

    def Build(self) -> None:
        """This function is called by the run manager to build the user actions."""
        # In this function we can create Run, Event and Tracking actions (e.g.: Saving data per track, event, etc.)
        gen = GENERATORS[self.generator](self.config.generator)
        self.logger.info(f"Using the generator: {self.generator}")
        # Set the generator as user action
        self.SetUserAction(gen)
        # Set the user run action
        self.SetUserAction(RunAct(self.config, self.processNum))
        # Set the user tracking action
        # self.SetUserAction(TrackingAction(self.config))
        # Set the user stacking action (This is used to kill particles not needed for the sim: electrons and positrons)
        self.SetUserAction(StackingAction())
        # Set the user event action (This is used to save the energy of the primary particles)
        # self.SetUserAction(UserEvent(self.config, self.processNum))


class StackingAction(G4UserStackingAction):
    def ClassifyNewTrack(self, aTrack: G4Track) -> G4ClassificationOfNewTrack:
        """This function is called for every new track in the stack.

        Args:
            aTrack (G4Track): A track object from Geant4.

        Returns:
            G4ClassificationOfNewTrack: The classification of the new track.
        """
        # Kill positrons and electrons. They are not interesting for us as they cant generate muons
        if aTrack.GetDefinition() == G4Electron.Electron():
            return G4ClassificationOfNewTrack.fKill
        if aTrack.GetDefinition() == G4Positron.Positron():
            return G4ClassificationOfNewTrack.fKill
        return G4ClassificationOfNewTrack.fUrgent


class RunAct(G4UserRunAction):
    def __init__(self, config_pyd: Config, processNum: int) -> None:
        """Initializes a run action that is called at the beginning and end of a run.

        Args:
            config_pyd (Config): Configuration parameters.
            processNum (int): The process number. Used to create unique output files.
        """
        super().__init__()
        self.config = config_pyd
        self.logger = logging.getLogger("main")
        self.save_dir = config_pyd.save_dir
        self.processNum = processNum
        # Create an analysis manager
        # This is a singleton class, so we can access it from anywhere
        analysisManager = G4AnalysisManager.Instance()

        # Create N tuple
        analysisManager.CreateNtuple("hits", "Hits")

        # Event ID and track ID
        analysisManager.CreateNtupleIColumn("eventID")
        analysisManager.CreateNtupleIColumn("trackID")
        # Process ID so that we can identify the process that generated the particles
        analysisManager.CreateNtupleIColumn("process_ID")

        # Particle type and particle ID
        analysisManager.CreateNtupleSColumn("particle_type")
        analysisManager.CreateNtupleIColumn("particleID")

        # Momentum and Position
        analysisManager.CreateNtupleDColumn("px[MeV]")
        analysisManager.CreateNtupleDColumn("py[MeV]")
        analysisManager.CreateNtupleDColumn("pz[MeV]")
        analysisManager.CreateNtupleDColumn("x[mm]")
        analysisManager.CreateNtupleDColumn("y[mm]")
        analysisManager.CreateNtupleDColumn("z[mm]")

        # Angles of the particles
        analysisManager.CreateNtupleDColumn("theta[rad]")
        analysisManager.CreateNtupleDColumn("phi[rad]")

        # Event start time
        analysisManager.CreateNtupleDColumn("time[s]")

        # Create 1d Histogram for the energy spectrum
        # ih = analysisManager.CreateH1("0", "energy spectrum dN/dE = f(E)", 1000, 400, 340000)
        # analysisManager.SetH1Activation(ih, False)

    def BeginOfRunAction(self, arg0: G4Run) -> None:
        """This function is called at the beginning of a run.

        Args:
            arg0 (G4Run): A run object from Geant4.
        """
        # Open an output file
        analysisManager = G4AnalysisManager.Instance()
        idrun = arg0.GetRunID()
        # Reset the analysis manager
        output_file = str(
            self.save_dir / f"hits_run_{idrun}_proc_{self.processNum}.csv"
        )
        analysisManager.OpenFile(output_file)
        self.logger.info(f"Creating the output file: {output_file}")
        analysisManager.FinishNtuple(0)

    def EndOfRunAction(self, arg0: G4Run) -> None:
        """This function is called at the end of a run.

        Args:
            arg0 (G4Run): A run object from Geant4.
        """
        # Save the data
        analysisManager = G4AnalysisManager.Instance()
        # Write the data
        analysisManager.Write()
        # Close the file
        analysisManager.CloseFile()
        self.logger.info("Finished writing the data to the output file")


class UserEvent(G4UserEventAction):
    def __init__(self, config_pyd: Config, process_num: int) -> None:
        """Initializes an event action that is called at the beginning and end of an event.

        Args:
            config_pyd (Config): Configuration parameters.
            process_num (int): The process number. Used to create unique output files.
        """
        # This action is used to save the energy of the primary particles (e.g.: protons that reach the atmosphere)
        # so that we can compare it with the energy of the particles that reach the sensitive detectors.
        super().__init__()
        self.config = config_pyd
        self.logger = logging.getLogger("main")
        self.process_num = process_num

    def BeginOfEventAction(self, anEvent: G4Event) -> None:
        """This function is called at the beginning of an event.

        Args:
            anEvent (G4Event): An event object from Geant4.
        """
        # Get energy of the event
        event = anEvent.GetPrimaryVertex(0)  # gps only throws one particle
        energy = event.GetPrimary().GetMomentum().mag() / MeV
        # Save the event ID and the energy
        with open(
            self.config.save_dir / f"primary_info_{self.process_num}.txt", "a"
        ) as f:
            f.write(f"{anEvent.GetEventID()} {energy} \n")


class TrackingAction(G4UserTrackingAction):
    def __init__(self, config_pyd: Config) -> None:
        """Initializes a tracking action that allows to interact with the information of the tracked particle.

        Args:
            config_pyd (Config): Configuration parameters.
        """
        super().__init__()
        self.config = config_pyd
        self.logger = logging.getLogger("main")

    def PreUserTrackingAction(self, arg0: G4Track) -> None:
        """This function is called before the tracking of a particle and stores the kinetic energy of the particle.

        Args:
            arg0 (G4Track): A track object from Geant4.
        """
        # Get the analysis manager
        analysisManager = G4AnalysisManager.Instance()
        # Fill the data
        kinetic_energy = arg0.GetKineticEnergy()
        analysisManager.FillH1(0, kinetic_energy)
