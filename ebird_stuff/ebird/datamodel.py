from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class eBirdTaxonomy:
    def __init__(self, ebird_data, banding_data):
        self.ebird_data = ebird_data
        self.banding_data = banding_data
        self.short_names = [a for a in ebird_data.keys() if len(a) < 4]

    # ToDo: support other languages/taxonomies. For now, only English eBird is supported.

    def name_to_codes(self, name, mode):
        """
        Maps a given bird name to its eBird 4-letter code or its banding code.
        Args:
            name (str): Bird name to look up.
            mode (str): Mode to operate in.
            Current modes:
                - "single" which returns a single code
                - "banding" which returns a single banding code
                - "all" which returns all possible codes
                - "fuzzy" which does a fuzzy match to find a single result.

        Returns:
            dict: Dictionary of the form {"name": name, "short_codes": [results], "species_code": result}
                "short_codes": is the 4-letter code results list, and will contain 0 items if there was no match.
                "species_code": is a string containing the 6-character ebird code, or None if there was no match.
        """
        res = {
            "name": name,
            "short_codes": [],
            "species_code": None,
            "scientific_name": None,
        }
        if mode != "fuzzy":
            try:
                bird = self.ebird_data[name]
                band = self.banding_data[name]
            except KeyError:
                return res
            if mode == "banding":
                res["short_codes"] = [band]
            elif mode == "single":
                res["short_codes"] = [bird["short_codes"][0]]
            else:
                res["short_codes"] = bird["short_codes"]
            res["species_code"] = bird["species_code"]
            res["scientific_name"] = bird["scientific_name"]
        return res

    @classmethod
    def load_parsed_data(data_path=Path("input_parsing")):
        with open(data_path / "all_common.json", "r") as f:
            ebird_data = json.load(f)

        with open(data_path / "banding.json", "r") as f:
            banding_data = json.load(f)

        test = eBirdTaxonomy(ebird_data, banding_data)
        return test
