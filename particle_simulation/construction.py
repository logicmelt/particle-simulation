from geant4_pybind import G4VUserDetectorConstruction, G4NistManager, G4State, G4Material, G4GDMLParser, G4VUserDetectorConstruction, G4Box, G4Sphere, G4LogicalVolume, G4PVPlacement, G4ThreeVector
# Import units
from geant4_pybind import kelvin, kg, m3, perCent, radian, km
import pandas as pd
import numpy as np
import pathlib

class DetectorConstruction(G4VUserDetectorConstruction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config["constructor"]
        self.save_dir = config["save_dir"]
        
        # GDML parser
        self.gdml_parser = G4GDMLParser()

        if self.config["input"] == "gdml":
            self.gdml_file = self.config["gdml_file"]
        else:
            # Get some parameters as attributes
            self.density_points = self.config["custom"]["atmos_n_points"]
            self.atmosphere_height = self.config["custom"]["atmos_height"] * km # Height of the atmosphere
            self.size = self.config["custom"]["atmos_size"] * km # Size of the world volume. Arc lenght for the sphere, side for the box
            self.shape = self.config["custom"]["geometry"] # Shape of the world volume

            # Export the geometry to a GDML file
            self.export_gdml = self.config["custom"].get("export_gdml", False)

            # Define the density, temperature and materials
            self.density, self.temp = self.parse_density_temp_from_config()
            self.material, self.world_material = self.define_materials()

    def Construct(self):
        # Construct the geometry
        if self.config["input"] == "gdml":
            # Load the geometry from a GDML file
            self.gdml_parser.Read(self.gdml_file)
            return self.gdml_parser.GetWorldVolume()
        
        # Define the world volume
        if self.shape == "flat":
            world_volume = self.construct_flat_world()
        else:
            world_volume = self.construct_spherical_world()
        
        # Export the geometry to a GDML file
        if self.export_gdml:
            outputPath = pathlib.Path(self.save_dir) / "geometry.gdml"
            if outputPath.exists():
                outputPath.unlink()
            self.gdml_parser.Write(str(outputPath), world_volume)
            # We want to export it once, not every time the Construct method is called
            self.export_gdml = False
        
        return world_volume

    def construct_flat_world(self):
        # Construct a flat world volume including all the layers of the atmosphere
        solidWorld = G4Box("solidWorld", self.size / 2, self.size / 2, self.atmosphere_height / 2)
        logicWorld = G4LogicalVolume(solidWorld, self.world_material, "logicWorld")
        physWorld = G4PVPlacement(None, G4ThreeVector(), logicWorld, "physWorld", None , False, 0, True)
        
        # Construct the layers of the atmosphere
        solidAtmos = np.zeros(self.density_points, dtype=object)
        logicAtmos = np.zeros(self.density_points, dtype=object)
        # Remember that G4Box inputs are half the size of the box
        box_height = self.atmosphere_height / self.density_points / 2

        for i in range(self.density_points):
            solidAtmos[i] = G4Box("solidAtmos_" + str(i), 
                                  self.size / 2 , 
                                  self.size / 2, 
                                  box_height)
            logicAtmos[i] = G4LogicalVolume(solidAtmos[i], 
                                            self.material[i], 
                                            "logicAtmos_" + str(i))
            G4PVPlacement(None, 
                          G4ThreeVector(0, 0, i * self.atmosphere_height / self.density_points + box_height - self.atmosphere_height / 2), 
                          logicAtmos[i], 
                          "physAtmos_" + str(i), 
                          logicWorld, 
                          False, 
                          i, 
                          True)
        
        return physWorld
    
    def construct_spherical_world(self):
        # Earth radius
        earth_rad = self.config["custom"]["earth_radius"] * km
        # Get the angle to create the spherical sector
        angle_sph = self.size / earth_rad * radian

        # Create the world volume
        solidWorld = G4Sphere("solidWorld", earth_rad, earth_rad + self.atmosphere_height, 0, 2*np.pi*radian, 0, angle_sph)
        logicWorld = G4LogicalVolume(solidWorld, self.world_material, "logicWorld")
        physWorld = G4PVPlacement(None, G4ThreeVector(0, 0, 0), logicWorld, "physWorld", None , False, 0, True)

        # Construct the layers of the atmosphere
        solidAtmos = np.zeros(self.density_points, dtype=object)
        logicAtmos = np.zeros(self.density_points, dtype=object)

        for i in range(self.density_points):
            solidAtmos[i] = G4Sphere("solidAtmos_" + str(i), 
                                    earth_rad + i * self.atmosphere_height / self.density_points, 
                                    earth_rad + (i + 1) * self.atmosphere_height / self.density_points, 
                                    0, 2*np.pi*radian, 0, angle_sph)
            logicAtmos[i] = G4LogicalVolume(solidAtmos[i], 
                                            self.material[i], 
                                            "logicAtmos_" + str(i))
            G4PVPlacement(None, 
                          G4ThreeVector(0, 0, 0), 
                          logicAtmos[i], 
                          "physAtmos_" + str(i), 
                          logicWorld, 
                          False, 
                          i, 
                          True)
            
        return physWorld

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
            height = np.array(df["Height/km"])
            temp = np.array(df["T/K"])
            density = np.array(df["rho/(kg/m3)"])

            # Interpolate the density and temperature to the height of the atmosphere
            density = np.interp(np.linspace(0, self.atmosphere_height, self.density_points), height, density)
            temp = np.interp(np.linspace(0, self.atmosphere_height, self.density_points), height, temp)

            return density, temp
        
        else:
            raise NotImplementedError("Only 'from_file' is supported for 'atmos_density' in the config file.")


