import pytest
import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

from static_maps.imager import Pixel, PixBbox, Image
from static_maps import imager


def create_blank_image(size=256, mode='RGB'):
    return Image.new(mode, (size, size))


class TestBbox:
    @pytest.mark.parametrize(
        "in_bbox",
        [
            (
                1, 2, 3, 4,
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
                1, 2, 3, 4,
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
            ((1, 2, 3, 4,), (1, 2, 3, 4)),
            ((1, 2, 3, 4,), [1, 2, 3, 4]),
            ((1, 2, 3, 4,), PixBbox(1, 2, 3, 4)),
        ],
    )
    def test_equal(self, in_bbox, comp):
        print(PixBbox(*in_bbox))
        assert PixBbox(*in_bbox) == comp

    @pytest.mark.parametrize(
        "in_bbox, comp",
        [
            ((1, 2, 3, 0,), (1, 2, 3, 4)),
            ((1, 2, 3, 0,), [1, 2, 3, 4]),
            ((1, 2, 3, 0,), PixBbox(1, 2, 3, 4)),
        ],
    )
    def test_not_equal(self, in_bbox, comp):
        print(PixBbox(*in_bbox))
        assert PixBbox(*in_bbox) != comp

    @pytest.mark.parametrize(
        "in_bbox, center",
        [
            ((0, 0, 0, 0,), (0, 0)),
            ((0, 0, 128, 128,), (64, 64)),
            ((12, 45, 39, 124), (26, 84)),
        ],
    )
    def test_center(self, in_bbox, center):
        r = PixBbox(*in_bbox)
        assert r.center == Pixel(*center)
        assert type(r.center) == Pixel


class TestImage:
    test_img_path = Path("./static_maps/tests/images")

    # @staticmethod
    def open_image(self, fn):
        p = self.test_img_path / Path(fn)
        with open(p, 'rb') as f:
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

        res1 = imager.transparency_composite(a=background_rgb, b=foreground, t=transparency)
        res2 = imager.transparency_composite(a=background_rgba, b=foreground, t=transparency)

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
                ('test_comp_2x2-0_0011_768.png',
                'test_comp_2x2-1_1021_768.png',
                'test_comp_2x2-2_0112_768.png',
                'test_comp_2x2-3_1122_768.png'),
                "result-composite_2x2-1536.png"),
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
