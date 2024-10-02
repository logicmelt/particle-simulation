# Particle Simulation

## Dependencies setup

Pyenv is recommended to manage the Python version.
Poetry is required to install dependencies and launch the code.

```bash
pyenv shell 3.12.3
poetry install --no-root
```

## Simulation

The simulation can be run directly from a configuration file in yaml format:

```bash
python particle_simulation additional_files/simulation_config.yaml
```

Inside the save directory, defined within the yaml file, the log and results (as .csv) will be stored. 