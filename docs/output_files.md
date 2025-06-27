Simulation output for the icos simulation is twofold:

- Aggregated data in time_resolution steps within a json file
- Individual muons per simulation as a csv file

The csv file has the following entries:

- EventID (int): ID of the proton that generated that particle (Within a process).
- TrackID (int): ID of the detected particle within a process.
- process_ID (int): ID of the process that generated the trigger. Only useful if several processes are used at the same time.
- Particle (str): Particle type.
- ParticleID (int): Particle ID from the Particle Data Group (PDG).
- px (float): Momentum of the muon along the x-axis in MeV.
- py (float): Momentum of the muon along the y-axis in MeV.
- pz (float): Momentum of the muon along the z-axis in MeV.
- x (float): x-coordinate where the particle reached the detector in mm.
- y (float): y-coordinate where the particle reached the detector in mm.
- z (float): z-coordinate where the particle reached the detector in mm.
- theta (float): Elevation angle in rads. Constrained between [0, pi/2].
- phi (float): Azimuthal angle in rads.
- time (float): Elapsed time between the original particle being shoot through the atmosphere and the generated particle reaching the detector.
- local_time (float): Elapsed time between the generation of the particle and reaching the detector.
- detector_type (str): Detector type, from the simulation it's always virtual.
- latitude (float): Latitude of the detector in decimal degrees (World Geodetic System 1984).
- longitude (float): Longitude of the detector in decimal degrees (World Geodetic System 1984).
- timestamp (float): Timestamp assigned to the particle for a unique ID tag (Needed for Influx).
- start_time (str): Start time in  YYYY-MM-DDTHH:MM:SS format.
- density_day_idx (int): Index of the density profile used for the simulation.
- run_ID (str): UUID assigned to the run.