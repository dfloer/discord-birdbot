import csv
import re
import json
from dataclasses import dataclass, asdict
from collections import defaultdict
import requests
import unicodedata as ud


@dataclass
class Taxon:
    """
    Class to represent a single Taxon
    """

    common_name: str
    scientific_name: str
    species_code: str
    short_codes: list
    scientific_code: str
    banding_code: str = ""


def open_raw_csv_ebird(csv_path):
    """
    Opens a raw csv file and parses it into a list of CSV lines.
    Args:
        csv_path (str): Path to the file to open.  If this is None or a blank string, use eBird's API to grab it.
    Returns:
        A list of lists, where each sublist is a line from the opened CSV file.
    """
    output = []
    if csv_path:
        with open(csv_path, "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            raw_lines = list(csv_reader)
    else:
        r = requests.get("https://api.ebird.org/v2/ref/taxonomy/ebird")
        csv_reader = csv.reader(r.text.split("\n"), delimiter=",")
        raw_lines = list(csv_reader)
    header = raw_lines[0]
    # the API and the CSV download have different header names, so we normalize them.
    r = {"PRIMARY_COM_NAME": "common_name", "SCI_NAME": "scientific_name"}
    keys = [x.lower() if x not in r.keys() else r[x] for x in header]
    for entry in raw_lines:
        # Of course some lines are blank. Why would they be well-formed CSVs?
        if not entry:
            continue
        e = {}
        for idx, field in enumerate(entry):
            e[keys[idx]] = field
        output += [e]
    return output


def name_to_4lc(name):
    """
    Converts a given name to a 4-letter code.
    Uses rules at: Rules: https://support.ebird.org/en/support/solutions/articles/48000960508-ebird-mobile-tips-tricks
    The rules don't specifically say how to deal with names shorter than 4 letters, so the whole name is returned in this case.
    Note that eBird's own website does not support searching for some of the birds their own rules generate.
    The are also several ambiguities and edge cases in eBrid's rules for finding 4-letter-codes. A best guess at correct behaviour was taken.
    For example, the current rules say to treat all hyphens as spaces, but for Eurasian Collared-Dove both EUCD (alternate 3-word split) and ECDO (normal 3-word rule).
    Results normalized to ascii.
    Args:
        name (str): name to convert to a 4-letter code
    Returns:
        A list of strings of 4 letters representing the ebird short code. Includes the base code as well as eBird's alternatives.
    """
    res = set()
    skipped_words = ["of", "and", "the"]

    # Normal handling of always splitting on a hyphen.
    split_name = tuple(re.split(r"[ -]", name))
    res.add(words_to_code(split_name))
    # Find the alternative for names longer than 4 words.
    if len(split_name) > 4:
        new_name = tuple(e for e in split_name if e not in skipped_words)
        res.add(words_to_code(new_name))
    # Handle the hyphenated split, which has very different rules.
    # Note that abc def-ghi should yield ABGJ
    # But acd-def ghi-jkl should be handled as a 4-word code, so ADGJ
    space_split = name.split(" ")
    if space_split[-1].count("-") == 1 and space_split[0].count("-") == 0:
        last_hyphen = space_split[-1].split("-")
        hyphen_alt = space_split[0][0:2] + last_hyphen[0][0] + last_hyphen[1][0]
        res.add(normalize_to_ascii(hyphen_alt.upper()))
    return list(res)


def words_to_code(split_name):
    """
    Takes a tuple of the words that make up a bird's name and returns the actual 4-letter code using eBird's rules.
    Result normalized to ascii.
    Args:
        split_name (tuple): Split words of a bird's name.
    Returns:
        A string of at most 4 characters containing the 4-letter-code for the given split name.
    """
    res = ""
    if len(split_name) == 1:
        res = split_name[0][0:4].upper()
    elif len(split_name) == 2:
        res = (split_name[0][0:2] + split_name[1][0:2]).upper()
    elif len(split_name) == 3:
        res = (split_name[0][0:1] + split_name[1][0:1] + split_name[2][0:2]).upper()
    elif len(split_name) >= 4:
        res = "".join([split_name[x][0] for x in range(4)]).upper()
    return normalize_to_ascii(res)


def taxonomy_parse(csv_path=""):
    """
    Parses the taxonomy csv into four-letter codes (both scientific, banding and common name),
        as well as eBird's unique codes and scientific + common names.
    Takes the raw eBird axonomy csv (not Clements or combined eBird/Clements).
    Note that there are collisions in 4 letter codes. This code does not attempt to disambiguate them.
    Args:
        csv_path (str): Path to the file to open. If this is None or a blank string, use eBird's API to grab it.
    Returns:
        4 dictionaries:
        1. key: each 4 letter code.
        2. key: ebird unique codes.
        3. key: common name.
        4. key:scientific name.
        With the values being an object containing the values associated with that key.
        Why do it this way? To make it easy to look things up by any of the 4 possible key types.
    """
    common_map = {}
    scientific_map = {}
    code_map = {}
    band_map = {}
    short_map = defaultdict(
        list
    )  # So that we can at least know of collisions rather than silently dropping them.
    raw_input = open_raw_csv_ebird(csv_path)
    for line in raw_input:
        if line["category"] == "species":
            common_name = line["common_name"]
            scientific_name = line["scientific_name"]
            species_code = line["species_code"]
            short_codes = name_to_4lc(common_name)
            scientific_code = name_to_4lc(scientific_name)
            try:
                banding_code = line["banding_codes"]
            # CSV doesn't have banding codes, so ignore it.
            except KeyError:
                banding_code = ""
            taxon = Taxon(
                common_name,
                scientific_name,
                species_code,
                short_codes,
                scientific_code,
                banding_code,
            )
            common_map[common_name] = taxon
            scientific_map[scientific_name] = taxon
            code_map[species_code] = taxon
            band_map[banding_code] = taxon
            # eBird supports these, so we are as well.
            if common_name == "Yellow-rumped Warbler":
                short_codes += ["MYWA", "AUWA"]
            for x in short_codes:
                short_map[x] += [taxon]
    return common_map, scientific_map, code_map, short_map, band_map


def normalize_to_ascii(s):
    """
    Normalizes a unicode string to the ascii representation of it.
    This may or may not produce sane results.
    Args:
        s (str): String to normalize.
    Returns:
        str: normalized string in ascii, no matter what.
    """
    return ud.normalize("NFKD", s).encode("ascii", "ignore").decode()


if __name__ == "__main__":
    fn = "eBird_Taxonomy_v2021.csv"
    common, scientific, code, short, band = taxonomy_parse(fn)

    # Dump all the data with common names as the keys.
    with open("all_common.json", "w") as f:
        common_name_mappings = {k: asdict(v) for k, v in common.items()}
        json.dump(common_name_mappings, f)
