from dbfread import DBF
import json


def load_dbf(filename):
    """
    Opens and returns s list representation of a dbf file.
    Args:
        filename (str): dbf file to open.
    Returns:
        List representation of the alpha codes zdbf file.
    """
    return DBF(filename, load=True)


def common_name_to_banding(filename):
    """
    Converts the banding code database file to a dictionary.
    Banding codes as per The Institute for Bird Populations downloaded from: http://www.birdpop.org/docs/misc/List18.zip
    Args:
        filename (str): dbf file to open.
    Returns:
        A dictionary of {"common name": "4 letter code"} pairs.
    """
    result = {}
    dbf_table = load_dbf(filename)
    for x in dbf_table:
        if x["SP"]:
            continue
        common_name = x["COMMONNAME"]
        banding_code = x["SPEC"]
        result[common_name] = banding_code
    return result


if __name__ == "__main__":
    dbf_filename = "LIST18.DBF"
    banding_mapping = common_name_to_banding(dbf_filename)
    with open('banding.json', 'w') as f:
        json.dump(banding_mapping, f)
