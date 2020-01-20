import pytest

import text_search
import sys

sys.path.append("../")
import input_parsing.ebird_taxonomy_parse as etp

fn = "../input_parsing/eBird_Taxonomy_v2019.csv"
common, scientific, code, short = etp.taxonomy_parse(fn)

# Test unicode to ascii normalization.
@pytest.mark.parametrize("unicode_str, ascii_str",
    [
        ("Rüppell's Bustard", "Ruppell's Bustard"),
        ("Sjöstedt's Owlet", "Sjostedt's Owlet"),
        ("Marañon Crescentchest", "Maranon Crescentchest"),
        ("Oberländer's Ground-Thrush", "Oberlander's Ground-Thrush"),
    ],
)
def test_unicode_normalization(unicode_str, ascii_str):
    assert text_search.normalize_to_ascii(unicode_str) == ascii_str

# Test single results, where the bird's exact name is looked up.
@pytest.mark.parametrize("name, results",
    [
        ("Bushtit", ["Bushtit"]),
        ("Yellow-rumped Warbler", ["Yellow-rumped Warbler"]),
        ("Von der Decken's Hornbill", ["Von der Decken's Hornbill"]),
        ("King-of-Saxony Bird-of-Paradise", ["King-of-Saxony Bird-of-Paradise"]),
    ],
)
def test_exact_match(name, results):
    assert text_search.word_start_search(name, common) == results

# Test single results, where a close name is looked up..
@pytest.mark.parametrize("name, results",
    [
        ("bushtit", ["Bushtit"]),
        ("Yellow rumped Warbler", ["Yellow-rumped Warbler"]),
        ("andean cock of the rock", ["Andean Cock-of-the-rock"]),
        ("omao", ["Omao"]),
        ("king of saxony bird of paradise", ["King-of-Saxony Bird-of-Paradise"])
    ],
)
def test_close_match(name, results):
    assert text_search.word_start_search(name, common) == results

@pytest.mark.parametrize("name, results",
    [
        ("Chickadee", ['Carolina Chickadee', 'Black-capped Chickadee', 'Mountain Chickadee', 'Mexican Chickadee', 'Chestnut-backed Chickadee', 'Boreal Chickadee', 'Gray-headed Chickadee']),
        ("Owl", ['New Caledonian Owlet-nightjar', 'Feline Owlet-nightjar', 'Starry Owlet-nightjar', "Wallace's Owlet-nightjar", "Archbold's Owlet-nightjar", 'Mountain Owlet-nightjar', 'Moluccan Owlet-nightjar', 'Australian Owlet-nightjar', 'Vogelkop Owlet-nightjar', 'Barred Owlet-nightjar', 'Sooty Owl', 'Australian Masked-Owl', 'Golden Masked-Owl', 'Seram Masked-Owl', 'Lesser Masked-Owl', 'Manus Masked-Owl', 'Taliabu Masked-Owl', 'Minahassa Masked-Owl', 'Sulawesi Masked-Owl', 'Australasian Grass-Owl', 'African Grass-Owl', 'Barn Owl', 'Andaman Masked-Owl', 'Ashy-faced Owl', 'Red Owl', 'Oriental Bay-Owl', 'Sri Lanka Bay-Owl', 'Congo Bay-Owl', 'White-fronted Scops-Owl', 'Andaman Scops-Owl', 'Reddish Scops-Owl', 'Serendib Scops-Owl', 'Sandy Scops-Owl', 'Sokoke Scops-Owl', 'Flores Scops-Owl', 'Mountain Scops-Owl', 'Rajah Scops-Owl', 'Javan Scops-Owl', 'Mentawai Scops-Owl', 'Indian Scops-Owl', 'Collared Scops-Owl', 'Giant Scops-Owl', 'Sunda Scops-Owl', 'Japanese Scops-Owl', "Wallace's Scops-Owl", 'Palawan Scops-Owl', 'Philippine Scops-Owl', "Everett's Scops-Owl", 'Negros Scops-Owl', 'Mindoro Scops-Owl', 'Moluccan Scops-Owl', 'Rinjani Scops-Owl', 'Mantanani Scops-Owl', 'Ryukyu Scops-Owl', 'Sulawesi Scops-Owl', 'Sangihe Scops-Owl', 'Siau Scops-Owl', 'Sula Scops-Owl', 'Biak Scops-Owl', 'Simeulue Scops-Owl', 'Enggano Scops-Owl', 'Nicobar Scops-Owl', 'Arabian Scops-Owl', 'Eurasian Scops-Owl', 'Pemba Scops-Owl', 'Sao Tome Scops-Owl', 'African Scops-Owl', 'Pallid Scops-Owl', 'Mindanao Scops-Owl', 'Luzon Scops-Owl', 'Moheli Scops-Owl', 'Comoro Scops-Owl', 'Seychelles Scops-Owl', 'Oriental Scops-Owl', 'Socotra Scops-Owl', 'Anjouan Scops-Owl', 'Mayotte Scops-Owl', 'Reunion Scops-Owl', 'Rodrigues Scops-Owl', 'Mauritius Scops-Owl', 'Malagasy Scops-Owl', 'Torotoroka Scops-Owl', 'Flammulated Owl', 'Puerto Rican Screech-Owl', 'Bare-shanked Screech-Owl', 'Whiskered Screech-Owl', 'White-throated Screech-Owl', 'Tropical Screech-Owl', "Koepcke's Screech-Owl", 'Rufescent Screech-Owl', 'Cinnamon Screech-Owl', 'Cloud-forest Screech-Owl', 'Montane Forest Screech-Owl', 'Middle American Screech-Owl', 'Choco Screech-Owl', 'Foothill Screech-Owl', 'Long-tufted Screech-Owl', 'Bearded Screech-Owl', 'Balsas Screech-Owl', 'Pacific Screech-Owl', 'Western Screech-Owl', 'Eastern Screech-Owl', 'Santa Marta Screech-Owl', 'Peruvian Screech-Owl', 'Tawny-bellied Screech-Owl', 'Black-capped Screech-Owl', 'Palau Owl', 'Bare-legged Owl', 'Northern White-faced Owl', 'Southern White-faced Owl', 'Crested Owl', 'Maned Owl', 'Spectacled Owl', 'Tawny-browed Owl', 'Band-bellied Owl', 'Great Horned Owl', 'Eurasian Eagle-Owl', 'Rock Eagle-Owl', 'Pharaoh Eagle-Owl', 'Cape Eagle-Owl', 'Spotted Eagle-Owl', 'Grayish Eagle-Owl', "Fraser's Eagle-Owl", 'Usambara Eagle-Owl', 'Spot-bellied Eagle-Owl', 'Barred Eagle-Owl', "Shelley's Eagle-Owl", "Verreaux's Eagle-Owl", 'Dusky Eagle-Owl', 'Akun Eagle-Owl', 'Philippine Eagle-Owl', 'Snowy Owl', "Blakiston's Fish-Owl", 'Brown Fish-Owl', 'Tawny Fish-Owl', 'Buffy Fish-Owl', "Pel's Fishing-Owl", 'Rufous Fishing-Owl', 'Vermiculated Fishing-Owl', 'Northern Hawk Owl', 'Eurasian Pygmy-Owl', 'Collared Owlet', 'Pearl-spotted Owlet', 'Northern Pygmy-Owl', 'Costa Rican Pygmy-Owl', 'Cloud-forest Pygmy-Owl', 'Andean Pygmy-Owl', 'Yungas Pygmy-Owl', 'Subtropical Pygmy-Owl', 'Central American Pygmy-Owl', 'Tamaulipas Pygmy-Owl', 'Colima Pygmy-Owl', 'Amazonian Pygmy-Owl', 'Pernambuco Pygmy-Owl', 'Least Pygmy-Owl', 'Ferruginous Pygmy-Owl', 'Austral Pygmy-Owl', 'Peruvian Pygmy-Owl', 'Cuban Pygmy-Owl', 'Red-chested Owlet', "Sjöstedt's Owlet", 'Asian Barred Owlet', 'Javan Owlet', 'Jungle Owlet', 'Chestnut-backed Owlet', 'African Barred Owlet', 'Chestnut Owlet', 'Albertine Owlet', 'Long-whiskered Owlet', 'Elf Owl', 'Spotted Owlet', 'Little Owl', 'Forest Owlet', 'White-browed Owl', 'Burrowing Owl', 'Mottled Owl', 'Black-and-white Owl', 'Black-banded Owl', 'Rufous-banded Owl', 'Spotted Wood-Owl', 'Mottled Wood-Owl', 'Brown Wood-Owl', 'Tawny Owl', 'Himalayan Owl', 'Desert Owl', 'Omani Owl', 'Spotted Owl', 'Barred Owl', 'Fulvous Owl', 'Rusty-barred Owl', 'Rufous-legged Owl', 'Chaco Owl', 'Ural Owl', "Pere David's Owl", 'Great Gray Owl', 'African Wood-Owl', 'Long-eared Owl', 'Abyssinian Owl', 'Madagascar Owl', 'Striped Owl', 'Stygian Owl', 'Short-eared Owl', 'Marsh Owl', 'Fearful Owl', 'Jamaican Owl', 'Boreal Owl', 'Northern Saw-whet Owl', 'Bermuda Saw-whet Owl', 'Unspotted Saw-whet Owl', 'Buff-fronted Owl', 'Rufous Owl', 'Powerful Owl', 'Barking Owl', 'Papuan Owl', 'Laughing Owl']),
        ("Grous", ['Black Grouse', 'Caucasian Grouse', 'Hazel Grouse', "Severtzov's Grouse", 'Ruffed Grouse', 'Greater Sage-Grouse', 'Gunnison Sage-Grouse', 'Siberian Grouse', 'Spruce Grouse', 'Dusky Grouse', 'Sooty Grouse', 'Sharp-tailed Grouse']),
    ],
)
def test_multiple_matches(name, results):
    assert text_search.word_start_search(name, common) == results

# Tests whether or not we're matching only at the start of words and not anywhere in the word.
@pytest.mark.parametrize("name, results",
    [
        ("Omao", ["Omao"]),
        ("Mao", ["Mao"]),
    ],
)
def test_start_only(name, results):
    assert text_search.word_start_search(name, common) == results

# Make sure we don't find matches for birds that aren't in the taxonomy.
@pytest.mark.parametrize("name, results",
    [
        ("potato", []),
        ("Birb", []),
    ],
)
def test_no_results(name, results):
    assert text_search.word_start_search(name, common) == results
