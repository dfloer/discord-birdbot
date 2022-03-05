from dataclasses import dataclass
import typesense
import meilisearch
from pprint import pprint
import json
from pathlib import Path
from ebird_stuff.ebird.datamodel import eBirdTaxonomy


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
        res = {
            "name": name,
            "short_codes": [],
            "species_code": None,
            "scientific_name": None,
        }
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
        elif mode == "banding":
            # TODO: Implement banding codes.
            res["short_codes"] = [data["short_codes"][0]]
        else:
            print("double")
            res["short_codes"] = data["short_codes"]
        res["species_code"] = data["species_code"]
        res["scientific_name"] = data["scientific_name"]
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
        res = {
            "name": name,
            "short_codes": [],
            "species_code": None,
            "scientific_name": None,
        }
        hits = self.search(name, 1)
        if len(hits) == 0 or hits == []:
            return res
        h = hits[0]
        print(h)
        codes = h["short_codes"]
        # TODO: Implement banding codes.
        if mode == "single" or mode == "banding":
            codes = [codes[0]]
        return {
            "name": h["common_name"],
            "short_codes": codes,
            "species_code": h["species_code"],
            "scientific_name": h["scientific_name"],
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
