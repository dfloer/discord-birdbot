import lxml.html
import requests


def ml_get_image_url(asset_id, size=1200):
    """
    Gets the image url if we only have an asset_id.
    Arguments:
        asset_id (int): Asset ID from ML.
        size (int, str): Width of the image. Not all sizes are valid.
            Int sized observed working: 640, 900, 1200, 1800, 2400.
            Can also be string sizes of "medium" = 640, "large" = 1200 and "original".
    Returns:
        The image's url.
    """
    image_base_url = "https://cdn.download.ams.birds.cornell.edu/api/v1/asset"
    return f"{image_base_url}/{asset_id}/{size}"


def rewrite_url(url, size=1200):
    """
    Changes a url of the form https://macaulaylibrary.org/asset/<asset_id> to "https://download.ams.birds.cornell.edu/api/v1/asset/<asset_id>"
    Args:
        url (str): ML web address
        size (int, str): Width of the image. Not all sizes are valid.
            Int sized observed working: 640, 900, 1200, 1800, 2400.
            Can also be string sizes of "medium" = 640, "large" = 1200 and "original".
    Returns:
        [str]: direct url to the picture
    """
    return ml_get_image_url(url.split("/")[-1])


def ml_get_images(taxon_code, sort_type="quality", size=1200):
    """
    Get images from ML using the API.
    Arguments:
        taxon_code (str): eBird's 6 character taxon code.
        sort_type (str): How the results should be sorted (default: {"quality"})
            Choices are "recent": "Recently Uploaded", "quality": "Best Quality", "least": "Least Rated", "newest": "Date: Newest First", "oldest": "Date: Oldest First".
        size (int, str): Width of the image. Not all sizes are valid.
            Int sized observed working: 640, 900, 1200, 1800, 2400.
            Can also be string sizes of "medium" = 640, "large" = 1200 and "original".
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
    search_url = f"https://search.macaulaylibrary.org/catalog.json?searchField=species&q=&taxonCode={taxon_code}&sort={sort_map[sort_type]}"
    data = requests.get(search_url, stream=True).json()
    asset_ids = [f"{x['previewUrl']}{size}" for x in data["results"]["content"]]
    return asset_ids


if __name__ == "__main__":
    test_taxon = "bushti"
    image_urls = ml_get_images(test_taxon)
    for x in image_urls:
        print(x)

    print("Rewrite:")
    test_url = "https://macaulaylibrary.org/asset/307671311"
    print(rewrite_url(test_url))
