import os
import tarfile
import urllib.request
import tempfile
import hashlib
import argparse
import pathlib

# See https://github.com/HaarigerHarald/geant4_pybind/blob/main/source/datainit.py for the original code

DATASET_URL = "https://cern.ch/geant4-data/datasets"
DATASETS = [
    {
        "name": "G4NDL",
        "version": "4.7",
        "filename": "G4NDL",
        "envvar": "G4NEUTRONHPDATA",
        "md5sum": "b001a2091bf9392e6833830347672ea2",
    },
    {
        "name": "G4EMLOW",
        "version": "8.5",
        "filename": "G4EMLOW",
        "envvar": "G4LEDATA",
        "md5sum": "146d0625d8d39f294056e1618271bc46",
    },
    {
        "name": "PhotonEvaporation",
        "version": "5.7",
        "filename": "G4PhotonEvaporation",
        "envvar": "G4LEVELGAMMADATA",
        "md5sum": "81ff27deb23af4aa225423e6b3a06b39",
    },
    {
        "name": "RadioactiveDecay",
        "version": "5.6",
        "filename": "G4RadioactiveDecay",
        "envvar": "G4RADIOACTIVEDATA",
        "md5sum": "acc1dbeb87b6b708b2874ced729a3a8f",
    },
    {
        "name": "G4PARTICLEXS",
        "version": "4.0",
        "filename": "G4PARTICLEXS",
        "envvar": "G4PARTICLEXSDATA",
        "md5sum": "d82a4d171d50f55864e28b6cd6f433c0",
    },
    {
        "name": "G4PII",
        "version": "1.3",
        "filename": "G4PII",
        "envvar": "G4PIIDATA",
        "md5sum": "05f2471dbcdf1a2b17cbff84e8e83b37",
    },
    {
        "name": "RealSurface",
        "version": "2.2",
        "filename": "G4RealSurface",
        "envvar": "G4REALSURFACEDATA",
        "md5sum": "ea8f1cfa8d8aafd64b71fb30b3e8a6d9",
    },
    {
        "name": "G4SAIDDATA",
        "version": "2.0",
        "filename": "G4SAIDDATA",
        "envvar": "G4SAIDXSDATA",
        "md5sum": "d5d4e9541120c274aeed038c621d39da",
    },
    {
        "name": "G4ABLA",
        "version": "3.3",
        "filename": "G4ABLA",
        "envvar": "G4ABLADATA",
        "md5sum": "b25d093339e1e4532e31038653580ca6",
    },
    {
        "name": "G4INCL",
        "version": "1.2",
        "filename": "G4INCL",
        "envvar": "G4INCLDATA",
        "md5sum": "0a76df936839bb557dae7254117eb58e",
    },
    {
        "name": "G4ENSDFSTATE",
        "version": "2.3",
        "filename": "G4ENSDFSTATE",
        "envvar": "G4ENSDFSTATEDATA",
        "md5sum": "6f18fce8f217e7aaeaa3711be9b2c7bf",
    },
]
# Check if the data directory exists


def check_and_download(data_dir: pathlib.Path) -> None:
    """Check if the datasets are already in storage, if not, download them.

    Args:
        data_dir (pathlib.Path): Path to the data directory.
    """
    # From the list of datasets, check if they are already downloaded, if not, download them
    file_name = [
        (idx, data["name"] + data["version"]) for idx, data in enumerate(DATASETS)
    ]

    # Get a list of the files in the data directory
    files_data = [f.name for f in data_dir.iterdir()]

    # Check if the files are already downloaded
    for idx, file in file_name:
        if file not in files_data:
            download_dataset(DATASETS[idx], data_dir)
            print("Downloaded", file)


# From the git package, to be able to download the datasets, extract them and check the md5sum
def md5_check(file, md5_exp: str) -> bool:
    """Check the md5sum of a file.

    Args:
        file (str): The file to check.
        md5_exp (str): The expected md5sum.

    Returns:
        bool: True if the md5sum is correct, False otherwise.
    """
    with open(file, "rb") as f:
        md5_calc = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            md5_calc.update(chunk)
            chunk = f.read(8192)

        if md5_calc.hexdigest() == md5_exp:
            return True

    return False


def download_dataset(dataset: dict[str, str], directory: pathlib.Path) -> None:
    """Download a dataset from a link.

    Args:
        dataset (dict[str, str]): The dataset to download.
        directory (pathlib.Path): The directory to save the dataset.
    """

    if not directory.exists():
        # Create it
        directory.mkdir(parents=True)

    filename = dataset["filename"] + "." + dataset["version"] + ".tar.gz"
    url = DATASET_URL + "/" + filename

    print("Downloading data file:", url)
    temp = tempfile.mktemp()
    urllib.request.urlretrieve(url, temp)
    if not md5_check(temp, dataset["md5sum"]):
        print("MD5 check failed for", filename)
        os.remove(temp)
        return

    tar = tarfile.open(temp)
    tar.extractall(directory)
    tar.close()
    os.remove(temp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Geant4 datasets")
    parser.add_argument(
        "--data_dir",
        type=str,
        default="geant4_datasets",
        help="Directory to download the datasets",
    )
    args = parser.parse_args()
    data_dir = pathlib.Path(args.data_dir)
    # Check the data directory
    if not data_dir.exists():
        # Create it
        data_dir.mkdir()

    check_and_download(data_dir)
