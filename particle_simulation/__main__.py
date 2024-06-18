from geant4_pybind import G4UImanager, G4UIExecutive, G4RunManagerFactory, G4RunManagerType, G4VisExecutive, QGSP_BERT_HP
from particle_simulation.construction import DetectorConstruction
from particle_simulation.action import ActionInitialization
import yaml

def load_config(config_file: str):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config

def main():
    # Load the configuration file
    config = load_config("additional_files/simulation_config.yaml")
    # Macro files
    macro_files = config["macro_files"]

    # Create an instance of the run manager
    runManager = G4RunManagerFactory.CreateRunManager(G4RunManagerType.Serial)

    # Load the geometry
    runManager.SetUserInitialization(DetectorConstruction(config))
    # Physics list
    runManager.SetUserInitialization(QGSP_BERT_HP())
    # Run action
    runManager.SetUserInitialization(ActionInitialization(config))

    # Initialize the run manager
    runManager.Initialize()

    ui = G4UIExecutive(1, ['vis.mac'])
    visManager = G4VisExecutive()
    visManager.Initialize()
    # Create an instance of the UI manager
    uiManager = G4UImanager.GetUIpointer()

    # Apply the commands in the macro file
    if isinstance(macro_files, str):
        uiManager.ApplyCommand(f"/control/execute {macro_files}")
    else:
        for macro in macro_files:
            uiManager.ApplyCommand(f"/control/execute {macro}")

if __name__ == "__main__":
    main()