import csv
import json


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
    with open(filename, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row["SP"] and not include_non_sp:
                continue
            common_name = row["COMMONNAME"]
            banding_code = row["SPEC"]
            result[common_name] = banding_code
    return result


if __name__ == "__main__":
    csv_filename = "list19p.csv"
    banding_mapping = common_name_to_banding(csv_filename)
    with open("banding.json", "w") as f:
        json.dump(banding_mapping, f)
