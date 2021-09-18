from collections import namedtuple
from dataclasses import dataclass, field
from io import BytesIO
from numbers import Number
from pathlib import Path
from typing import Any, Dict, Iterable, NamedTuple, Tuple, Union

import PIL.Image as BaseImage
import PIL.ImageDraw as ImageDraw
from requests import Response

from static_maps.geo import BBoxBase, BBoxT

ImageQuad = namedtuple("ImageQuad", "tl, tr, bl, br")

# Monkey Patch pillow so that .getbbox() call returns PixBbox instances.
# This is down because pillow doesn't really support subclasses, and this was cleaner than a delegate wrapper.
Image = BaseImage
Image.Image._getbbox = Image.Image.getbbox


def new_getbbox(self: Any) -> "PixBbox":
    r = self._getbbox()
    print("new_getbbox - r:", r)
    return PixBbox(*r) if r is not None else r


Image.Image.getbbox = new_getbbox


def asbytes(self) -> bytes:
    d = BytesIO()
    self.save(d, "png")
    return BytesIO(d.getvalue())


Image.Image.asbytes = asbytes

Pixel = namedtuple("Pixel", "x, y")


@dataclass(eq=False)
class PixBbox(BBoxBase):
    point_type: namedtuple = field(default=Pixel, init=False, repr=False)

    @property
    def center(self) -> Pixel:
        cx, cy = super().center
        return Pixel(round(cx), round(cy))

    @property
    def pillow(self) -> Tuple[int]:
        """Returns pixel values, normalized for a top left orgin for pillow."""
        new_top = self.bottom
        new_bottom = self.top
        return (self.left, new_top, self.right, new_bottom)


def transparency_composite(a: "Image", b: "Image", t: int = 200) -> "Image":
    """
    Composites image b onto image a and adjusts the opacity.
    Why do it this way? It was the only way to support an already partially opaque image.
    Essentially it takes only the not perfectly transparent pixels and removes the opacity, so that it can be adjusted.
    This is useful if, for example, one want to composite layers together.
    Note that this normalizes the transparency across the foreground image. Adjusting mask generation (bp2m) to take into account already existing transparency would change this.
    Args:
        a (Image): Base image.
        b (Image): Image to composite. Needs to be RGBA to work.
        t (int, optional): Opacity level, between 0 and 255 inclusive. Defaults to 200.
    Returns:
        Image: Composited image.
    """
    # print(f"trans_comp:\na: {a}\nb: {b}")
    t = max(min(t, 255), 0)
    if b.mode != "RGBA":
        raise NotRGBAError
    # We want to convert our transparent image to a non-transparent image only where there are pixels with a not fully-transparent alpha value.
    # So we end up with two transparency levels, either fully transparent or not at all.
    bp = list(b.getdata())
    bp2 = [(r, g, b, 255) if a != 0 else (r, b, g, 0) for r, g, b, a in bp]
    new_b = Image.new("RGBA", b.size)
    new_b.putdata(bp2)

    # Generate transparency mask.
    # If there's a non fully-transparent pixel in b, this should be added to the mast at the specified transparency level.
    # And if it isn't, it can stay at 0 (a==0).
    bp2m = [t if a != 0 else a for _, _, _, a in bp]
    paste_mask = Image.new("L", b.size, 255)
    paste_mask.putdata(bp2m)

    # best not to clobber a, just in case.
    temp_image = a.copy()
    temp_image.paste(new_b, (0, 0, *b.size), mask=paste_mask)
    return temp_image


def image_from_response(response: Response) -> Image:
    """
    Converts the content from a response object into an image.
    Args:
        response (Response): Response object.
    Raises:
        ImageLoadError: If the loading fails for any reason.
    Returns:
        Image: Image from the response.
    """
    try:
        return Image.open(BytesIO(response.content))
    except Exception as e:
        raise ImageLoadError(f"An error occured in image loading: {e}.")


class ImageLoadError(Exception):
    def __init__(self, message="An error occured in image loading."):
        self.message = message
        super().__init__(self.message)


# def calc_extra_tiles(tiles, extra_tiles):
#     """
#     ...
#     """
#     left = min(t.tid.x for t in tiles) - extra_tiles[0]
#     upper = min(t.tid.y for t in tiles) - extra_tiles[1]
#     right = max(t.tid.x for t in tiles) + extra_tiles[2]
#     lower = max(t.tid.y for t in tiles) + extra_tiles[3]
#     return (left, upper, right, lower)


def find_crop_bounds(image: "Image", output_size: int = 512) -> Tuple:
    """
    Calculates the crop for a given image.
    Args:
        image (Image): input image to calculate the crop for.
        output_size (int, optional): [description]. Defaults to 512.
    Raises:
        NotRGBAError: We can only find pixels that contain data on RGBA images, as alpha = 0 is no data.
    Returns:
        [tuple]: (swapped_image, crop_area, center, bbox, extra_tiles, fill_crop)
            Where:
            "swapped_image" is None if the image doesn't need to cross the antimeridian, otherwise an image with both sides of the antimerdian stuck together.
            "crop_area" is the area this tile would be cropped to if it was output_size pixels on a side.
            "center" is the center of the area that was cropped.
            "bbox" is the maximum bounding box for the pixels in the source image.
            "extra_tiles" is whether or not extra tiles need to be grabbed in the form (left, upper, right, bottom).
                This does not currently handle what happens in we need extra tiles for a swap.
            "fill_crop" is the bounding box for a crop that stays within the current image.

    """
    if image.mode != "RGBA":
        raise NotRGBAError
    bbox = image.getbbox()
    x_dim, y_dim = bbox.xy_dims
    size_x, size_y = image.size
    swapped_image = None
    # TODO: Make sure this works when the split is uneven. Will this ever even happen?
    if x_dim > output_size:
        print("Wrapping Detected.")
        print(f"orig crop area: {x_dim}, {y_dim}")
        print("orig bbox:", bbox)
        swapped_image = swap_left_right(image)
        image = swapped_image

    bbox = image.getbbox()
    x_dim, y_dim = bbox.xy_dims
    print(f"minimal crop area: {x_dim}, {y_dim}")
    center = bbox.center
    left = center[0] - output_size // 2
    upper = center[1] - output_size // 2
    right = center[0] + output_size // 2
    lower = center[1] + output_size // 2
    crop_area = (left, upper, right, lower)
    # print("ideal crop:", crop_area)
    extra_tiles = [0, 0, 0, 0]
    fill_left = left
    fill_upper = upper
    if left < 0:
        extra_tiles[0] = 1
        fill_left = 0
    if upper < 0:
        extra_tiles[1] = 1
        fill_upper = 0
    if right > size_x:
        extra_tiles[2] = 1
        fill_left = 0
    if lower > size_y:
        extra_tiles[3] = 1
        fill_upper = 0
    fill_crop = (
        fill_left,
        fill_upper,
        fill_left + output_size,
        fill_upper + output_size,
    )
    new_img = image.copy()
    bg_img = image.copy()
    box_img = ImageDraw.Draw(new_img)
    box_img.rectangle(fill_crop, outline=(0, 255, 255), fill=(0, 0, 0, 0))
    new_img.alpha_composite(bg_img)
    with open("crop_area.png", "wb") as f:
        new_img.save(f, "png")

    if swapped_image:
        print("crop_area", crop_area)
        print("center", center)
        print("bbox", bbox)
        print("extra_tiles", extra_tiles)
        print("fill_crop", fill_crop)

    return swapped_image, crop_area, center, bbox, extra_tiles, fill_crop


def swap_left_right(image):
    """
    Swaps the left half and the right half of an image. The split is always at the halfway mark.
    This is useful when the map crosses the anti-meridian.
    Args:
        image (Image): Image to swap.

    Returns:
        Image: The swapped image.
    """
    mode = image.mode
    if mode == "RGBA":
        new_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    else:
        new_image = Image.new("RGB", image.size, (0, 0, 0))
    size_x, size_y = image.size
    left = image.crop((0, 0, size_x // 2, size_y))
    right = image.crop((size_x // 2, 0, size_x, size_y))
    new_image = img_comp(new_image, right, (0, 0))
    new_image = img_comp(new_image, left, (size_x // 2, 0))
    return new_image


def img_comp(a: "Image", b: "Image", xy: Tuple[int], mode: str = None) -> "Image":
    """
    Convenience function that calls alpha_composite or paste based on image mode.
    equivalent to calling a.alpha_composite(b, *xy) or a.paste(b, *xy)
    Args:
        a (Image): background image
        b (Image): foreground image
        xy (Tuple[Int]): xy coordinates of the top left corner of a full bbox, as per piilows coordinate reference.
        mode (str, optional): mode, if none specified uses b's mode. Defaults to None.
    Returns:
        Image: output_image
    """
    print("modes", mode, a.mode, b.mode)
    if not mode:
        mode = a.mode
    if mode == "RGBA":
        a.alpha_composite(b, xy)
    else:
        a.paste(b, xy)
    return a


class NotRGBAError(Exception):
    pass


def composite_mxn(
    images: Dict[Tuple[int, int], "Image"], strict: bool = False
) -> "Image":
    """
    Composites MxN images together based on their image index.
    Args:
        images Dict[Tuple[int, int], 'Image']: a Dictionary containing an image and its coordinates from an xy plane of images.
        strict (bool, optional): If true, mixed modes and sparse (holey) images are disallowed. Defaults to False.
    Raises:
        CompositingError: If compositing can't be carrier out.
    Returns:
        Image: composited image.
    """
    x_dim = minmax_range([t[0] for t in images])
    y_dim = minmax_range([t[1] for t in images])
    x_min, _ = minmax([t[0] for t in images])
    y_min, _ = minmax([t[1] for t in images])
    # Check for holes.
    if x_dim * y_dim != len(images) and strict:
        msg = f"{len(images)} expected, got {x_dim * y_dim}."
        raise CompositingError(msg)
    # Make sure that all of the tiles are the same size.
    if len(set(im.size for im in images.values())) != 1:
        print([im.size for im in images.values()])
        msg = "All tiles need to be the same size."
        raise CompositingError(msg)
    # Make sure images are the same mode.
    if len(set(im.mode for im in images.values())) != 1 and strict:
        msg = "Mixed tile image modes."
        raise CompositingError(msg)
    image_meta = list(images.values())[0]
    image_size = image_meta.size[0]
    output_size = (image_size * x_dim, image_size * y_dim)
    mode = image_meta.mode

    if mode == "RGB":
        new_image = Image.new("RGB", output_size)
    else:
        new_image = Image.new("RGBA", output_size, (0, 255, 255, 0))
    for (img_x, img_y), img in images.items():
        # Normalize tile coordinates where x_min and/or y_min are not 0.
        img_x -= x_min
        img_y -= y_min
        x_coord = img_x * image_size
        y_coord = img_y * image_size
        img_topleft = (x_coord, y_coord)
        new_image = img_comp(new_image, img, img_topleft)
    return new_image


class CompositingError(Exception):
    """
    Raised when compositing fails.
    """

    def __init__(self, message="An error occured in compositing."):
        self.message = message
        super().__init__(self.message)


def minmax(vals: Iterable[Number]) -> Tuple[Number, Number]:
    return min(vals), max(vals)


def minmax_range(vals: Iterable[Number]) -> Tuple[Number, Number]:
    a, b = minmax(vals)
    return b - a + 1


def scale_image(image: Image, scale_factor: int = -1, quality: int = 4) -> Image:
    """
    Scales an image.
    Args:
        image (Image): image to be scaled.
        scale_factor (int, optional): Factor to scale by. 0 is no scaling. 1 means the image is 4x the size, -1 means the image is 1/4 the size. Defaults to -1.
            Any scale factors producing a >1x1 pixel image will product a 1x1 pixel image.
        quality (int, optional): quality. Higher number is better quality at the expense of performance. Defaults to 4.
    Returns:
        Image: resized version of the original image.
    """
    quality = max(min(quality, 4), 0)
    resample = [
        Image.NEAREST,
        Image.BOX,
        Image.BILINEAR,
        Image.HAMMING,
        Image.BICUBIC,
        Image.LANCZOS,
    ]
    if scale_factor == 0:
        return image
    size0 = max((2 ** scale_factor) * image.size[0], 1)
    size1 = max((2 ** scale_factor) * image.size[1], 1)
    return image.resize((size0, size1), resample=resample[quality])


def quad_split(input_image: Image, fpath: str = None) -> NamedTuple:
    """
    Splits a square image evenly into 4 pieces.
    Args:
        input_image (Image): Image to split.
        fpath (Path, optional): If set, saves the resulting images to this path.
            Generates filesnames of the form -i_abcd_s where i is the index (in reading order), s is the size of the output (so in_size / 2)
            and abcd are the normalized start pixels. Mapping 0 = 0, 1 = size / 2, 2 = size
    Returns:
        ImageQuad: The four split images in the order (top_left, top_right, bottom_left, bottom_right).
    """
    s = input_image.size[0]
    h = s // 2
    split_bbox = [(0, 0, h, h), (h, 0, s, h), (0, h, h, s), (h, h, s, s)]
    res = [input_image.copy().crop(x) for x in split_bbox]
    if fpath:
        for idx, x in enumerate(res):
            suffix = "".join([str(a // h) for a in split_bbox[idx]])
            x.save(fpath + f"-{idx}_{suffix}_{h}.png", "png")
    return ImageQuad(*res)


def blank(mode: str = "RGB", size: Tuple[int, int] = (512, 512)) -> "Image":
    """
    Convenience function that creates a blank image.
    """
    return Image.new(mode, size)


def debug_draw_pix_bbox(
    bbox: BBoxT, image: "Image", name: str, colour: Tuple[int] = (0, 255, 255)
) -> None:
    """
    Debug function. Takes a list of bounding boxes and names and draws them on the image.
    """
    background = image.copy()
    new_img2 = Image.new("RGBA", image.size, (0, 0, 0, 0))
    box_img1 = ImageDraw.Draw(new_img2)
    for b in bbox:
        box_img1.rectangle(tuple(b), outline=colour, fill=(0, 0, 0, 0))
    background = Image.alpha_composite(background, new_img2)
    with open(f"{name}.png", "wb") as f:
        background.save(f, "png")


def paste_halves(a: "Image", b: "Image") -> "Image":
    """
    Pastes image B to the right of image A
    """
    mode = a.mode
    assert a.mode == b.mode
    print("ph size:", a.size, b.size)
    assert a.size[1] == b.size[1]
    w, h = a.size
    output_size = (w * 2, h)
    # if mode == "RGB":
    #     new_image = Image.new("RGB", output_size)
    # else:
    new_image = Image.new(mode, output_size)
    new_image.paste(a, (0, 0))
    new_image.paste(b, (w, 0))
    return new_image
