import csv
import re
import json


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


def parse_raw_ebird_to_4lc(csv_path):
    """
    Takes the raw eBird axonomy csv (not Clements or combined eBird/Clements) and returns a dictionary of eBird 4 letter codes and either common or scientific names.
    Rules: https://help.ebird.org/customer/en/portal/articles/2667298-how-quick-entry-codes-are-created
    Note that there are collisions in 4 letter codes. This code does not attempt to disambiguate them.
    Args:
        csv_path (str): Path to the file to open.
    Returns:
        A dictionary, with the key being the common name, and the value being the 4 letter code.
    """
    common_name_map = {}
    raw_input = open_raw_csv_ebird(csv_path)
    for line in raw_input:
        if line['category'] == "species":
            name = line["primary_com_name"]
            scientific_name = line["sci_name"]
            common_four_letter_code = name_to_4lc(name)
            scienfitic_four_letter_code = name_to_4lc(scientific_name)
            common_name_map[name] = common_four_letter_code + scienfitic_four_letter_code

    # Stupid special case for two of the Yellow-rumped Warblers.
    common_name_map["Yellow-rumped Warbler (Myrtle)"] = ["YRWA", "MYWA"]
    common_name_map["Yellow-rumped Warbler (Audubon's)"] = ["YRWA", "AUWA"]
    return common_name_map


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


if __name__ == "__main__":
    fn = "eBird_Taxonomy_v2019.csv"
    common_name_mappings = parse_raw_ebird_to_4lc(fn)

    with open('common.json', 'w') as f:
        json.dump(common_name_mappings, f)
