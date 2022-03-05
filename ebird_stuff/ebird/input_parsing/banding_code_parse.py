import csv
import json
import requests
import zipfile
from io import BytesIO, StringIO


def common_name_to_banding(filename, include_non_sp=False):
    """
    Converts the banding code CSV file to a dictionary.
    Banding codes as per The Institute for Bird Populations downloaded from: http://www.birdpop.org/docs/misc/IBPAOU.zip
    Args:
        filename (str): csv file to open.
        include_non_sp (bool, optional): Whether ot not to include non-species taxa, such as subspecies or morphs. Defaults to False.
    Returns:
        dict: A dictionary of {"common name": "4 letter code"} pairs.
    """
    result = {}
    if filename != "":
        with open(filename, "r") as csv_file:
            reader = list(csv.DictReader(csv_file))
    else:
        reader = download_csv()
    for row in reader:
        if row["SP"] and not include_non_sp:
            continue
        common_name = row["COMMONNAME"]
        banding_code = row["SPEC"]
        result[common_name] = banding_code
    return result


def download_csv():
    """
    Downloads the banding code CSV from Bird Pop.
    """
    url = "http://www.birdpop.org/docs/misc/IBPAOU.zip"
    r = requests.get(url)
    z = zipfile.ZipFile(BytesIO(r.content))
    fn = z.namelist()[0]
    # There should be a cleaner way to do this...
    unzipped = []
    for line in z.open(fn).readlines():
        unzipped += [line.decode("ascii").replace("\r", "").replace("\n", "")]
    reader = list(csv.DictReader(unzipped))
    return reader


if __name__ == "__main__":
    csv_filename = "IBP-AOS-LIST21.csv"
    banding_mapping = common_name_to_banding(csv_filename)
    with open("banding.json", "w") as f:
        json.dump(banding_mapping, f)
