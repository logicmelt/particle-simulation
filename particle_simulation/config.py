from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    CliSettingsSource,
)
from pydantic import Field, model_validator, StringConstraints
from typing import Annotated
import pathlib
import time
import datetime


class GeneratorConfig(BaseSettings):
    """Configuration settings for the particle generator."""

    gen_type: Annotated[str, StringConstraints(to_lower=True)] = Field(
        default="gps", description="Type of generator to use: gps or particle_gun"
    )
    n_events: int = Field(
        default=1,
        ge=1,
        description=(
            "Number of particles to be shoot at one invokation of GeneratePrimaryVertex()"
            "method for a particle gun (Same physical quantities)"
        ),
    )
    energy: float = Field(
        default=100.0,
        gt=0,
        description="Energy of the primary particle in Gev (Only particle gun generator)",
    )
    particle: Annotated[str, StringConstraints(to_lower=True)] = Field(
        default="proton",
        description="Type of primary particle to shoot in the particle gun generator",
    )
    position: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0),
        min_length=3,
        max_length=3,
        description=(
            "Position of the primary particle in km (Particle gun generator)."
            "Distance with respect the center of the geometry"
        ),
    )
    direction: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 1.0),
        min_length=3,
        max_length=3,
        description="Direction of the momentum of the primary particle (Particle gun generator)",
    )

    @model_validator(mode="after")
    def validate_data(self) -> "GeneratorConfig":
        """Validate the data in the GeneratorConfig."""
        assert self.gen_type in [
            "gps",
            "particle_gun",
        ], f"Invalid generator type {self.gen_type}"
        if self.gen_type == "particle_gun":
            assert self.particle in [
                "e-",
                "e+",
                "gamma",
                "mu-",
                "mu+",
                "nu_e",
                "nu_mu",
                "proton",
                "neutron",
                "geantino",
                "chargedgeantino",
            ], f"Invalid particle {self.particle}"
        return self


class SensitiveDetectorConfig(BaseSettings):
    """Configuration settings for the sensitive detector."""

    enabled: bool = Field(
        default=True, description="Enable or disable the sensitive detector"
    )
    altitude: tuple[float, ...] = Field(
        default=(0.0,),
        description="Altitude of the sensitive detector in km",
    )
    particles: tuple[str, ...] = Field(
        default=("mu-",), description="List of particles to be detected"
    )

    @model_validator(mode="after")
    def validate_data(self) -> "SensitiveDetectorConfig":
        """Validate the data in the SensitiveDetectorConfig."""
        if self.enabled:
            # If the sensitive detector is enabled, the altitude and particles must be provided
            assert (
                len(self.altitude) > 0
            ), "At least one altitude must be provided to place the sensitive detector"
            assert (
                len(self.particles) > 0
            ), "At least one particle must be provided for the sensitive detector"
            # Validate the altitude and particles values
            for alt in self.altitude:
                assert alt >= 0, "Altitude must be positive or zero"
            for particle in self.particles:
                assert particle in [
                    "e-",
                    "e+",
                    "gamma",
                    "mu-",
                    "mu+",
                    "nu_e",
                    "nu_mu",
                    "proton",
                    "neutron",
                    "geantino",
                    "chargedgeantino",
                    "all",
                ], f"Invalid particle {particle} for the sensitive detector"
        return self


class DensityProfileConfig(BaseSettings):
    """Configuration settings for the density profile."""

    density_file: pathlib.Path = Field(
        default="", description="Path to the json file with the density profiles."
    )
    day_idx: int = Field(
        default=0, ge=0, description="Index of the day in the density file"
    )


class MagneticFieldConfig(BaseSettings):
    """Configuration settings for the magnetic field."""

    enabled: bool = Field(
        default=True, description="Enable or disable the magnetic field"
    )
    mag_source: Annotated[str, StringConstraints(to_lower=True)] = Field(
        default="file",
        description="Source of the magnetic field: file or estimated from latitude, longitude and date.",
    )
    mag_file: pathlib.Path = Field(
        default="",
        description=(
            "File containing the magnetic field as a csv with 7 columns:"
            "Bx, By, Bz, altitude, latitude, longitude and date"
            "Or a txt file with paths to the csv files, the start time and ent time of each file"
        ),
    )
    latitude: float = Field(
        default=42.224,
        le=90,
        ge=-90,
        description="Latitude of the detector in decimal degrees (World Geodetic System 1984)."
        "Positive north equator (default: 42.224).",
    )
    longitude: float = Field(
        default=-8.716,
        le=180,
        ge=-180,
        description="Longitude of the detector in decimal degrees (World Geodetic System 1984)."
        "Positive east of the prime meridian (default: -8.716).",
    )
    mag_time: datetime.datetime = Field(
        default=datetime.datetime(2021, 1, 1),
        description="Date to get the magnetic field values. Format YYYY-MM-DDTHH:MM:SS.",
    )

    @property
    def decimal_year(self) -> float:
        """Return the decimal year from a date in format YYYY-MM-DD."""
        # Precision of days so we use only the date
        return self.transform_to_decimal_year(self.mag_time.date())

    def transform_to_decimal_year(self, date: datetime.date) -> float:
        """Return the decimal year from a date in format YYYY-MM-DD.

        Args:
            date (datetime.date): Date in format YYYY-MM-DD

        Returns:
            float: Decimal year
        """
        # Start of the year
        start = datetime.date(date.year, 1, 1).toordinal()
        # Length of the year
        year_length = datetime.date(date.year + 1, 1, 1).toordinal() - start
        # Return the decimal year
        return date.year + float(date.toordinal() - start) / year_length


class ConstructorConfig(BaseSettings):
    """Configuration settings for the geometry constructor."""

    input_geom: Annotated[str, StringConstraints(to_lower=True)] = Field(
        default="custom", description="gdml or custom"
    )
    gdml_file: pathlib.Path = Field(default="", description="GDML file to be used")
    magnetic_field: MagneticFieldConfig = MagneticFieldConfig()
    sensitive_detectors: SensitiveDetectorConfig = Field(
        default=SensitiveDetectorConfig()
    )
    export_gdml: bool = Field(
        default=False, description="Export the geometry to a GDML file"
    )
    geometry: Annotated[str, StringConstraints(to_lower=True)] = Field(
        default="flat", description="Type of geometry to be used: flat or curved"
    )
    earth_radius: float = Field(
        default=6371, gt=0, description="Radius of the Earth in km"
    )
    atmos_size: float = Field(
        default=100,
        gt=0,
        description="Size of the atmosphere in km (arc lenght if curved geometry)",
    )
    atmos_height: float = Field(
        default=70, gt=0, description="Height of the atmosphere in km"
    )
    atmos_comp: tuple[str | float, ...] = Field(
        default=("N", 70, "O", 27, "Ar", 3),
        min_length=2,
        description="Composition of the atmosphere in %",
    )
    atmos_n_points: int = Field(
        default=100, gt=0, description="Number of points in the density profile"
    )

    density_profile: DensityProfileConfig = DensityProfileConfig()

    @model_validator(mode="after")
    def validate_data(self) -> "ConstructorConfig":
        """Validate the data in the ConstructorConfig."""
        assert self.input_geom in ["gdml", "custom"]
        assert self.geometry in ["flat", "curved"]
        return self


class Config(BaseSettings):
    """Configuration settings for the simulation."""

    # Allow the configuration to be parsed from the command line
    model_config = SettingsConfigDict(cli_parse_args=True, env_nested_delimiter="__")
    # Random seed from the current time if not provided
    random_seed: int = Field(
        default_factory=lambda: int(time.time()),
        gt=0,
        description="Random seed for reproducibility. If not provided, it will be set to the current time",
    )
    num_processes: int = Field(
        default=1, ge=1, description="Number of processes to use for simulation"
    )
    logger_level: Annotated[str, StringConstraints(to_upper=True)] = Field(
        default="INFO", description="Logger level"
    )
    particles_per_run: int = Field(
        default=1, ge=1, description="Number of particles to be generated per run"
    )
    generator: GeneratorConfig = GeneratorConfig()
    constructor: ConstructorConfig = ConstructorConfig()
    macro_files: tuple[pathlib.Path, ...] | pathlib.Path = Field(
        description="Macro files to be executed as a list or a single string"
    )
    save_dir: pathlib.Path = Field(description="Directory to save the output files")
    time_resolution: float = Field(
        default=1e6,
        gt=0,
        description="Time resolution of the simulation in microseconds. This parameter defines\
            How much time is covered by one simulation (It's not a real time step, just for the output files).",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            CliSettingsSource(settings_cls, cli_parse_args=True),
            init_settings,
        )

    @model_validator(mode="after")
    def validate_data(self) -> "Config":
        """Validate the data in the Config."""
        if isinstance(self.macro_files, pathlib.Path):
            assert (
                self.macro_files.is_file()
            ), f"Macro file {self.macro_files} not found"
        else:
            for macro_file in self.macro_files:
                assert macro_file.is_file(), f"Macro file {macro_file} not found"
        assert self.logger_level in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ], f"Invalid logger level {self.logger_level}"
        if self.constructor.input_geom == "gdml":
            assert (
                self.constructor.gdml_file.is_file()
            ), f"GDML File {self.constructor.gdml_file} not found"

        if self.constructor.magnetic_field.mag_source == "file":
            if self.constructor.magnetic_field.mag_file.suffix == ".csv":
                assert (
                    self.constructor.magnetic_field.mag_file.is_file()
                ), f"Magnetic field file {self.constructor.magnetic_field.mag_file} not found"
            elif self.constructor.magnetic_field.mag_file.suffix == ".txt":
                assert (
                    self.constructor.magnetic_field.mag_file.is_file()
                ), f"List of magnetic fields files {self.constructor.magnetic_field.mag_file} not found"

        assert (
            self.constructor.density_profile.density_file.is_file()
        ), f"Density profile file {self.constructor.density_profile} not found"

        assert self.constructor.density_profile.density_file.suffix in [
            ".json"
        ], f"Invalid density profile file extension"
        return self
