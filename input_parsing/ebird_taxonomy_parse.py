import csv
import re
import json
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class Taxon:
    """
    Class to represent a single Taxon
    """
    common_name: str
    scientific_name: str
    species_code: str
    short_codes: list

def open_raw_csv_ebird(csv_path):
    """
    Opens a raw csv file and parses it into a list of CSV lines.
    Args:
        csv_path (str): Path to the file to open.
    Returns:
        A list of lists, where each sublist is a line from the opened CSV file.
    """
    output = []
    with open(csv_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        raw_lines = list(csv_reader)
    header = raw_lines[0]
    keys = [x.lower() for x in header]
    for entry in raw_lines:
        e = {}
        for idx, field in enumerate(entry):
            e[keys[idx]] = field
        output += [e]
    return output


def name_to_4lc(name):
    """
    Converts a given name to a 4-letter code.
    Uses rules at: Rules: https://help.ebird.org/customer/en/portal/articles/2667298-how-quick-entry-codes-are-created
    The rules don't specifically say how to deal with names shorter than 4 letters, so the whole name is returned in this case.
    Note that eBird's own website does not support searching for some of the birds their own rules generate.
    The are also several ambiguities and edge cases in eBrid's rules for finding 4-letter-codes. A best guess at correct behaviour was taken.
    Args:
        name (str): name to convert to a 4-letter code
    Returns:
        A list of strings of 4 letters representing the ebird short code. Includes the base code as well as eBird's alternatives.
    """
    res = set()
    skipped_words = ["of", "and", "the"]

    # Normal handling of always splitting on a hyphen.
    split_name = tuple(re.split(r'[ -]', name))
    res.add(words_to_code(split_name))
    # Find the alternative for names longer than 4 words.
    if len(split_name) > 4:
        new_name = tuple(e for e in split_name if e not in skipped_words)
        res.add(words_to_code(new_name))
    # Handle the hyphenated split, which has very different rules.
    space_split = name.split(' ')
    if space_split[-1].count('-') == 1:
        last_hyphen = space_split[-1].split('-')
        hyphen_alt = space_split[0][0 : 2] + last_hyphen[0][0] + last_hyphen[1][0]
        res.add(hyphen_alt.upper())
    return list(res)


def words_to_code(split_name):
    """
    Takes a tuple of the words that make up a bird's name and returns the actual 4-letter code using eBird's rules.
    Args:
        split_name (tuple): Split words of a bird's name.
    Returns:
        A string of at most 4 characters containing the 4-letter-code for the given split name.
    """
    res = ''
    if len(split_name) == 1:
        res = split_name[0][0: 4].upper()
    elif len(split_name) == 2:
        res =(split_name[0][0: 2] + split_name[1][0: 2]).upper()
    elif len(split_name) == 3:
        res = (split_name[0][0: 1] + split_name[1][0: 1] + split_name[2][0: 2]).upper()
    elif len(split_name) >= 4:
        res = ''.join([split_name[x][0] for x in range(4)]).upper()
    return res


def taxonomy_parse(csv_path):
    """
    Parses the taxonomy csv into four-letter codes (both scientific, banding and common name),
        as well as eBird's unique codes and scientific + common names.
    Takes the raw eBird axonomy csv (not Clements or combined eBird/Clements).
    Note that there are collisions in 4 letter codes. This code does not attempt to disambiguate them.
    Args:
        csv_path (str): Path to the file to open.
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
    short_map = defaultdict(list)  # So that we can at least know of collisions rather than silently dropping them.

    raw_input = open_raw_csv_ebird(csv_path)
    for line in raw_input:
        if line['category'] == "species":
            common_name = line["primary_com_name"]
            scientific_name = line["sci_name"]
            common_four_letter_code = name_to_4lc(common_name)
            scientific_four_letter_code = name_to_4lc(scientific_name)
            species_code = line["species_code"]
            short_codes = common_four_letter_code + scientific_four_letter_code
            taxon = Taxon(common_name, scientific_name, species_code, short_codes)
            common_map[common_name] = taxon
            scientific_map[scientific_name] = taxon
            code_map[species_code] = taxon
            if common_name == "Yellow-rumped Warbler":
                short_codes += ["MYWA", "AUWA"]
            for x in short_codes:
                short_map[x] += [taxon]
    return common_map, scientific_map, code_map, short_map


if __name__ == "__main__":
    fn = "eBird_Taxonomy_v2019.csv"
    common, scientific, code, short = taxonomy_parse(fn)

    # Dump all the data with common names as the keys.
    with open('all_common.json', 'w') as f:
        common_name_mappings = {k: asdict(v) for k, v in common.items()}
        json.dump(common_name_mappings, f)
