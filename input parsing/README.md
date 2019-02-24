# Input Parsing Scripts

 - `ebird_taxonomy_parse.py`: For parsing the eBird taxonomy CSV obtained from <http://www.birds.cornell.edu/clementschecklist/download/ into common/scientific> names and their 4-letter-codes to allow mapping between 4-letter codes and the common, not scientific, name. Outputs mappings in json format to `common.json`, which includes the commone name to all 4-letter-codes including the scientific/binomial mapping.\
 \
 Currently tested with the 2018 eBird taxonomy (not Clements or combined). \
 \
 Uses the rules as given at <https://help.ebird.org/customer/portal/articles/2667298-quick-entry-code-methodology> with some additional behaviour for edge-cases the rules don't include.\
 \
 Unspecified Behaviour:
   - Several entries on eBird don't match their own rules. This code does not replicate this behaviour and instead returns according to the rules. \
   For example, "King-of-Saxony Bird-of-Paradise" is given in the rules (and this code) as producing KOSB and KSBP, but only KOSB produces results in eBird's species search.
   - Birds with names that are less than 4 letters long have a code of their whole name.
   - There in an alternative rule for dealing with birds that have a hyphen separating the final words of their names. There are several birds with more than one hyphen separating the last words of the name, including a few birds where all of their name is hyphenated. The rule says **a** hyphen, so this code only uses the alternative with one hyphen.
   - Further on the previous, there are also bird species that have multiple than one word before the hyphenated part. Only the first word and last hyphenated words are looked at. \
    Examples: Serra do Mar Tyrant-Manakin is SETM. even though the rules are unclear how this is treated.
    - For bird names that are over 4 words long when split on hyphens, but 4 or fewer words long when not split on hyphens using the alternative hyphen splitting rule, both forms are returned.
    - In addition to the previous, both rules are also applied with the alternate rule for >4 word names with obvious conjunctions omitted (of, and, the).
    - Does not represent alternate common names as these are not included in the eBird taxonomy and it is unknown which are supported.
 - `banding_code_parse.py`: Parses the banding codes from The Institute for Bird Populations.       