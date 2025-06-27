FROM python:3.12.6

# Environment Variables
    # Python
ENV PYTHONUNBUFFERED=1 \
    # Poetry
    POETRY_VIRTUALENVS_CREATE=false \ 
    POETRY_HOME="/opt/poetry" \
    # Geant4
    G4NEUTRONHPDATA=/data/G4NDL4.7 \
    G4LEDATA=/data/G4EMLOW8.5 \
    G4LEVELGAMMADATA=/data/PhotonEvaporation5.7 \
    G4RADIOACTIVEDATA=/data/RadioactiveDecay5.6 \
    G4PARTICLEXSDATA=/data/G4PARTICLEXS4.0 \
    G4PIIDATA=/data/G4PII1.3 \
    G4REALSURFACEDATA=/data/RealSurface2.2 \
    G4SAIDXSDATA=/data/G4SAIDDATA2.0 \
    G4ABLADATA=/data/G4ABLA3.3 \
    G4INCLDATA=/data/G4INCL1.2 \
    G4ENSDFSTATEDATA=/data/G4ENSDFSTATE2.3 \
    # Path
    PATH="/opt/poetry/bin:/opt/poetry/venv:$PATH"

# Change to the app directory
WORKDIR /app

# Stuff needed for OpenGL
RUN apt update \
    && apt install -y --no-install-recommends libsm6 libxext6 \
        ffmpeg libfontconfig1 libxrender1 libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3
COPY pyproject.toml poetry.lock README.md ./
RUN poetry check --lock && poetry install --no-root

# Copy the download script and run it
COPY particle_simulation/download_geant4_datasets.py /app/particle_simulation/download_geant4_datasets.py
RUN poetry run python particle_simulation/download_geant4_datasets.py --data_dir /data

# Copy the rest of the code
ADD additional_files /app/additional_files
ADD particle_simulation /app/particle_simulation

# Run the simulation as an entry point
CMD ["poetry", "run", "python", "-m", "particle_simulation.icos_sim", "--config_file", "additional_files/simulation_config.yaml", "--sim_cycles", "-1"]
