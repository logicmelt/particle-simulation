# Particle Simulation

## Dependencies setup

Pyenv is recommended to manage the Python version.
Poetry is required to install dependencies and launch the code.

```bash
pyenv shell 3.12.3
poetry install --no-root
```

## Simulation

Particle-simulation supports both API and CLI-based simulations.

```python
import particle_simulation.config as config
from particle_simulation.utils import load_config
from particle_simulation.runner import SimRunner

# Load a config file (yaml or json) or create one from scratch as a dict
config_file = load_config("additional_files/simulation_config.yaml")
# Create a Config instance
config_pyd = config.Config(**config_file) # Pydantic will parse and validate the input config file
# Create an instance of the runner
runner = SimRunner(config_pyd)
# Run the simulation
runner.run()
```
Via CLI we have three options:
- Use a configuration file 
```bash
python particle_simulation --config_file additional_files/simulation_config.yaml
```
- Set up the simulation using command line parameters
```bash
python particle_simulation --random_seed 42 --constructor.sensitive_detectors.enabled True
```
- A combination of both: Use a configuration file and override from command line parameters.
```bash
python particle_simulation --config_file additional_files/simulation_config.yaml --random_seed 648 --constructor.sensitive_detectors.enabled False
```
Within the save directory the log and results (as .csv) will be stored alongisde the configuration file as json. 
