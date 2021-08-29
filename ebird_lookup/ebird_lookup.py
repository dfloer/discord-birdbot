from dataclasses import dataclass
import typesense
import meilisearch
from pprint import pprint
import json
from pathlib import Path


def get_data(data_path=Path("input_parsing")):
    with open(data_path / "all_common.json", "r") as f:
        ebird_data = json.load(f)

    with open(data_path / "banding.json", "r") as f:
        banding_data = json.load(f)

    test = eBirdTaxonomy(ebird_data, banding_data)
    return test


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
        res = {"name": name, "short_codes": [], "species_code": None}
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
        return res

    def on_get(req, res, mode, name):
        return {"k": "v"}


@dataclass
class TypeSenseSearch:
    api_key: str
    taxonomy: eBirdTaxonomy = None
    client: None = None
    host: str = "localhost"
    port: str = "8108"
    protocol: str = "http"
    timeout: int = 2

    def connect(self):
        self.client = typesense.Client(
            {
                "api_key": self.api_key,
                "nodes": [
                    {"host": self.host, "port": self.port, "protocol": self.protocol}
                ],
                "connection_timeout_seconds": self.timeout,
            }
        )

    def clean(self, name):
        """
        Typesense doesn't handle punctiation very well.
        - becomes a space, it's used as a word seperator.
        . and ' can be removed completely.
        """
        # return name.replace('-', ' ').replace('.', '').replace("'", '')
        return name

    def populate_taxonomy(self):
        """
        This probably only needs to be run once, unless the database goes poof.
        """
        if not self.taxonomy:
            raise PopulateTaxonomyError
        cr = self.client.collections.create(
            {
                "name": "taxonomy",
                "token_separators": ["-"],
                "symbols_to_index": [".", "'"],
                "fields": [
                    {"name": "common_name", "type": "string"},
                    {"name": "clean_name", "type": "string"},
                    {"name": "scientific_name", "type": "string"},
                    {"name": "species_code", "type": "string"},
                    {"name": "short_codes", "type": "string[]"},
                    {"name": "banding_code", "type": "string", "optional": True},
                ],
            }
        )

        for k, v in self.taxonomy.ebird_data.items():
            try:
                v["banding_code"] = self.taxonomy.banding_data[k]
            except KeyError:
                pass
            cn = v["common_name"]
            v["clean_name"] = self.clean(cn)
            self.client.collections["taxonomy"].documents.create(v)

    def search_name(self, name):
        cn = self.clean(name)
        params = {"q": cn, "query_by": "clean_name"}
        res = self.client.collections["taxonomy"].documents.search(params)
        return res["hits"]

    def search_code(self, code):
        params = {"q": code, "query_by": "short_codes"}
        res = self.client.collections["taxonomy"].documents.search(params)
        return res["hits"]

    def name_to_codes(self, name, mode="single"):
        res = {"name": name, "short_codes": [], "species_code": None}
        sr = self.search_name(name)
        # No results.
        if len(sr) == 0:
            return res
        data = sr[0]["document"]
        pprint(sr)
        print("match", sr[0]["text_match"])
        res["name"] = data["common_name"]
        if mode == "single":
            print("single")
            res["short_codes"] = [data["short_codes"][0]]
        else:
            print("double")
            res["short_codes"] = data["short_codes"]
        res["species_code"] = data["species_code"]
        return res

    def code_to_names(self, code):
        res = {"names": []}
        if len(code) not in (3, 4):
            return res
        code = code.upper()  # normalize code to upper case.
        sr = self.search_code(code)
        # No results.
        if len(sr) == 0:
            return res
        pprint(sr)
        print("code ", code, "match ", sr[0]["text_match"])
        # Typesense doesn't have a way currently to specify an exact match, so this filters for exact matches.
        res["names"] = [
            x["document"]["common_name"]
            for x in sr
            if code in x["document"]["short_codes"]
        ]
        return res


@dataclass
class MeilisearchSearch:
    api_key: str
    taxonomy: eBirdTaxonomy = None
    client: meilisearch.Client = None
    host: str = "localhost"
    port: str = "7700"
    protocol: str = "http"
    index_name: str = "taxonomy"
    index: meilisearch.index.Index = None
    synonyms: dict = None

    def connect(self):
        self.client = meilisearch.Client(
            f"{self.protocol}://{self.host}:{self.port}", self.api_key
        )
        self.index = self.client.index(self.index_name)

    def populate_taxonomy(self):
        # This is temporary, there needs to be a better way to do this.
        # This would also be a good spot to add other common mis-spelling.
        # Ptarmigan comes to mind.
        synonyms = {
            "grey": ["gray"],
            "gray": ["grey"],
            "color": ["colour"],
            "colour": ["color"],
        }
        if not self.taxonomy:
            raise PopulateTaxonomyError
        taxonomy = [x[1] for x in self.taxonomy.ebird_data.items()]
        self.index.update_filterable_attributes(list(taxonomy[0].keys()))
        self.index.update_synonyms(synonyms)
        self.index.add_documents(taxonomy, primary_key="species_code")

    def filter_search(self, term, max_hits=1, filter=""):
        if not filter:
            return self.index.search(term, {"limit": max_hits})["hits"]
        else:
            print("Filter: ", filter)
            return self.index.search(term, {"limit": max_hits, "filter": filter})[
                "hits"
            ]

    def search(self, term, max_hits=1):
        return self.filter_search(term, max_hits)

    def name_to_codes(self, name, mode="single"):
        res = {"name": name, "short_codes": [], "species_code": None}
        hits = self.search(name, 1)
        if len(hits) == 0 or hits == []:
            return res
        h = hits[0]
        print(h)
        codes = h["short_codes"]
        if mode == "single":
            codes = [codes[0]]
        return {
            "name": h["common_name"],
            "short_codes": codes,
            "species_code": h["short_codes"],
        }

    def code_to_names(self, code):
        code = code.upper()
        res = {"names": []}
        if len(code) not in (3, 4):
            return res
        hits = self.filter_search(code, 100, filter=f"short_codes = {code}")
        print("HITS: ", hits)
        return {"names": [x["common_name"] for x in hits]}


class PopulateTaxonomyError(Exception):
    def __init__(self):
        self.message = (
            "populate_taxonomy() can only be called on instances with an EbirdTaxonomy."
        )
