from geant4_pybind import G4VUserDetectorConstruction, G4NistManager, G4State, G4Material, G4GDMLParser, G4VUserDetectorConstruction 
from geant4_pybind import G4Box, G4Sphere, G4LogicalVolume, G4PVPlacement, G4ThreeVector, G4MagneticField, G4FieldManager, G4SDManager, G4GenericMessenger
# Import units
from geant4_pybind import kelvin, kg, m3, perCent, radian, km, mm, tesla 
import pandas as pd
import numpy as np
import pathlib
# Sensitive detector
import particle_simulation.detector
# Logger
import logging

#TODO: Are the sensitive sensors too big? Worried that some particles might be created inside the sensitive detector and trigger
#TODO: Need to correct the altitude of the magnetic field given that with boxes we start at -height/2 and with spheres at earths_radius

class UniformMagneticField(G4MagneticField):
    def __init__(self, x: float, y: float, z: float):
        super().__init__()
        self.fbx = x * tesla
        self.fby = y * tesla
        self.fbz = z * tesla

        # define commands for this class
        # Define /B5/field command directory using generic messenger class
        self.fMessenger = G4GenericMessenger(self, "/B5/field/", "Field control")

        # fieldValue command
        valueCmd = self.fMessenger.DeclareMethodWithUnit("value", "tesla", self.SetFieldy,
                                                         "Set field strength.")
        # valueCmd.SetParameterName("field", True)

    def GetFieldValue(self, point, Bfield):
        Bfield[0] = self.fbx
        Bfield[1] = self.fby
        Bfield[2] = self.fbz
        # Alternatively you can return the field as an array
        # return [0, self.fBy, 0]

    def SetFieldy(self, val: float):
        self.fby = val

class DetectorConstruction(G4VUserDetectorConstruction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config["constructor"]
        self.save_dir = config["save_dir"]
        self.logic_volume = None
        self.sensitive_detector = None
        self.correction_factor = 0 # Correction factor to translate the altitude from the input positions to the actual positions within the geometry.
        # e.g: If the altitude is given as 0, it will be placed at -total_height/2 for a box and at earths_radius for a sphere

        # Logger
        self.logger = logging.getLogger("main")
        self.logger.info("Creating the detector construction")

        # Magnetic field 
        self.mag_field = self.parse_magnetic_field(self.config["mag_file"])

        # GDML parser
        self.gdml_parser = G4GDMLParser()

        if self.config["input"] == "gdml":
            self.gdml_file = self.config["gdml_file"]
            self.density_points = None
        else:
            # Get some parameters as attributes
            self.density_points = self.config["custom"]["atmos_n_points"]
            self.atmosphere_height = self.config["custom"]["atmos_height"] * km # Height of the atmosphere
            self.size = self.config["custom"]["atmos_size"] * km # Size of the world volume. Arc lenght for the sphere, side for the box
            self.shape = self.config["custom"]["geometry"] # Shape of the world volume

            # Export the geometry to a GDML file
            self.export_gdml = self.config["custom"].get("export_gdml", False)

            # Define the density, temperature and materials
            self.density, self.temp, _ = self.parse_density_temp_from_config()
            self.material, self.world_material = self.define_materials()

            # Lower and upper limits of the layers
            self.altitude_limits = np.zeros((self.density_points,2), dtype=float)

    def Construct(self):
        # TODO: Reading from GDML files is a pain in the back. If the GDML file is generated using this package we are ok,
        # otherwise we need to check the order and altitude so that we can associate the correct value of the magnetic field.
        
        # Construct the geometry
        if self.config["input"] == "gdml":
            # Load the geometry from a GDML file
            self.gdml_parser.Read(self.gdml_file)
            # The number of layers is the number of daughters of the world volume
            self.density_points = self.gdml_parser.GetWorldVolume().GetLogicalVolume().GetNoDaughters()
            world_volume = self.gdml_parser.GetWorldVolume()

            # Get the logical volumes of the layers
            self.logic_volume = np.zeros(self.density_points, dtype=object)
            for i in range(self.density_points):
                self.logic_volume[i] = world_volume.GetLogicalVolume().GetDaughter(i).GetLogicalVolume()

            return world_volume
        
        # Define the world volume
        if self.shape == "flat":
            world_volume, logic_volume = self.construct_flat_world()
        else:
            world_volume, logic_volume = self.construct_spherical_world()
        
        # Export the geometry to a GDML file
        if self.export_gdml:
            outputPath = pathlib.Path(self.save_dir) / "geometry.gdml"
            if outputPath.exists():
                outputPath.unlink()
            self.gdml_parser.Write(str(outputPath), world_volume)
            self.logger.info(f"Exported the geometry to {outputPath}/geometry.gdml")
            # We want to export it once, not every time the Construct method is called
            self.export_gdml = False

        self.logic_volume = logic_volume
        return world_volume
    
    def ConstructSDandField(self):
        #TODO: Several sensitive detectors might be problematic if all of them have to write files. Too much i/o
        # Add sensitive detectors and magnetic fields if any
        if self.mag_field is not None:
            self.logger.info("Adding the magnetic field")
            # Correct the altitude of the magnetic field
            self.mag_field[:,3] += self.correction_factor
            # Add the magnetic field to the layers
            for i in range(self.density_points):
                # Get the altitude of the layer
                altitude = (self.altitude_limits[i][0] + self.altitude_limits[i][1]) / 2
                # Search for the magnetic field at that altitude
                chosen_mag = self.mag_field[np.argmin(np.abs(self.mag_field[:,3] - altitude))]
                self.logger.debug(f"At layer {i} (altitude: {altitude}) adding magnetic field from altitude {chosen_mag[3]}")
                # Create the magnetic field
                magField = UniformMagneticField(chosen_mag[0], chosen_mag[1], chosen_mag[2])
                locField = G4FieldManager()
                locField.CreateChordFinder(magField)
                locField.SetDetectorField(magField)
                # Add the magnetic field to the logic volume
                self.logic_volume[i].SetFieldManager(locField, True)

        if self.sensitive_detector is not None:
            sdManager = G4SDManager.GetSDMpointer()
            for i in range(len(self.sensitive_detector)):
                sensitive_det = particle_simulation.detector.SensDetector(self.config, "sensitive_detector_" + str(i))
                sdManager.AddNewDetector(sensitive_det)
                self.sensitive_detector[i].SetSensitiveDetector(sensitive_det)

    def parse_magnetic_field(self, mag_file: str):
        # Parse the magnetic field from a file
        if mag_file == "None":
            self.logger.info("No magnetic field file provided")
            return
        else:
            self.logger.info(f"Reading the magnetic field from {mag_file}")
            open_csv = pd.read_csv(mag_file)
            # Transforms the values from nT to Tesla
            open_csv[["x", "y", "z"]] = open_csv[["x", "y", "z"]] * 1e-9
            # And the km column using the geant4 System of units
            open_csv["altitude"] = open_csv["altitude"] * km
            # Print back the magnetic field and the altitude
            return np.array(open_csv[["x", "y", "z", "altitude"]])

    def construct_flat_world(self):
        # Construct a flat world volume including all the layers of the atmosphere
        solidWorld = G4Box("solidWorld", self.size / 2, self.size / 2, self.atmosphere_height / 2)
        logicWorld = G4LogicalVolume(solidWorld, self.world_material, "logicWorld")
        physWorld = G4PVPlacement(None, G4ThreeVector(), logicWorld, "physWorld", None , False, 0, True)
        
        # The correction factor for a flat world is the altitude of the world volume over 2
        self.correction_factor = -self.atmosphere_height / 2

        # Construct the layers of the atmosphere
        solidAtmos = np.zeros(self.density_points, dtype=object)
        logicAtmos = np.zeros(self.density_points, dtype=object)
        # Remember that G4Box inputs are half the size of the box
        box_height = self.atmosphere_height / self.density_points / 2
        self.logger.debug(f"Creating {self.density_points} layers of the atmosphere for a total height of {self.atmosphere_height} assuming flat world.")

        for i in range(self.density_points):
            solidAtmos[i] = G4Box("solidAtmos_" + str(i), 
                                  self.size / 2 , 
                                  self.size / 2, 
                                  box_height)
            logicAtmos[i] = G4LogicalVolume(solidAtmos[i], 
                                            self.material[i], 
                                            "logicAtmos_" + str(i))
            # Add the values of the altitude limits
            self.altitude_limits[i] = [i * self.atmosphere_height / self.density_points + self.correction_factor, 
                                        i * self.atmosphere_height / self.density_points + 2*box_height + self.correction_factor]
            self.logger.debug(f"Creating atmos layer {i} with altitude limits {self.altitude_limits[i][0]} and {self.altitude_limits[i][1]}.")
            self.logger.debug(f"Layers size is {box_height}.")
            self.logger.debug(f"Layer centered at {i * self.atmosphere_height / self.density_points + box_height + self.correction_factor}.")
            G4PVPlacement(None, 
                          G4ThreeVector(0, 0, i * self.atmosphere_height / self.density_points + box_height + self.correction_factor), 
                          logicAtmos[i], 
                          "physAtmos_" + str(i), 
                          logicWorld, 
                          False, 
                          i, 
                          True)

        # Construct the sensitive detectors if any
        if self.config["sensitive_detectors"].get("enabled", False):
            detectors_alt = np.array(self.config["sensitive_detectors"]["altitude"]) * km + self.correction_factor
            n_detectors = len(detectors_alt)

            # First we need to identify in which layer the detectors are
            detectors_layer = np.zeros(n_detectors, dtype=int)
            for i in range(n_detectors):
                for j in range(self.density_points):
                    if detectors_alt[i] >= self.altitude_limits[j][0] and detectors_alt[i] <= self.altitude_limits[j][1]:
                        detectors_layer[i] = j
                        break

            # Now we can create the sensitive detectors
            logicDetector = np.zeros(n_detectors, dtype=object)
            solidDetector = np.zeros(n_detectors, dtype=object)
            detector_size = min(10*mm, self.atmosphere_height / self.density_points / 10) # 10mm or 1/10 of the layer height 
            for i in range(n_detectors):
                self.logger.debug(f"Creating sensitive detector at altitude {detectors_alt[i]} in layer {detectors_layer[i]}.")
                self.logger.debug(f"Detector size is {detector_size}.")

                solidDetector[i] = G4Box("solidDetector_" + str(i), self.size / 2, self.size / 2, detector_size / 2)
                logicDetector[i] = G4LogicalVolume(solidDetector[i], self.material[detectors_layer[i]], "logicDetector_" + str(i))
                # The sensitive detector will be a daughter of the layer where it is located
                # Therefore, the placement is relative to the layer and we need to ensure that the detector fits in the layer

                # Layer limits in local coordinates
                upper_lim = box_height
                layer_center = self.altitude_limits[detectors_layer[i]][0] + box_height
                lower_lim = -box_height 

                # The altitude of the detector is the altitude of the layer plus the distance to the limit
                detector_position = detectors_alt[i] - layer_center
                # Check if the detector fits in the layer
                if detector_position + detector_size / 2 > upper_lim:
                    detector_position = (upper_lim - detector_size / 2 )
                elif detector_position - detector_size / 2 < lower_lim:
                    detector_position += detector_size / 2

                self.logger.debug(f"Detector position is {detector_position} in local coordinates.")

                G4PVPlacement(None, 
                              G4ThreeVector(0, 0, detector_position), 
                              logicDetector[i], 
                              "physDetector_" + str(i), 
                              logicAtmos[detectors_layer[i]], 
                              False, 
                              i, 
                              True)

            # Add the sensitive detectors to the attribute
            self.sensitive_detector = logicDetector

        return physWorld, logicAtmos
    
    def construct_spherical_world(self):
        # Earth radius
        earth_rad = self.config["custom"]["earth_radius"] * km
        # Get the angle to create the spherical sector
        angle_sph = self.size / earth_rad * radian

        # The correction factor in a spherical world is the radius of the earth
        self.correction_factor = earth_rad

        # Create the world volume
        solidWorld = G4Sphere("solidWorld", self.correction_factor, self.correction_factor + self.atmosphere_height, 0, 2*np.pi*radian, 0, angle_sph)
        logicWorld = G4LogicalVolume(solidWorld, self.world_material, "logicWorld")
        physWorld = G4PVPlacement(None, G4ThreeVector(0, 0, 0), logicWorld, "physWorld", None , False, 0, True)

        # Construct the layers of the atmosphere
        solidAtmos = np.zeros(self.density_points, dtype=object)
        logicAtmos = np.zeros(self.density_points, dtype=object)
        self.logger.debug(f"Creating {self.density_points} layers of the atmosphere for a total height of {self.atmosphere_height} assuming curved world.")
        
        for i in range(self.density_points):
            solidAtmos[i] = G4Sphere("solidAtmos_" + str(i), 
                                    self.correction_factor + i * self.atmosphere_height / self.density_points, 
                                    self.correction_factor + (i + 1) * self.atmosphere_height / self.density_points, 
                                    0, 2*np.pi*radian, 0, angle_sph)
            logicAtmos[i] = G4LogicalVolume(solidAtmos[i], 
                                            self.material[i], 
                                            "logicAtmos_" + str(i))

            # Add the values of the altitude limits
            self.altitude_limits[i] = [self.correction_factor + i * self.atmosphere_height / self.density_points, 
                                        self.correction_factor + (i + 1) * self.atmosphere_height / self.density_points]
            self.logger.debug(f"Creating atmos layer {i} with altitude limits {self.altitude_limits[i][0]} and {self.altitude_limits[i][1]}.")
            self.logger.debug(f"Layers {i} size is {self.atmosphere_height / self.density_points}.")
            G4PVPlacement(None, 
                          G4ThreeVector(0, 0, 0), 
                          logicAtmos[i], 
                          "physAtmos_" + str(i), 
                          logicWorld, 
                          False, 
                          i, 
                          True)
            
        # Construct the sensitive detectors if any
        if self.config["sensitive_detectors"].get("enabled", False):
            detectors_alt = np.array(self.config["sensitive_detectors"]["altitude"]) * km + self.correction_factor
            n_detectors = len(detectors_alt)

            # First we need to identify in which layer the detectors are
            detectors_layer = np.zeros(n_detectors, dtype=int)
            for i in range(n_detectors):
                for j in range(self.density_points):
                    if detectors_alt[i] >= self.altitude_limits[j][0] and detectors_alt[i] <= self.altitude_limits[j][1]:
                        detectors_layer[i] = j
                        break

            # Now we can create the sensitive detectors
            logicDetector = np.zeros(n_detectors, dtype=object)
            solidDetector = np.zeros(n_detectors, dtype=object)
            detector_size = min(10*mm, self.atmosphere_height / self.density_points / 10) # 10mm or 1/10 of the layer height 
            for i in range(n_detectors):
                self.logger.debug(f"Creating sensitive detector at altitude {detectors_alt[i]} in layer {detectors_layer[i]}.")
                self.logger.debug(f"Detector size is {detector_size}.")
                
                # Get the upper and lower layer limits
                upper_lim = self.altitude_limits[detectors_layer[i]][1]

                # The altitude of the detector is the altitude of the layer plus the detector size if it fits
                if detectors_alt[i] + detector_size <= upper_lim:
                    chosen_alt = detectors_alt[i]
                else:
                    chosen_alt = upper_lim - detector_size

                solidDetector[i] = G4Sphere("solidDetector_" + str(i), 
                                    chosen_alt, 
                                    chosen_alt + detector_size, 
                                    0, 2*np.pi*radian, 0, angle_sph)
                logicDetector[i] = G4LogicalVolume(solidDetector[i], self.material[detectors_layer[i]], "logicDetector_" + str(i))
                # The sensitive detector will be a daughter of the layer where it is located
                # Therefore, the placement is relative to the layer and we need to ensure that the detector fits in the layer

                # Position of the detector in local coordinates is easy, it's an sphere centered at (0,0,0)
                G4PVPlacement(None, 
                              G4ThreeVector(0, 0, 0), 
                              logicDetector[i], 
                              "physDetector_" + str(i), 
                              logicAtmos[detectors_layer[i]], 
                              False, 
                              i, 
                              True)

            # Add the sensitive detectors to the attribute
            self.sensitive_detector = logicDetector


        return physWorld, logicAtmos

    def define_materials(self):
        # Define materials from the config file using the Nist manager
        nist_manager = G4NistManager.Instance()
        # The world material is air
        world_material = nist_manager.FindOrBuildMaterial("G4_AIR")

        comp = self.config["custom"]["atmos_comp"]
        # Get the material from the Nist manager
        elem = np.zeros((len(comp) // 2,2), dtype=object)
        for i in range(0, len(comp), 2):
            elem[i // 2] = [nist_manager.FindOrBuildElement(comp[i]), comp[i + 1] * perCent]

        # Create the material
        mat = np.zeros(self.density_points, dtype=object)

        for i in range(self.density_points):
            mat[i] = G4Material("G4_Air_" + str(i), self.density[i] * kg/m3, len(comp) // 2, state = G4State.kStateGas, temp = self.temp[i] * kelvin)
        
        # Add the elements to the material
        for i in range(self.density_points):
            for j in range(len(elem)):
                mat[i].AddElement(elem[j][0], elem[j][1])

        return mat, world_material

    def parse_density_temp_from_config(self):
        # TODO: We are using only ONE day from the dataset for the density and temperature
        # TODO: Add different interpolation methods for the density and temperature
        # Parse the density and temperature from the config file
        if self.config["custom"]["atmos_density"] == "from_file":
            # Read the density and temperature profile from a file
            file_path = self.config["custom"]["atmos_from_file"]
            df = pd.read_csv(file_path)
            # Get the height, temperature and density
            height = np.array(df["Height/km"]) * km
            temp = np.array(df["T/K"])
            density = np.array(df["rho/(kg/m3)"])

            # Interpolate the density and temperature to the height of the atmosphere
            inter_height = np.linspace(0, self.atmosphere_height, self.density_points)
            density = np.interp(inter_height, height, density)
            temp = np.interp(inter_height, height, temp)

            return density, temp, inter_height
        
        else:
            self.logger.error("Only 'from_file' is supported for 'atmos_density' in the config file.")
            raise NotImplementedError("Only 'from_file' is supported for 'atmos_density' in the config file.")


