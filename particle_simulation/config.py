from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, StringConstraints
from typing import Annotated
import pathlib
import time


class GeneratorConfig(BaseSettings):
    """Configuration settings for the particle generator."""

    gen_type: Annotated[str, StringConstraints(to_lower=True)] = Field(
        default="gps", description="Type of generator to use: gps or particle_gun"
    )
    n_events: int = Field(
        default=1,
        gt=0,
        description="Number of events to be generated per run using the particle gun generator",
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
        default=(0.0, 0.0, 0.0), min_length=3, max_length=3,
        description="Position of the primary particle in km (Particle gun generator). Distance with respect the center of the geometry",
    )
    direction: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 1.0), min_length=3, max_length=3,
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
        min_length=1,
        description="Altitude of the sensitive detector in km",
    )
    particles: tuple[str, ...] = Field(
        default=("mu-",), min_length=1, description="List of particles to be detected"
    )

    @model_validator(mode="after")
    def validate_data(self) -> "SensitiveDetectorConfig":
        """Validate the data in the SensitiveDetectorConfig."""
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
            ], f"Invalid particle {particle}"
        return self


class ConstructorConfig(BaseSettings):
    """Configuration settings for the geometry constructor."""

    input_geom: Annotated[str, StringConstraints(to_lower=True)] = Field(
        default="custom", description="gdml or custom"
    )
    gdml_file: str = Field(default="", description="GDML file to be used")
    mag_file: str = Field(
        default="",
        description="File containing the magnetic field as a csv with 7 columns: Bx, By, Bz, altitude, latitude, longitude and date",
    )
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

    density_profile: str = Field(
        default="",
        description="File containing the density/temperature profile at different altitudes",
    )

    @model_validator(mode="after")
    def validate_data(self) -> "ConstructorConfig":
        """Validate the data in the ConstructorConfig."""
        assert self.input_geom in ["gdml", "custom"]
        assert self.geometry in ["flat", "curved"]
        return self


class Config(BaseSettings):
    """Configuration settings for the simulation."""

    # Allow the configuration to be parsed from the command line
    model_config = SettingsConfigDict(cli_parse_args=True)
    # Random seed from the current time if not provided
    random_seed: int = Field(
        default_factory=lambda: int(time.time()),
        gt=0,
        description="Random seed for reproducibility. If not provided, it will be set to the current time",
    )
    num_processes: int = Field(
        default=1, gt=0, description="Number of processes to use for simulation"
    )
    logger_level: Annotated[str, StringConstraints(to_upper=True)] = Field(
        default="INFO", description="Logger level"
    )
    generator: GeneratorConfig = GeneratorConfig()
    constructor: ConstructorConfig = ConstructorConfig()
    macro_files: tuple[str, ...] | str = Field(description="Macro files to be executed")
    save_dir: str = Field(description="Directory to save the output files")

    @model_validator(mode="after")
    def validate_data(self) -> "Config":
        """Validate the data in the Config."""
        if isinstance(self.macro_files, str):
            assert pathlib.Path(
                self.macro_files
            ).is_file(), f"Macro file {self.macro_files} not found"
        else:
            for macro_file in self.macro_files:
                assert pathlib.Path(
                    macro_file
                ).is_file(), f"Macro file {macro_file} not found"
        assert self.logger_level in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ], f"Invalid logger level {self.logger_level}"
        if self.constructor.input_geom == "gdml":
            assert pathlib.Path(
                self.constructor.gdml_file
            ).is_file(), f"GDML File {self.constructor.gdml_file} not found"
        assert pathlib.Path(
            self.constructor.mag_file
        ).is_file(), f"Magnetic field file {self.constructor.mag_file} not found"
        assert pathlib.Path(
            self.constructor.density_profile
        ).is_file(), (
            f"Density profile file {self.constructor.density_profile} not found"
        )
        return self
