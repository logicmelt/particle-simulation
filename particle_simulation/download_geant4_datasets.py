import os
import tarfile
import urllib.request
import tempfile
import sys
import shutil
import stat
import hashlib
import argparse

# See https://github.com/HaarigerHarald/geant4_pybind/blob/main/source/datainit.py for the original code

DATASET_URL = "https://cern.ch/geant4-data/datasets"
DATASETS = [
    {"name": "G4NDL",
     "version": "4.7",
     "filename": "G4NDL",
     "envvar": "G4NEUTRONHPDATA",
     "md5sum": "b001a2091bf9392e6833830347672ea2"},

    {"name": "G4EMLOW",
     "version": "8.5",
     "filename": "G4EMLOW",
     "envvar": "G4LEDATA",
     "md5sum": "146d0625d8d39f294056e1618271bc46"},

    {"name": "PhotonEvaporation",
     "version": "5.7",
     "filename": "G4PhotonEvaporation",
     "envvar": "G4LEVELGAMMADATA",
     "md5sum": "81ff27deb23af4aa225423e6b3a06b39"},

    {"name": "RadioactiveDecay",
     "version": "5.6",
     "filename": "G4RadioactiveDecay",
     "envvar": "G4RADIOACTIVEDATA",
     "md5sum": "acc1dbeb87b6b708b2874ced729a3a8f"},

    {"name": "G4PARTICLEXS",
     "version": "4.0",
     "filename": "G4PARTICLEXS",
     "envvar": "G4PARTICLEXSDATA",
     "md5sum": "d82a4d171d50f55864e28b6cd6f433c0"},

    {"name": "G4PII",
     "version": "1.3",
     "filename": "G4PII",
     "envvar": "G4PIIDATA",
     "md5sum": "05f2471dbcdf1a2b17cbff84e8e83b37"},

    {"name": "RealSurface",
     "version": "2.2",
     "filename": "G4RealSurface",
     "envvar": "G4REALSURFACEDATA",
     "md5sum": "ea8f1cfa8d8aafd64b71fb30b3e8a6d9"},

    {"name": "G4SAIDDATA",
     "version": "2.0",
     "filename": "G4SAIDDATA",
     "envvar": "G4SAIDXSDATA",
     "md5sum": "d5d4e9541120c274aeed038c621d39da"},

    {"name": "G4ABLA",
     "version": "3.3",
     "filename": "G4ABLA",
     "envvar": "G4ABLADATA",
     "md5sum": "b25d093339e1e4532e31038653580ca6"},

    {"name": "G4INCL",
     "version": "1.2",
     "filename": "G4INCL",
     "envvar": "G4INCLDATA",
     "md5sum": "0a76df936839bb557dae7254117eb58e"},

    {"name": "G4ENSDFSTATE",
     "version": "2.3",
     "filename": "G4ENSDFSTATE",
     "envvar": "G4ENSDFSTATEDATA",
     "md5sum": "6f18fce8f217e7aaeaa3711be9b2c7bf"}
]

def check_missing_datasets():
    missing_datasets = []
    for dataset in DATASETS:
        if dataset["envvar"] not in os.environ:
            missing_datasets.append(dataset)
    return missing_datasets