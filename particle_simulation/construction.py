from geant4_pybind import (
    G4VUserDetectorConstruction,
    G4NistManager,
    G4State,
    G4Material,
    G4GDMLParser,
    G4VUserDetectorConstruction,
    G4doubleVector,
    G4VPhysicalVolume,
)
from geant4_pybind import (
    G4Box,
    G4Sphere,
    G4LogicalVolume,
    G4PVPlacement,
    G4ThreeVector,
    G4RotationMatrix,
    G4MagneticField,
    G4FieldManager,
    G4SDManager,
    G4GenericMessenger,
)

# Import units
from geant4_pybind import kelvin, kg, m3, perCent, radian, km, mm, tesla

from particle_simulation.config import Config, MagneticFieldConfig
from pygeomag import GeoMag
import pandas as pd
import numpy as np
import json

# Sensitive detector
import particle_simulation.detector

# Logger
import logging

# TODO: Are the sensitive sensors too big? Worried that some particles might be created inside the sensitive detector and trigger
# TODO: Need to correct the altitude of the magnetic field given that with boxes we start at -height/2 and with spheres at earths_radius
# TODO: Reading from GDML files is a pain in the back. If the GDML file is generated using this package we are ok,
# otherwise we need to check the order and altitude so that we can associate the correct value of the magnetic field.
# TODO: Several sensitive detectors might be problematic if all of them have to write files. Too much i/o
# TODO: Add different interpolation methods for the density and temperature


class UniformMagneticField(G4MagneticField):
    def __init__(self, x: float, y: float, z: float) -> None:
        """Creates a uniform magnetic field in cartesian coordinates.

        Args:
            x (float): x component of the magnetic field in Tesla.
            y (float): y component of the magnetic field in Tesla.
            z (float): z component of the magnetic field in Tesla.
        """
        super().__init__()
        self.fbx = x * tesla
        self.fby = y * tesla
        self.fbz = z * tesla

        # define commands for this class
        # Define /B5/field command directory using generic messenger class
        self.fMessenger = G4GenericMessenger(self, "/B5/field/", "Field control")

        # fieldValue command
        valueCmd = self.fMessenger.DeclareMethodWithUnit(
            "value", "tesla", self.SetFieldy, "Set field strength."
        )
        # valueCmd.SetParameterName("field", True)

    def GetFieldValue(self, Point: G4doubleVector, Bfield: list[float]) -> None:
        """Get the magnetic field at a given point.

        Args:
            Point (G4doubleVector): The point where the field is calculated.
            Bfield (list[float]): The magnetic field at the given point.
        """
        Bfield[0] = self.fbx
        Bfield[1] = self.fby
        Bfield[2] = self.fbz
        # Alternatively you can return the field as an array
        # return [0, self.fBy, 0]

    def SetFieldy(self, val: float) -> None:
        """Set the y component of the magnetic field.

        Args:
            val (float): The value of the y component of the magnetic field in Tesla.
        """
        self.fby = val


class DetectorConstruction(G4VUserDetectorConstruction):
    def __init__(self, config_pyd: Config, process_num: int) -> None:
        """Constructs the geometry of the detector from the configuration file.

        Args:
            config (dict[str, Any]): The configuration file with the parameters of the detector.
            process_num (int): The process number. Used to tag the particles that reach the sensitive detectors.
        """
        super().__init__()
        self.config = config_pyd.constructor
        self.save_dir = config_pyd.save_dir
        self.process_num = process_num
        self.logic_volume: np.ndarray = np.array([])
        self.sensitive_detector: np.ndarray = np.array([])
        self.correction_factor: float = (
            0  # Correction factor to translate the altitude from the input positions to the actual positions within the geometry.
        )
        # e.g: If the altitude is given as 0, it will be placed at -total_height/2 for a box and at earths_radius for a sphere

        # Logger
        self.logger = logging.getLogger("main")
        self.logger.info("Creating the detector construction")

        # GDML parser
        self.gdml_parser = G4GDMLParser()

        if self.config.input_geom == "gdml":
            self.gdml_file = self.config.gdml_file
            self.density_points: int = 0
        else:
            # Get some parameters as attributes
            self.density_points = self.config.atmos_n_points
            self.atmosphere_height = (
                self.config.atmos_height * km
            )  # Height of the atmosphere
            self.size = (
                self.config.atmos_size * km
            )  # Size of the world volume. Arc lenght for the sphere, side for the box
            self.shape = self.config.geometry  # Shape of the world volume

            # Export the geometry to a GDML file
            self.export_gdml = self.config.export_gdml

            # Define the density, temperature and materials
            self.density, self.temp, self.inter_heights = (
                self.parse_density_temp_from_config()
            )
            self.material, self.world_material = self.define_materials()

            # Lower and upper limits of the layers
            self.altitude_limits = np.zeros((self.density_points, 2), dtype=float)

    def Construct(self) -> G4VPhysicalVolume:
        """Construct the geometry of the detector.

        Returns:
            G4VPhysicalVolume: The world volume of the detector.
        """
        # Construct the geometry
        if self.config.input_geom == "gdml":
            # Load the geometry from a GDML file
            self.gdml_parser.Read(str(self.gdml_file))
            # The number of layers is the number of daughters of the world volume
            self.density_points = (
                self.gdml_parser.GetWorldVolume().GetLogicalVolume().GetNoDaughters()
            )
            world_volume = self.gdml_parser.GetWorldVolume()

            # Get the logical volumes of the layers
            self.logic_volume = np.zeros(self.density_points, dtype=object)
            for i in range(self.density_points):
                self.logic_volume[i] = (
                    world_volume.GetLogicalVolume().GetDaughter(i).GetLogicalVolume()
                )

            return world_volume

        # Define the world volume
        if self.shape == "flat":
            world_volume, logic_volume = self.construct_flat_world()
        else:
            world_volume, logic_volume = self.construct_spherical_world()

        # Export the geometry to a GDML file
        if self.export_gdml:
            outputPath = self.save_dir / "geometry.gdml"
            if outputPath.exists():
                outputPath.unlink()
            self.gdml_parser.Write(str(outputPath), world_volume)
            self.logger.info(f"Exported the geometry to {outputPath}/geometry.gdml")
            # We want to export it once, not every time the Construct method is called
            self.export_gdml = False

        self.logic_volume = logic_volume
        return world_volume

    def ConstructSDandField(self) -> None:
        """Construct the sensitive detectors and magnetic fields if any."""
        # Add sensitive detectors and magnetic fields if any
        if self.config.magnetic_field.enabled:
            self.logger.info(
                f"Adding a magnetic field from: {self.config.magnetic_field.mag_source}"
            )
            # Get the magnetic field from a file or estimate it from position and a time
            mag_field = self.get_magnetic_field(self.config.magnetic_field)
            # Add the magnetic field to the layers
            for i in range(self.density_points):
                # Get the altitude of the layer
                altitude: float = (
                    self.altitude_limits[i][0] + self.altitude_limits[i][1]
                ) / 2
                self.logger.debug(
                    f"At layer {i} (altitude: {altitude}) adding magnetic field from "
                    f"altitude {self.inter_heights[i] + self.correction_factor}."
                )
                self.logger.debug("Magnetic field: " + str(mag_field[i]))
                # Create the magnetic field
                magField = UniformMagneticField(
                    mag_field[i, 0], mag_field[i, 1], mag_field[i, 2]
                )
                locField = G4FieldManager()
                locField.CreateChordFinder(magField)
                locField.SetDetectorField(magField)
                # Add the magnetic field to the logic volume
                self.logic_volume[i].SetFieldManager(locField, True)

        if self.sensitive_detector is not None:
            sdManager = G4SDManager.GetSDMpointer()
            for i in range(len(self.sensitive_detector)):
                # We add the correction factor to the sensitive detector so that we the z-axis is distance from the surface.
                sensitive_det = particle_simulation.detector.SensDetector(
                    self.config,
                    "sensitive_detector_" + str(i),
                    self.process_num,
                    self.correction_factor
                )
                sdManager.AddNewDetector(sensitive_det)
                self.sensitive_detector[i].SetSensitiveDetector(sensitive_det)

    def get_magnetic_field(self, mag_config: MagneticFieldConfig) -> np.ndarray:
        """Gets the magnetic field from a file or estimate it from position and a time.

        Args:
            mag_file (MagneticFieldConfig): Magnetic field configuration with a path to a file in csv format or the position in
                latitude-longitude coordinates (geodetic coordinates) and the date.

        Returns:
            np.ndarray: The magnetic field in cartesian coordinates and altitude.
        """
        # Parse the magnetic field from a file
        if mag_config.mag_source != "file":
            self.logger.info(
                f"Estimating magnetic field at latitude: {mag_config.latitude}º and longitude: {mag_config.longitude}º "
                f"on date: {mag_config.mag_time}"
            )
            gm = GeoMag()
            mag_field = np.zeros((self.density_points, 3))
            for i in range(self.density_points):
                result = gm.calculate(
                    glat=mag_config.latitude,
                    glon=mag_config.longitude,
                    alt=self.inter_heights[i] / km,
                    time=mag_config.decimal_year,
                )
                # Change to -z because the magnetic field is defined positive towards the center of the earth
                mag_field[i] = (
                    np.array([result.x, result.y, -result.z]) * 1e-9
                )  # nT to Tesla
            return mag_field
        else:
            self.logger.info(f"Reading the magnetic field from {mag_config.mag_file}")
            open_csv = pd.read_csv(mag_config.mag_file)
            # Transforms the values from nT to Tesla
            open_csv[["x", "y", "z"]] = open_csv[["x", "y", "z"]] * 1e-9
            # And the km column using the geant4 System of units
            open_csv["altitude"] = open_csv["altitude"] * km
            mag_field = np.array(open_csv[["x", "y", "z", "altitude"]])
            # Interpolate to the layers altitude
            new_x = np.interp(self.inter_heights, mag_field[:, 3], mag_field[:, 0])
            new_y = np.interp(self.inter_heights, mag_field[:, 3], mag_field[:, 1])
            new_z = np.interp(self.inter_heights, mag_field[:, 3], mag_field[:, 2])
            # Return the interpolated magnetic field:
            return np.array([new_x, new_y, new_z]).T

    def construct_flat_world(self) -> tuple[G4VPhysicalVolume, np.ndarray]:
        """Construct a flat world volume with layers of the atmosphere.

        Returns:
            tuple[G4VPhysicalVolume, np.ndarray]: The world volume and the logical volumes of the layers.
        """

        # Construct a flat world volume including all the layers of the atmosphere
        solidWorld = G4Box(
            "solidWorld", self.size / 2, self.size / 2, self.atmosphere_height / 2
        )
        logicWorld = G4LogicalVolume(solidWorld, self.world_material, "logicWorld")
        physWorld = G4PVPlacement(
            G4RotationMatrix(), G4ThreeVector(), logicWorld, "physWorld", None, False, 0, True  # type: ignore
        )

        # The correction factor for a flat world is the altitude of the world volume over 2
        self.correction_factor = -self.atmosphere_height / 2

        # Construct the layers of the atmosphere
        solidAtmos = np.zeros(self.density_points, dtype=object)
        logicAtmos = np.zeros(self.density_points, dtype=object)
        # Remember that G4Box inputs are half the size of the box
        box_height = self.atmosphere_height / self.density_points / 2
        self.logger.debug(
            f"Creating {self.density_points} layers of the atmosphere for a total height of {self.atmosphere_height} assuming flat world."
        )

        for i in range(self.density_points):
            solidAtmos[i] = G4Box(
                "solidAtmos_" + str(i), self.size / 2, self.size / 2, box_height
            )
            logicAtmos[i] = G4LogicalVolume(
                solidAtmos[i], self.material[i], "logicAtmos_" + str(i)
            )
            # Add the values of the altitude limits
            self.altitude_limits[i] = [
                i * self.atmosphere_height / self.density_points
                + self.correction_factor,
                i * self.atmosphere_height / self.density_points
                + 2 * box_height
                + self.correction_factor,
            ]
            self.logger.debug(
                f"Creating atmos layer {i} with altitude limits {self.altitude_limits[i][0]} and {self.altitude_limits[i][1]}."
            )
            self.logger.debug(f"Layers size is {box_height}.")
            self.logger.debug(
                f"Layer centered at {i * self.atmosphere_height / self.density_points + box_height + self.correction_factor}."
            )
            G4PVPlacement(
                G4RotationMatrix(),
                G4ThreeVector(
                    0,
                    0,
                    i * self.atmosphere_height / self.density_points
                    + box_height
                    + self.correction_factor,
                ),
                logicAtmos[i],
                "physAtmos_" + str(i),
                logicWorld,
                False,
                i,
                True,
            )

        # Construct the sensitive detectors if any
        if self.config.sensitive_detectors.enabled:
            detectors_alt = (
                np.array(self.config.sensitive_detectors.altitude) * km
                + self.correction_factor
            )
            n_detectors = len(detectors_alt)

            # First we need to identify in which layer the detectors are
            detectors_layer = np.zeros(n_detectors, dtype=int)
            for i in range(n_detectors):
                for j in range(self.density_points):
                    if (
                        detectors_alt[i] >= self.altitude_limits[j][0]
                        and detectors_alt[i] <= self.altitude_limits[j][1]
                    ):
                        detectors_layer[i] = j
                        break

            # Now we can create the sensitive detectors
            logicDetector = np.zeros(n_detectors, dtype=object)
            solidDetector = np.zeros(n_detectors, dtype=object)
            detector_size = min(
                10 * mm, self.atmosphere_height / self.density_points / 10
            )  # 10mm or 1/10 of the layer height
            for i in range(n_detectors):
                self.logger.debug(
                    f"Creating sensitive detector at altitude {detectors_alt[i]} in layer {detectors_layer[i]}."
                )
                self.logger.debug(f"Detector size is {detector_size}.")

                solidDetector[i] = G4Box(
                    "solidDetector_" + str(i),
                    self.size / 2,
                    self.size / 2,
                    detector_size / 2,
                )
                logicDetector[i] = G4LogicalVolume(
                    solidDetector[i],
                    self.material[detectors_layer[i]],  # type: ignore
                    "logicDetector_" + str(i),
                )
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
                    detector_position = upper_lim - detector_size / 2
                elif detector_position - detector_size / 2 < lower_lim:
                    detector_position += detector_size / 2

                self.logger.debug(
                    f"Detector position is {detector_position} in local coordinates."
                )

                G4PVPlacement(
                    G4RotationMatrix(),
                    G4ThreeVector(0, 0, detector_position),
                    logicDetector[i],
                    "physDetector_" + str(i),
                    logicAtmos[detectors_layer[i]],  # type: ignore
                    False,
                    i,
                    True,
                )

            # Add the sensitive detectors to the attribute
            self.sensitive_detector = logicDetector

        return physWorld, logicAtmos

    def construct_spherical_world(self) -> tuple[G4VPhysicalVolume, np.ndarray]:
        """Construct a spherical world volume with layers of the atmosphere.

        Returns:
            tuple[G4VPhysicalVolume, np.ndarray]: The world volume and the logical volumes of the layers.
        """
        # Earth radius
        earth_rad: float = self.config.earth_radius * km
        # Get the angle to create the spherical sector
        angle_sph: float = self.size / earth_rad * radian

        # The correction factor in a spherical world is the radius of the earth
        self.correction_factor = earth_rad

        # Create the world volume
        solidWorld = G4Sphere(
            "solidWorld",
            self.correction_factor,
            self.correction_factor + self.atmosphere_height,
            0,
            2 * np.pi * radian,
            0,
            angle_sph,
        )
        logicWorld = G4LogicalVolume(solidWorld, self.world_material, "logicWorld")
        physWorld = G4PVPlacement(
            G4RotationMatrix(), G4ThreeVector(0, 0, 0), logicWorld, "physWorld", None, False, 0, True  # type: ignore
        )

        # Construct the layers of the atmosphere
        solidAtmos = np.zeros(self.density_points, dtype=object)
        logicAtmos = np.zeros(self.density_points, dtype=object)
        self.logger.debug(
            f"Creating {self.density_points} layers of the atmosphere for a total height of {self.atmosphere_height} assuming curved world."
        )

        for i in range(self.density_points):
            solidAtmos[i] = G4Sphere(
                "solidAtmos_" + str(i),
                self.correction_factor
                + i * self.atmosphere_height / self.density_points,
                self.correction_factor
                + (i + 1) * self.atmosphere_height / self.density_points,
                0,
                2 * np.pi * radian,
                0,
                angle_sph,
            )
            logicAtmos[i] = G4LogicalVolume(
                solidAtmos[i], self.material[i], "logicAtmos_" + str(i)
            )

            # Add the values of the altitude limits
            self.altitude_limits[i] = [
                self.correction_factor
                + i * self.atmosphere_height / self.density_points,
                self.correction_factor
                + (i + 1) * self.atmosphere_height / self.density_points,
            ]
            self.logger.debug(
                f"Creating atmos layer {i} with altitude limits {self.altitude_limits[i][0]} and {self.altitude_limits[i][1]}."
            )
            self.logger.debug(
                f"Layers {i} size is {self.atmosphere_height / self.density_points}."
            )
            G4PVPlacement(
                G4RotationMatrix(),
                G4ThreeVector(0, 0, 0),
                logicAtmos[i],
                "physAtmos_" + str(i),
                logicWorld,
                False,
                i,
                True,
            )

        # Construct the sensitive detectors if any
        if self.config.sensitive_detectors.enabled:
            detectors_alt = (
                np.array(self.config.sensitive_detectors.altitude) * km
                + self.correction_factor
            )
            n_detectors = len(detectors_alt)

            # First we need to identify in which layer the detectors are
            detectors_layer = np.zeros(n_detectors, dtype=int)
            for i in range(n_detectors):
                for j in range(self.density_points):
                    if (
                        detectors_alt[i] >= self.altitude_limits[j][0]
                        and detectors_alt[i] <= self.altitude_limits[j][1]
                    ):
                        detectors_layer[i] = j
                        break

            # Now we can create the sensitive detectors
            logicDetector = np.zeros(n_detectors, dtype=object)
            solidDetector = np.zeros(n_detectors, dtype=object)
            detector_size = min(
                10 * mm, self.atmosphere_height / self.density_points / 10
            )  # 10mm or 1/10 of the layer height
            for i in range(n_detectors):
                self.logger.debug(
                    f"Creating sensitive detector at altitude {detectors_alt[i]} in layer {detectors_layer[i]}."
                )
                self.logger.debug(f"Detector size is {detector_size}.")

                # Get the upper and lower layer limits
                upper_lim = self.altitude_limits[detectors_layer[i]][1]

                # The altitude of the detector is the altitude of the layer plus the detector size if it fits
                if detectors_alt[i] + detector_size <= upper_lim:
                    chosen_alt = detectors_alt[i]
                else:
                    chosen_alt = upper_lim - detector_size

                solidDetector[i] = G4Sphere(
                    "solidDetector_" + str(i),
                    chosen_alt,
                    chosen_alt + detector_size,
                    0,
                    2 * np.pi * radian,
                    0,
                    angle_sph,
                )
                logicDetector[i] = G4LogicalVolume(
                    solidDetector[i],
                    self.material[detectors_layer[i]],  # type: ignore
                    "logicDetector_" + str(i),
                )
                # The sensitive detector will be a daughter of the layer where it is located
                # Therefore, the placement is relative to the layer and we need to ensure that the detector fits in the layer

                # Position of the detector in local coordinates is easy, it's an sphere centered at (0,0,0)
                G4PVPlacement(
                    G4RotationMatrix(),
                    G4ThreeVector(0, 0, 0),
                    logicDetector[i],
                    "physDetector_" + str(i),
                    logicAtmos[detectors_layer[i]],  # type: ignore
                    False,
                    i,
                    True,
                )

            # Add the sensitive detectors to the attribute
            self.sensitive_detector = logicDetector

        return physWorld, logicAtmos

    def define_materials(self) -> tuple[np.ndarray, G4Material]:
        """Define the materials of the atmosphere.

        Returns:
            tuple[np.ndarray, G4Material]: The materials of the layers and the world material.
        """
        # Define materials from the config file using the Nist manager
        nist_manager = G4NistManager.Instance()
        # The world material is air
        world_material = nist_manager.FindOrBuildMaterial("G4_AIR")

        comp = self.config.atmos_comp
        # Get the material from the Nist manager
        elem = np.zeros((len(comp) // 2, 2), dtype=object)
        for i in range(0, len(comp), 2):
            elem[i // 2] = [
                nist_manager.FindOrBuildElement(str(comp[i])),
                float(comp[i + 1]) * perCent,
            ]

        # Create the material
        mat = np.zeros(self.density_points, dtype=object)

        for i in range(self.density_points):
            mat[i] = G4Material(
                "G4_Air_" + str(i),
                self.density[i] * kg / m3,
                len(comp) // 2,
                state=G4State.kStateGas,
                temp=self.temp[i] * kelvin,
            )

        # Add the elements to the material
        for i in range(self.density_points):
            for j in range(len(elem)):
                mat[i].AddElement(elem[j][0], elem[j][1])

        return mat, world_material

    def parse_density_temp_from_config(
        self,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Parse the density and temperature from the configuration file.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray]: The density, temperature and height of the atmosphere layers interpolated from the file.
        """

        # Read the density and temperature profile from the json file
        with open(self.config.density_profile.density_file, "r") as f:
            data = json.load(f)
        # Choose the day to be used from the configuration
        data_day = data[str(self.config.density_profile.day_idx)]
        # Get the height, temperature and density
        height = np.array(data_day["altitude"]) * km
        temp = np.array(data_day["T"])
        density = np.array(data_day["density"])
        # Interpolate the density and temperature to the height of the atmosphere
        inter_height = np.linspace(0, self.atmosphere_height, self.density_points)
        density = np.interp(inter_height, height, density)
        temp = np.interp(inter_height, height, temp)

        return density, temp, inter_height
