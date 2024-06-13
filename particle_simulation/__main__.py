from geant4_pybind import G4UImanager, G4UIExecutive, G4RunManagerFactory, G4RunManagerType, G4VisExecutive, QGSP_BERT_HP
from particle_simulation.construction import DetectorConstruction
import yaml

def load_config(config_file):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config

def main():
    ui = G4UIExecutive(1, ['vis.mac'])
    # Load the configuration file
    config = load_config("additional_files/simulation_config.yaml")

    # Create an instance of the run manager
    runManager = G4RunManagerFactory.CreateRunManager(G4RunManagerType.Serial)

    # Load the geometry
    runManager.SetUserInitialization(DetectorConstruction(config["constructor"]["predefined"]))
    # Physics list
    runManager.SetUserInitialization(QGSP_BERT_HP())

    # Initialize the run manager
    runManager.Initialize()

    visManager = G4VisExecutive()
    visManager.Initialize()
    # Create an instance of the UI manager
    uiManager = G4UImanager.GetUIpointer()
    uiManager.ApplyCommand("/control/execute vis.mac")
    ui.SessionStart()

if __name__ == "__main__":
    main()