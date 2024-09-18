#/bin/bash

# First, we need to download the Geant4 datasets if needed
python particle_simulation/download_geant4_datasets.py

# Then, we build the docker image
docker build -t particle_simulation .