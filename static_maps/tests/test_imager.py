import pytest
import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

from static_maps.imager import Pixel, PixBbox, Image
from static_maps import imager


def create_blank_image(size=256, mode="RGB"):
    return Image.new(mode, (size, size))


class TestBbox:
    @pytest.mark.parametrize(
        "in_bbox",
        [
            (
                1,
                2,
                3,
                4,
            ),
        ],
    )
    def test_creation(self, in_bbox):
        res_bbox = PixBbox(*in_bbox)
        assert res_bbox == in_bbox

    @pytest.mark.parametrize(
        "in_bbox",
        [
            (
                1,
                2,
                3,
                4,
            ),
        ],
    )
    def test_corners(self, in_bbox):
        res_bbox = PixBbox(*in_bbox)
        assert res_bbox.left == in_bbox[0]
        assert res_bbox.top == in_bbox[1]
        assert res_bbox.right == in_bbox[2]
        assert res_bbox.bottom == in_bbox[3]

    @pytest.mark.parametrize(
        "in_bbox, comp",
        [
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                (1, 2, 3, 4),
            ),
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                [1, 2, 3, 4],
            ),
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                PixBbox(1, 2, 3, 4),
            ),
        ],
    )
    def test_equal(self, in_bbox, comp):
        print(PixBbox(*in_bbox))
        assert PixBbox(*in_bbox) == comp

    @pytest.mark.parametrize(
        "in_bbox, comp",
        [
            (
                (
                    1,
                    2,
                    3,
                    0,
                ),
                (1, 2, 3, 4),
            ),
            (
                (
                    1,
                    2,
                    3,
                    0,
                ),
                [1, 2, 3, 4],
            ),
            (
                (
                    1,
                    2,
                    3,
                    0,
                ),
                PixBbox(1, 2, 3, 4),
            ),
        ],
    )
    def test_not_equal(self, in_bbox, comp):
        print(PixBbox(*in_bbox))
        assert PixBbox(*in_bbox) != comp

    @pytest.mark.parametrize(
        "in_bbox, center",
        [
            (
                (
                    0,
                    0,
                    0,
                    0,
                ),
                (0, 0),
            ),
            (
                (
                    0,
                    0,
                    128,
                    128,
                ),
                (64, 64),
            ),
            ((12, 45, 39, 124), (26, 84)),
        ],
    )
    def test_center(self, in_bbox, center):
        r = PixBbox(*in_bbox)
        assert r.center == Pixel(*center)
        assert type(r.center) == Pixel

    @pytest.mark.parametrize(
        "in_bbox, result",
        [
            (
                PixBbox(left=0, top=256, right=256, bottom=0),
                (0, 0, 256, 256),
            ),
            (
                PixBbox(left=216, top=512, right=728, bottom=1024),
                (216, 512, 728, 1024),
            ),
        ],
    )
    def test_pillow(self, in_bbox, result):
        assert in_bbox.pillow == result


class TestImage:
    test_img_path = Path("./static_maps/tests/images")

    # @staticmethod
    def open_image(self, fn):
        p = self.test_img_path / Path(fn)
        with open(p, "rb") as f:
            return Image.open(f).copy()

    @staticmethod
    def compare_images(a, b):
        return list(a.getdata()) == list(b.getdata())

    @pytest.mark.parametrize(
        "transparency",
        [0, 64, 128, 200],
    )
    def test_composite_transparency(self, transparency):
        """
        Tests compositing a mixed transparency image on a background and then changing the transparency of that image to a baseline.
        """
        foreground = self.open_image("transparency-test-paw_RGBA.png")
        background_rgb = self.open_image("background_RGB.png")
        background_rgba = self.open_image("background_RGBA.png")

        res1 = imager.transparency_composite(
            a=background_rgb, b=foreground, t=transparency
        )
        res2 = imager.transparency_composite(
            a=background_rgba, b=foreground, t=transparency
        )

        exp1 = self.open_image(f"result-RGB_comp-trans_{transparency}.png")
        exp2 = self.open_image(f"result-RGBA_comp-trans_{transparency}.png")

        assert self.compare_images(res1, exp1)
        assert self.compare_images(res2, exp2)

    def test_monkeypatch_getbbox(self):
        res = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
        bb = res.getbbox()
        print(bb, type(bb))
        print("image", Image)
        assert bb.left == 0
        assert bb.right == 256
        assert bb.top == 0
        assert bb.bottom == 256

    def test_swap(self):
        img = self.open_image("test_image_RGBA.png")
        swap = imager.swap_left_right(img)
        exp = self.open_image("result_swap_lr.png")
        assert self.compare_images(swap, exp)
        back = imager.swap_left_right(swap)
        assert self.compare_images(back, img)

    @pytest.mark.parametrize(
        "images, result",
        [
            (
                (
                    "test_comp_2x2-0_0011_768.png",
                    "test_comp_2x2-1_1021_768.png",
                    "test_comp_2x2-2_0112_768.png",
                    "test_comp_2x2-3_1122_768.png",
                ),
                "result-composite_2x2-1536.png",
            ),
        ],
    )
    def test_composite_split_2x2(self, images, result):
        """
        Tests compositing 4 images together into a 2x2 grid and then splitting them back again.
        """
        expected = self.open_image(result)
        imgs = [self.open_image(fn) for fn in images]
        idxs = [(x + 1, y + 2) for x, y in ((0, 0), (1, 0), (0, 1), (1, 1))]
        idx_imgs = {k: v for k, v in zip(idxs, imgs)}
        res = imager.composite_mxn(idx_imgs)
        assert self.compare_images(res, expected)

        # And back again.
        sp = imager.quad_split(res)
        assert all([self.compare_images(*a) for a in zip(sp, imgs)])

    @pytest.mark.parametrize(
        "left_image, right_image, result, error",
        [
            (
                "test_paste_halves_left.png",
                "test_paste_halves_right.png",
                "result_paste_halves.png",
                None,
            ),
            (
                "test_paste_halves_left.png",
                "test_paste_halves_right-2x.png",
                "result_paste_halves-2x.png",
                None,
            ),
            (
                "test_paste_halves_left.png",
                "test_paste_halves_right.png",
                "",
                imager.MixedImageModesError,
            ),
            (
                "test_paste_halves_left.png",
                "test_paste_halves_right.png",
                "",
                imager.CompositingError,
            ),
        ],
    )
    def test_paste_halves(self, left_image, right_image, result, error):
        left = self.open_image(left_image)
        right = self.open_image(right_image)
        if error is imager.MixedImageModesError:
            left.mode = "RGBA"
            right.mode = "RGB"
        if error is imager.CompositingError:
            left = left.crop((0, 0, left.size[0], left.size[1] // 2))
        if not error:
            result = self.open_image(result)
            res = imager.paste_halves(left, right)
            res.save("imph.png")
            assert self.compare_images(result, res)
        else:
            with pytest.raises(error):
                _ = imager.paste_halves(left, right)

    @pytest.mark.parametrize(
        "image_fn, crop_size, expected_bounds",
        [
            (
                "test_crop_bounds_512-max.png",
                512,
                PixBbox(256, 256, 768, 768),
            ),
            (
                "test_crop_bounds_512-normal.png",
                512,
                PixBbox(109, 132, 621, 644),
            ),
            (
                "test_crop_bounds_512-am.png",
                512,
                PixBbox(128, 128, 640, 640),
            ),
        ],
    )
    def test_find_crop_bounds(self, image_fn, crop_size, expected_bounds):
        image = self.open_image(image_fn)
        fitted_crop, center_crop = imager.find_crop_bounds(image, crop_size)
        assert fitted_crop == expected_bounds
