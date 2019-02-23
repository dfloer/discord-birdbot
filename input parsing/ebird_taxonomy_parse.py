import csv
import re


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


def parse_raw_ebird_to_4lc_common(csv_path):
    """
    Takes the raw eBird axonomy csv (not Clements or combined eBird/Clements) and returns a dictionary of eBird 4 letter codes and common names.
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
            common_name = line['primary_com_name']
            four_letter_code = common_name_to_4lc(common_name)
            common_name_map[common_name] = four_letter_code
    return common_name_map


def common_name_to_4lc(name):
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
    res = []
    skipped_words = ["of", "and", "the"]

    # Normal handling of always splitting on a hyphen.
    all_splits = set()
    normal_split = re.split(r' |-', name)
    all_splits.add(tuple(normal_split))
    # Don't split if the last two words are hyphenated.
    hyphen_split = re.findall(r"((?:(?:[^\s-]+-)+[^\s-]+$)|(?:[^\s-]+))", name)
    all_splits.add(tuple(hyphen_split))
    for split_name in all_splits:
        res += [words_to_code(split_name)]
        # Find the alternative for names longer than 4 words.
        if len(split_name) > 4:
            new_name = tuple(e for e in split_name if e not in skipped_words)
            res += [words_to_code(new_name)]
    return res



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
    fn = "eBird_Taxonomy_v2018_14Aug2018.csv"
    name_mappings = parse_raw_ebird_to_4lc_common(fn)



