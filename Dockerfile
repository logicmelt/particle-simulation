FROM python:3.12.6

# Stuff needed for openGL
RUN apt update && apt install -y libsm6 libxext6 ffmpeg libfontconfig1 libxrender1 libgl1-mesa-glx

# Install poetry
ENV POETRY_VIRTUALENVS_CREATE=false \ 
    POETRY_HOME="/opt/poetry"
RUN curl -sSL https://install.python-poetry.org | python3
ENV PATH="$POETRY_HOME/bin:$POETRY_HOME/venv:$PATH"
COPY pyproject.toml poetry.lock README.md ./
RUN poetry check --lock && poetry install

# Copy the rest of the code
COPY . /app

# Change to the app directory
WORKDIR /app

# Run the simulation as an entry point
CMD ["poetry", "run", "python", "-m", "particle_simulation", "additional_files/simulation_config.yaml"]
