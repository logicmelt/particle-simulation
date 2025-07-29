Parameters can be introduced as command line arguments or through a configuration file in JSON/YAML format ([additional_files/simulation_config.yaml](https://github.com/logicmelt/particle-simulation/blob/feature/input_parser/additional_files/simulation_config.yaml) for an example). 

Only three parameters are required to run a simulation: save_dir, macro_files and density_file. 

All available parameters are:

- save_dir (str, **Required**): Directory to save the output files.
- random_seed (int, Optional): Random seed for reproducibility. If not provided, it will be set to the current time.
- num_processes (int, Optional): Number of processes to use for simulation. Defaults to 1.
- macro_files (list[str] | str, **Required**): Macro files to be executed as a list or a single string. Order matters if more than one file.
- logger_level (str, Optional): Logger level ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]. Defaults to "INFO".
- particles_per_run (int, Optional): Number of particles to be generated per run. Defaults to 1.
- time_resolution (float, Optional): Time resolution in microseconds. This is used to: update magnetic field between simulation runs, change density profile when a new day starts and to define a timestamp for the output particles. Defaults to 1s.
- generator:
  - gen_type (str, Optional): Type of generator to use: gps or particle_gun. Defaults to gps.
  - n_events (int, Optional): Number of particles to be shoot at one invokation of GeneratePrimaryVertex() method for a particle gun (Same physical quantities). Defaults to 1.
  - energy (float, Optional): Energy of the primary particle in Gev (Only particle gun generator). Defaults to 100GeV.
  - particle (str, Optional): Type of primary particle to shoot in the particle gun generator. Defaults to proton.
  - position (list[float], Optional): Position of the primary particle in km (Particle gun generator). Distance with respect the center of the geometry. Defaults to (0, 0, 0)
  - direction (list[float], Optional): Direction of the momentum of the primary particle (Particle gun generator). Defaults to (0, 0, 1.)
- constructor:
  - input_geom (str, Optional): Read from a gdml file or construct the model from params: "gdml" or "custom". Defaults to custom.
  - gdml_file (str, Optional): Path to gdml file. Required if "gdml" is selected.
  - export_gdml (bool, Optional): Export the geometry to a GDML file. Defaults to False.
  - geometry (str, Optional): Type of geometry to be used: flat or curved. Defaults to flat.
  - earth_radius (str, Optional): Earth's radius in km. Required if curved geometry. Defaults to 6371.
  - atmos_size (float, Optional): Size of the atmosphere in km (arc lenght if curved geometry). Defaults to 100km.
  - atmos_height (float, Optional): Height of the atmosphere in km. Defaults to 70km.
  - atmos_comp (list[float | str], Optional): Composition of the atmosphere in %. Defaults to ("N", 70, "O", 27, "Ar", 3).
  - atmos_n_points (int, Optional): Number of points in the density profile. Defaults to 100.
  - density_profile:
    - density_file (str, **Required**): Path to the json file with the density profiles.
    - day_idx (int, Optional): Index of the day in the density file. Defaults to 0.
  - magnetic_field:
    - enabled (bool, Optional): Enable the magnetic field in the simulation. Defaults to True.
    - mag_source (str, Optional): Source of the magnetic field: "file" or "estimated" (from latitude, longitude and date). Defaults to file.
    - mag_file (str, Optional): File containing the magnetic field as a csv with 7 columns: Bx, By, Bz, altitude, latitude, longitude and date. Required if mag_source is file.
    - latitude (float, Optional): Latitude of the detector in decimal degrees (World Geodetic System 1984). Positive north equator and values between -90º to 90º. Defaults t 42.224º.
    - longitude (float, Optional): Longitude of the detector in decimal degrees (World Geodetic System 1984). Positive east of the prime meridian and values between -180º to 180º. Defaults to -8.716º.
    - mag_time (str, Optional): Date to get the magnetic field values. Format YYYY-MM-DD. Defaults to 2021-01-01.
  - sensitive_detectors:
    - enabled (bool, Optional): Enable sensitive detectors. Defaults to True.
    - altitude (list[float], Optional): Altitude of the sensitive detector in km. Defaults to [0.].
    - particles (list[str], Optional): List of particles that will be recorded in the sensitive detectors (if ["all"] all the particles will be recorded). Defaults to ["mu-"].
