import sys
sys.path.append("../")

from fuzzywuzzy import fuzz, process
import re
import unicodedata as ud


def fuzzy_search(search_term, search_set, score_type="ratio", score_cutoff=100):
    """
    Does fuzzy searching over a set of things to search over based on different scoring metrics and takes the top scoring item.
    Args:
        search_term (str): Term to search for. Ideally should be the same type as set uses.
        search_set (dict): Taxonomy to parse, from ebird_taxonomy_parse.taxonomy_parse().
        score_type (str, optional): One of "ratio", "partial", "token", "set", "partial_set", "partial_sort".
            These map to the fuzzywuzzy.fuzz functions of ratio(), partial_ratio(), token_sort_ratio() token_set_ratio(), partial_token_set_ratio() and partial_token_sort_ratio().
            Defaults to "ratio".
        score_cutoff (int, optional): Cutoff of how well a match needs to score to be included in the results. Defaults to 100, or perfect (non-whitespace) match.
    Returns:
        dict: A {"score": best_score_int, "result": ["results"]} dictionary.
    """
    scorers = {
        "partial": fuzz.partial_ratio,
        "token": fuzz.token_sort_ratio,
        "set": fuzz.token_set_ratio,
        "partial_set": fuzz.partial_token_set_ratio,
        "partial_sort": fuzz.partial_token_sort_ratio,
        "ratio": fuzz.ratio,
    }
    scorer = scorers[score_type]
    res = process.extractWithoutOrder(search_term, search_set.keys(), scorer=scorer, score_cutoff=score_cutoff)
    return list(res)

def word_start_search(search_term, search_set):
    """
    Search that finds any instances of the search term in the search set only when it occurs at the start of words.
    The way this search works is that "Owl" will return things like "Barred Owl", "Mountain Scops-Owl" and "Collared Owlet" and not "Greater Yellowlegs".
        But this also means that "Grouse" will return "Greater Sage-Grouse", "Sooty Grouse" but not "Spotted Sandgrouse".

    Args:
        search_term (str): Term to search for. Ideally should be the same type as set uses.
        search_set (dict): Taxonomy to parse, from ebird_taxonomy_parse.taxonomy_parse().
    Returns:
        list: All matching search strings from search_set.
    """
    results = []
    search_terms = normalize_to_ascii(search_term).lower()
    search_terms = re.split("[ -]", search_terms)

    # Matching start of string or ' ' or '-' before the first search term.
    # This is so that a search of Omao doesn't match Olomao, but Chickadee does match Boreal Chickadee.
    regex = f"(^|[ -]){search_terms[0]}"
    regex += ''.join([f".*[ -]{x}" for x in search_terms[1 : ]])
    r = re.compile(regex)
    print(r)

    for x in search_set.keys():
        name = x
        if not x.isascii():
            x = normalize_to_ascii(x)
        x = x.lower()
        res = re.search(r, x)
        if res:
            results += [name]
    return results


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
