import lxml.html
import requests


def ml_get_image_url(asset_id, size=1200):
    """
    Gets the image from ML.
    Arguments:
        asset_id (int): Asset ID from ML.
        size (int, str): Width of the image. Not all sizes are valid.
            Int sized observed working: 640, 900, 1200, 1800, 2400.
            Can also be string sizes of "medium" = 640, "large" = 1200 and "original".
    Returns:
        The image's url.
    """
    image_base_url = "https://download.ams.birds.cornell.edu/api/v1/asset"
    return f"{image_base_url}/{asset_id}/{size}"


def ml_get_images(taxon_code, sort_type="quality"):
    """
    Get images from ML using the API.
    Arguments:
        taxon_code (str): eBird's 6 character taxon code.
        sort_type (str): How the results should be sorted (default: {"quality"})
            Choices are "recent": "Recently Uploaded", "quality": "Best Quality", "least": "Least Rated", "newest": "Date: Newest First", "oldest": "Date: Oldest First".
    Returns:
        A list of asset IDs for the bird as sorted.
    """
    sort_map = {
        "recent": "",
        "quality": "rating_rank_desc",
        "least": "rating_count_asc",
        "newest": "obs_date_desc",
        "oldest": "obs_date_asc",
    }
    search_url = f"https://ebird.org/media/catalog?taxonCode={taxon_code}&sort={sort_map[sort_type]}&view=List"
    response = requests.get(search_url, stream=True)
    response.raw.decode_content = True
    tree = lxml.html.parse(response.raw)
    # The xpath expression might change unexpectedly, so this is fragile.
    # Also note that xpath is _1_ indexed, which is what the +1 is for.
    asset_ids = []
    for x in range(30):
        x += 1
        entry = tree.xpath(f"/html/body/main/form/div/div[3]/div[1]/div[{x}]/div[1]/div/a")[0].attrib
        asset_ids += [int(entry["data-asset-id"])]
    return asset_ids


if __name__ == "__main__":
    test_taxon = "bushti"
    images = ml_get_images(test_taxon)
    image_urls = [ml_get_image_url(x) for x in images]
    for x in image_urls:
        print(x)
