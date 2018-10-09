import functools
import itertools
import json
import operator
import os
import string
from collections import namedtuple
from contextlib import suppress

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.spatial.distance import euclidean
from skimage import exposure
from typo_graphics import Glyph

tree_set = namedtuple('tree_set', ['glyph_set', 'tree', 'centroid',
                                   'mean_square_from_centroid', 'stack_size'])
tree_set.__doc__ = """
Named tuple container for information regarding sets of glyphs

May be unpacked, or accessed using member names
:attr:`~typo_graphics.typograph.tree_set.glyph_set`,
:attr:`~typo_graphics.typograph.tree_set.tree`,
:attr:`~typo_graphics.typograph.tree_set.centroid`,
:attr:`~typo_graphics.typograph.tree_set.mean_square_from_centroid`,
:attr:`~typo_graphics.typograph.tree_set.stack_size`

:param glyph_set: list containing a collection of glyphs 
:type glyph_set: [:class:`Glyph`]
:param tree: a :class:`~scipy.spatial.cKDTree` instantiated with the glyphs
 of :attr:`~typo_graphics.typograph.tree_set.glyph_set`
:type tree: :class:`~scipy.spatial.cKDTree`
:param array_like centroid: position of centroid in :attr:`~Glyph.sample_x` * :attr:`~Glyph.sample_y` parameter space
:param mean_square_from_centroid: mean square distance of glyphs from centroid
:type mean_square_from_centroid: :class:`float`
:param stack_size: number of fundamental glyphs used to compose each glyph
 in :attr:`~typo_graphics.typograph.tree_set.glyph_set`
:type stack_size: :class:`int`
"""

typed_art = namedtuple('typed_art', ['calculation', 'output', 'instructions'])
typed_art.__doc__ = """
Named tuple container for output of :meth:`~Typograph.image_to_text`

May be unpacked, or accessed using member names
:attr:`~typo_graphics.typograph.typed_art.calculation`,
:attr:`~typo_graphics.typograph.typed_art.output`,
:attr:`~typo_graphics.typograph.typed_art.instructions`

:param calculation: an :class:`~PIL.Image.Image` object, showing the :attr:`~Glyph.fingerprint_display` images, 
 composed according to the result
:type calculation: :class:`~PIL.Image.Image`
:param output: an :class:`~PIL.Image.Image` object, showing the composed glyph result
:type output: :class:`~PIL.Image.Image`
:param instructions: string of instruction lines, separated by \n
:type instructions: :class:`string`
"""

# TODO dump list
# Enhanced image production for single glyph stacking
# --> looks to be issue with how we calculate self.value_extrema
# docs with sphinx
# demo images / gifs etc
# --> translation, rotations of simple shapes
# --> show image, calculation for both good samples, and sample of (1,1)
# ------> ie the common easy ascii method
# some nice, royalty free images to show
# updated glyph images, getting rid of some of the messiness
# --> can just make a glyph sheet for this


class Typograph:
    """
    Class for processing glyphs for the creation of images.

    This class primarily is designed to be used to convert an image into a set of instructions,
    that can be typed on a typewriter to reproduce the image.

    Class methods :meth:`~Typograph.from_glyph_sheet` and
    :meth:`~Typograph.from_directory` present other initialisation options

    Exposes :meth:`~Typograph.image_to_text` , which can be used to convert any supplied image into glyph format
    """

    def __init__(self, glyph_images=None, samples=(3, 3), glyph_depth=2):
        """
        Create :class:`Typograph` object with glyphs specified in `glyph_images`

        :param glyph_images: dictionary of images, keyed with glyph names
        :type glyph_images: {:class:`str`: :class:`~PIL.Image.Image`}
        :param samples: number of samples across and down, used to match glyphs to input images.
         If only :class:`int` given, uses that value for both directions
        :type samples: (:class:`int`, :class:`int`) or :class:`int`
        :param glyph_depth: maximum number of glyphs to stack into single characters
        :type glyph_depth: :class:`int`
        """

        if isinstance(samples, int):
            samples = (samples, samples)

        self.samples = samples
        self.sample_x, self.sample_y = samples
        if glyph_images is None:
            from typo_graphics import package_directory
            glyph_directory = os.path.join(package_directory, './Glyphs')
            glyph_images = self._get_glyphs_from_directory(glyph_directory)

        self.glyphs = {}

        for name, image in glyph_images.items():
            glyph_ = Glyph(name, image, samples=samples)
            # TODO perhaps we no longer need this dict format
            self.glyphs.update({glyph_.name: glyph_})


        # TODO ugly, would be cleaner if glyphs were in a sequence
        self.glyph_width, self.glyph_height = next(iter(self.glyphs.values())).image.size
        self.glyph_depth = glyph_depth
        self.standalone_glyphs = {}
        self._recalculate_glyphs()

    @classmethod
    def from_glyph_sheet(cls, glyph_sheet, number_glyphs, glyph_dimensions=None, grid_size=None,
                         glyph_names=None, spacing=(0, 0), **kwargs):
        """
        Create :class:`Typograph` object with glyphs as extracted from `glyph_sheet`

        Allows for a single :class:`~PIL.Image.Image` to be used to provide glyph images

        :param glyph_sheet: glyph sheet :class:`~PIL.Image.Image`, to be split into glyphs
        :type glyph_sheet: :class:`~PIL.Image.Image`
        :param number_glyphs: total number of glyphs present in `glyph_sheet`
        :type number_glyphs: :class:`int`
        :param glyph_dimensions: pixel dimensions of glyphs given as (width, height)
        :type glyph_dimensions: (:class:`int`, :class:`int`)
        :param grid_size: if given, number of (rows, columns) that glyphs are arranged in
        :type grid_size: (:class:`int`, :class:`int`)
        :param glyph_names: list of glyph names listed left to right, top to bottom
        :type glyph_names: [:class:`str`]
        :param spacing: tuple of integer pixel spacing between adjacent glyphs,
         as number of pixels between glyphs horizontally and vertically
        :type spacing: (:class:`int`, :class:`int`)
        :param kwargs: optional keyword arguments as for :class:`Typograph`
        :return: An :class:`Typograph` object using glyphs images extracted from `glyph_sheet`
        :rtype: :class:`Typograph`
        :raises TypeError: if `number_glyphs` is not given
        :raises TypeError: if neither `grid_size` or `glyph_dimensions` are specified
        """

        if (glyph_dimensions is None) and (grid_size is None):
            raise TypeError("from_glyphsheet() missing required keyword argument "
                            "'grid_size' or 'glyph_dimensions'")

        sheet_width, sheet_height = glyph_sheet.size
        spacing_x, spacing_y = spacing

        if grid_size is not None:
            grid_width, grid_height = grid_size
            glyph_width = (sheet_width - (spacing_x * (grid_width - 1))) / grid_width
            glyph_height = (sheet_height - (spacing_y * (grid_height - 1))) / grid_height
            if not (glyph_width.is_integer() and glyph_height.is_integer()):
                raise ValueError("incorrect glyph counts for image and dimensions given")
            glyph_width = int(glyph_width)
            glyph_height = int(glyph_height)
        else:
            glyph_width, glyph_height = glyph_dimensions
            grid_width = (sheet_width + spacing_x) // (glyph_width + spacing_x)
            grid_height = (sheet_height + spacing_y) // (glyph_height + spacing_y)

        glyph_images = {}
        for i_y in range(grid_height):
            for i_x in range(grid_width):
                box = (i_x * (glyph_width + spacing_x), i_y * (glyph_height + spacing_y),
                       ((i_x + 1) * glyph_width) + (i_x * spacing_x), ((i_y + 1) * glyph_height) + (i_y * spacing_y))
                glyph = glyph_sheet.crop(box)
                name_index = (i_y * grid_width) + i_x

                if glyph_names:
                    name = glyph_names[name_index]
                else:
                    name = 'g{}'.format(name_index)

                glyph_images.update({name: glyph})

                if len(glyph_images) == number_glyphs:
                    return cls(glyph_images=glyph_images, **kwargs)

    @classmethod
    def from_directory(cls, glyph_directory, **kwargs):
        """
        Create :class:`Typograph` object loading glyph images from a given directory.

        In addition to images, the directory can contain a name_map.json file
        giving alias names for glyphs located in the directory

        :param glyph_directory: A file path for directory containing glyph images
        :type glyph_directory: :class:`str`
        :param kwargs: optional keyword arguments as for :class:`Typograph`
        :return: An :class:`Typograph` object using glyphs images found from directory
        :rtype: :class:`Typograph`
        """
        glyph_images = cls._get_glyphs_from_directory(glyph_directory)
        return cls(glyph_images=glyph_images, **kwargs)

    @staticmethod
    def _get_glyphs_from_directory(glyph_directory):
        with suppress(FileNotFoundError):  # look for a name_map.json, but continue if not found
            with open(os.path.join(glyph_directory, 'name_map.json'), 'r', encoding="utf-8") as fp:
                glyph_names = json.load(fp)

        glyph_images = {}

        for filename in os.listdir(glyph_directory):
            with suppress(IOError):  # skips over any files that Image cannot open
                name = os.path.splitext(filename)[0]
                name = glyph_names.get(name, name)
                path = os.path.join(glyph_directory, filename)
                image = Image.open(path)
                glyph_images.update({name: image})

        return glyph_images

    # ~~ GLYPH WORK ON INIT ~~

    def _calculate_trees(self):
        """
        Calculate tree sets for input glyphs, combined up to `self.glyph_depth`

        :return: list of tree sets
        :rtype: [:class:`~typograph.tree_set`]
        """
        tree_sets = []

        for stack_size in range(1, self.glyph_depth + 1):
            glyph_set = list(self._combine_glyphs(stack_size).values())

            if stack_size == 1:
                glyph_set.extend(list(self.standalone_glyphs.values()))

            glyph_data = [list(glyph.fingerprint.getdata()) for glyph in glyph_set]
            tree = cKDTree(glyph_data)
            centroid = np.mean(glyph_data, axis=0)
            mean_square_from_centroid = np.mean(((glyph_data - centroid) ** 2).sum(axis=1))

            tree_sets.append(tree_set(glyph_set=glyph_set, tree=tree, centroid=centroid,
                                      mean_square_from_centroid=mean_square_from_centroid,
                                      stack_size=stack_size))

        return tree_sets

    def _combine_glyphs(self, depth):
        """
        Calculate all unique combinations of `depth` number of glyphs

        :param depth: number of glyphs to combine into composite glyphs
        :type depth: :class:`int`
        :return: dictionary of combination glyphs, using glyph names as keys
        :rtype: :class:`dict`
        """
        glyph_combinations = itertools.combinations(iter(self.glyphs.values()), depth)
        output = {}
        for combination in glyph_combinations:
            new = functools.reduce(operator.add, combination)
            output.update({new.name: new})
        return output

    def _average_glyph_values(self):
        """
        Calculate average pixel values for all glyphs in `self.tree_sets`

        :return: list of average pixel values, no given order
        :rtype: [:class:`float`]
        """
        average_values = []
        for tree_set in self.tree_sets:
            for glyph in tree_set.glyph_set:
                values = list(glyph.fingerprint.getdata())
                average_value = sum(values) / len(values)
                average_values.append(average_value)
        return average_values

    def _glyph_value_extrema(self):
        """
        Extrema of average pixel values for all glyphs

        :return: tuple of (min, max) pixel values
        :rtype: (:class:`float`, :class:`float`)
        """
        return min(self.average_values), max(self.average_values)

    def _recalculate_glyphs(self):
        """
        Update tree sets, average values and the value extrema. Used whenever glyphs are changed.
        """
        # Will be recalculating all trees, not just the ones affected
        self.tree_sets = self._calculate_trees()
        self.average_values = self._average_glyph_values()
        self.value_extrema = self._glyph_value_extrema()

    def add_glyph(self, glyph, use_in_combinations=False):
        """
        Add extra glyphs into the available pool.
        New glyphs added in this manner can be excluded from use in combinations, to be used only as standalone glyph.

        Adding a glyph already present in combinations, as a standalone
        will result in removal of glyph from combinations. The reverse of this is also true.

        :param glyph: glyph to add
        :type glyph: :class:`Glyph`
        :param use_in_combinations: use this glyph in combinations, default False
        :type use_in_combinations: :class:`bool`
        """
        if use_in_combinations:
            self.standalone_glyphs.pop(glyph.name, None)
            self.glyphs.update({glyph.name: glyph})
        else:
            self.glyphs.pop(glyph.name, None)
            self.standalone_glyphs.update({glyph.name: glyph})

        self._recalculate_glyphs()

    # string name variant, may want to investigate using glyph too
    def remove_glyph(self, glyph, remove_from="Both"):
        """
        Remove glyph from available pool.
        Glyphs can be explicitly removed from combinations, standalone, or both

        Glyphs are removed by name, if passed a :class:`Glyph` instance, will use the :attr:`~Glyph.name` attribute

        ``"Combinations"`` or ``"C"`` to remove from combinations
        ``"Standalone"`` or ``"S"`` to remove from standalone glyphs
        ``"Both"`` or ``"B"`` to remove from both

        Returns the glyph instance removed, or None if the glyph was not found

        :param glyph: glyph to remove
        :type glyph: :class:`Glyph` or :class:`str`
        :param remove_from: string identifier for where to remove from
        :return: glyph removed or :class:`None`
        :rtype: :class:`Glyph` or :class:`None`
        """

        if isinstance(glyph, Glyph):
            glyph = glyph.name

        remove_from = remove_from.lower()

        if remove_from in ("both", "b", "combinations", "c"):
            from_combination = self.glyphs.pop(glyph, None)
        if remove_from in ("both", "b", "standalone", "s"):
            from_standalone = self.standalone_glyphs.pop(glyph, None)

        self._recalculate_glyphs()

        return from_combination or from_standalone

    # ~~ IMAGE PROCESSING ~~

    @staticmethod
    def _fit_to_aspect(image, aspect_ratio):
        """
        Return copy of image, cropped to `aspect_ratio`.

        Cropping is applied evenly to both sides of image, so as to preserve center

        :param image:  An :class:`~PIL.Image.Image` object
        :type image: :class:`~PIL.Image.Image`
        :param aspect_ratio: target aspect ratio of width / height
        :type aspect_ratio: :class:`float`
        :return: An :class:`~PIL.Image.Image` object cropped to target aspect ratio
        :rtype: :class:`~PIL.Image.Image`
        """
        current_aspect = image.width / image.height
        if current_aspect < aspect_ratio:  # Image too tall
            perfect_height = image.width / aspect_ratio
            edge = (image.height - perfect_height) / 2
            image = image.crop((0, edge, image.width, perfect_height + edge))
        elif current_aspect > aspect_ratio:  # Image too wide
            perfect_width = image.height * aspect_ratio
            edge = (image.width - perfect_width) / 2
            image = image.crop((edge, 0, perfect_width + edge, image.height))

        return image

    def _preprocess(self, image, target_size, resize_mode, clip_limit, use_clahe, rescale_intensity, background_glyph):
        """
        Preprocess input image to better be reproduced by glyphs

        :param image: input :class:`~PIL.Image.Image` to be processed
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
         Given as total number of glyphs to be used across and down
        :type target_size: (:class:`int`, :class:`int`)
        :param resize_mode: any resize mode as able to be used by :meth:`~PIL.Image.Image.resize`
        :param clip_limit: clip limit as used by :meth:`~skimage.exposure.equalize_adapthist`
        :type clip_limit: :class:`float`
        :param use_clahe: enable or disable use of :meth:`~skimage.exposure.equalize_adapthist` on input image
        :type use_clahe: :class:`bool`
        :param rescale_intensity: enable or disable use of :meth:`~skimage.exposure.rescale_intensity`
        :type rescale_intensity: :class:`bool`
        :return: image after preprocessing has been applied
        :rtype: :class:`~PIL.Image.Image`
        """

        target_width, target_height = target_size
        desired_aspect = (self.glyph_width * target_width) / (self.glyph_height * target_height)
        image = self._fit_to_aspect(image, desired_aspect)

        sized_picture = image.resize((target_width * self.sample_x, target_height * self.sample_y), resize_mode)
        if background_glyph is not None:
            image_bands = sized_picture.getbands()
            if "A" in image_bands:
                alpha_channel = sized_picture.split()[image_bands.index("A")]
            else:
                alpha_channel = Image.new("L", sized_picture.size, "white")
        sized_picture = sized_picture.convert("L")

        if use_clahe or rescale_intensity:
            sized_picture = np.asarray(sized_picture)

            if min(target_size) > 1 and use_clahe:
                sized_picture = exposure.equalize_adapthist(sized_picture, clip_limit=clip_limit)

            # TODO Something is screwy with the current contrast methods, need to investigate
            self.value_extrema = (150, 250)

            if rescale_intensity:
                sized_picture = exposure.rescale_intensity(sized_picture, out_range=self.value_extrema)

            sized_picture = Image.fromarray(sized_picture.astype("uint8"))

        if background_glyph is not None:
            sized_picture.putalpha(alpha_channel)
        return sized_picture

    def _chunk(self, image_data, target_width):
        """
        Separate `image_data` into chunks, according to :attr:`~Glyph.sample_x` and :attr:`~Glyph.self.sample_y`

        Working from left to right, top to bottom of data representing an input image,
                produces lists of data corresponding to a region of the full image
                that are :attr:`~Glyph.sample_x` by :attr:`~Glyph.sample_y` in size.

        :param image_data: list of image data specifying pixel values in range 0->255
        :type image_data: [:class:`int`]
        :param target_width: width of target image as measured in glyphs
        :type target_width: :class:`int`
        :return: list of chunks, each of which are a list of integer values from source `image_data`
        :rtype: [[:class:`int`]]
        """
        chunks = []
        height = len(image_data) // (target_width * self.sample_y * self.sample_x)
        for y in range(height):
            rows = range(self.sample_y * y, self.sample_y * (y + 1))
            for x in range(target_width):
                columns = range(self.sample_x * x, self.sample_x * (x + 1))
                chunk = [image_data[column + row * target_width * self.sample_x] for row in rows for column in columns]
                chunks.append(chunk)
        return chunks

    # ~~ OUTPUT CREATION ~~

    # Could be split in 2, if wanted to. perform the histogram once, then apply on func call
    def _equalize_glyphs(self, image):
        """
        Adjust image histogram with the intention using each glyph equally.

        :param image: image to manipulate
        :type image: :class:`~PIL.Image.Image`
        :return: input image adjusted to glyph histogram
        :rtype: :class:`~PIL.Image.Image`
        """
        h = image.histogram()
        target_indices = []
        for i in range(256):
            count = self.average_values.count(i)
            if count:
                target_indices.extend([i] * count)

        histo = [_f for _f in h if _f]
        step = (functools.reduce(operator.add, histo) - histo[-1]) // len(target_indices)

        lut = []
        n = step // 2
        for i in range(256):
            position = min(n // step, len(target_indices) - 1)
            lut.append(target_indices[position])
            n += h[i]

        return image.point(lut)

    def _find_closest_glyph(self, target, cutoff, background_glyph):
        """
        Determine closest glyph available to `target` data

        `cutoff` value can be used to specify frequency with which glyphs will be
        replaced by simpler glyphs that are not quite as close to target.
        A value of 0.0 will permit no substitutions, always using the best glyph.
        Higher values will allow less similar glyphs to be used, if they comprise of fewer component pieces.

        :param target: data of target region of image, given as a list of integers,
         range 0->255 listed from left to right, top to bottom.
        :type target: [:class:`int`]
        :param cutoff: value used to determine replacement with a
         simpler glyph that is not quite as good a match to `target`.
        :type cutoff: :class:`float`
        :return: tuple of best matched :class:`Glyph` found to `target`
         and distance between target and said glyph.
         Distance is given as Euclidian distance in :attr:`~Glyph.sample_x` * :attr:`~Glyph.sample_y` dimensional value space.
        :rtype: (:class:`Glyph`, :class:`float`)
        """

        # TODO: may want to easy out if we're at glyph depth of 1?

        background_distance = None

        if background_glyph is not None:
            is_transparent = [alpha < 255 for value, alpha in target]
            if all(is_transparent):  # if deemed transparent enough
                return background_glyph, None  # using None for distance
            elif any(is_transparent):  # some transparency, merge in background glyph
                background = background_glyph.fingerprint.getdata()
                target = [(target_value * alpha/255) + (back_value * (255 - alpha)/255)
                          for back_value, (target_value, alpha) in zip(background, target)]
                background_distance = euclidean(background, target)
            else:  # otherwise strip alpha, continue as normal
                target = [value for value, alpha in target]

        neighbours = []
        for tree_set in self.tree_sets:
            tree = tree_set.tree
            distance, index = tree.query(target)
            neighbours.append((tree_set, distance, index))

        best_tree_set, best_distance, best_index = min(neighbours, key=lambda x: x[1])
        best_glyph = best_tree_set.glyph_set[best_index]

        # We permit background glyph use in semi-transparent areas, if best match
        if background_distance is not None:
            if background_distance < best_distance:
                best_distance = background_distance
                best_glyph = background_glyph

        max_stack_size = best_tree_set.stack_size

        for tree_set, distance, index in neighbours[:max_stack_size-1]:

            distance_diff = distance - best_distance
            stack_size_diff = best_tree_set.stack_size - tree_set.stack_size
            rmd = self._root_mean_square_distance(target, tree_set)

            if (distance_diff / (stack_size_diff * rmd)) < cutoff:
                return tree_set.glyph_set[index], distance

        return best_glyph, best_distance

    def _compose_calculation(self, result, target_width, target_height):
        """
        Create calculation demonstration image, composed of glyph :attr:`~Glyph.fingerprint_display` images.

        Useful in seeing how glyphs are matched to input image.

        :param result: list of :class:`Glyph`
        :type result: [:class:`Glyph`]
        :param target_width: number of :class:`Glyph` across the `result` represents
        :type target_width: :class:`int`
        :param target_height: number of :class:`Glyph` down the `result` represents
        :type target_height: :class:`int`
        :return: a :class:`~PIL.Image.Image` comprised of glyph :attr:`~Glyph.fingerprint_display` images
        :rtype: :class:`~PIL.Image.Image`
        """
        calculation = Image.new("L", (target_width * self.glyph_width, target_height * self.glyph_height))
        for i, glyph_ in enumerate(result):
            x = self.glyph_width * (i % target_width)
            y = self.glyph_height * (i // target_width)
            calculation.paste(glyph_.fingerprint_display, (x, y, x + self.glyph_width, y + self.glyph_height))
        return calculation

    def _compose_output(self, result, target_width, target_height):
        """
        Create output image, composed of glyph images.

        Shows the final output of converting an image to a set of glyphs.
        Very helpful to have visible when trying to type out result, for error checking.

        :param result: list of :class:`Glyph`
        :type result: [:class:`Glyph`]
        :param target_width: number of :class:`Glyph` across the `result` represents
        :type target_width: :class:`int`
        :param target_height: number of :class:`Glyph` down the `result` represents
        :type target_height: :class:`int`
        :return: a :class:`~PIL.Image.Image` comprised of glyph images,
         representing final output of conversion from image to glyphs
        :rtype: :class:`~PIL.Image.Image`
        """
        output = Image.new("L", (target_width * self.glyph_width, target_height * self.glyph_height))
        for i, glyph_ in enumerate(result):
            x = self.glyph_width * (i % target_width)
            y = self.glyph_height * (i // target_width)
            output.paste(glyph_.image, (x, y, x + self.glyph_width, y + self.glyph_height))
        return output

    def _instructions(self, result_glyphs, spacer, target_width, target_height, trailing_spacer=False):
        """
        Create instruction set for the given result glyphs.

        Instructions are optimised to contain the fewest groups when glyphs are combined.

        For every line of the image, a number of lines are created,
        equal to the depth of the most stacked glyph in the line

        :param result_glyphs: list of glyphs that compost the output, listed top left, across then down
        :type result_glyphs: [:class`Glyph`]
        :param spacer: spacing glyph, relating to a movement of 1 character over, with no glyph printed
        :type spacer: :class:`Glyph`
        :param target_width: width of image, measured in glyphs
        :type target_width: :class:`int`
        :param target_height: height of image, measured in glyphs
        :type target_height: :class:`int`
        :param trailing_spacer: enable inclusion of trailing spacer characters.
         This can be helpful for counting back from end of line
        :type trailing_spacer: :class:`bool`
        :return: List of instruction strings
        :rtype: [:class:`str`]
        """
        instructions = []

        row_counter_length = str(len(str(target_height)))

        lines = [result_glyphs[i * target_width: (i + 1) * target_width] for i in range(target_height)]
        for line_number, line in enumerate(lines):
            line_columns = []
            last_column = []
            for character in line:
                components = character.components
                elements = max(len(last_column), len(components))
                column = [spacer] * elements
                indexes = list(range(0, elements))
                deferred = []
                # Match up position of characters that were also in last composite glyph
                for glyph_atom in components:
                    if glyph_atom in last_column:
                        index = last_column.index(glyph_atom)
                        column[index] = glyph_atom
                        indexes.remove(index)
                    else:
                        deferred.append(glyph_atom)
                # Remianing components fill in the remianing spaces
                for glyph_atom, index in zip(deferred, indexes):
                    column[index] = glyph_atom

                last_column = column
                line_columns.append(column)

            rows = list(itertools.zip_longest(*line_columns, fillvalue=spacer))
            row_letters = self._iter_all_strings()

            for row_number, row in enumerate(rows):
                glyph_groups = itertools.groupby(row, key=lambda glyph: glyph.name)
                glyph_groups = [(key, list(group)) for key, group in glyph_groups]

                if not trailing_spacer:
                    # remove last group if it contains the spacer character
                    if glyph_groups[-1][1][0] == spacer:
                        glyph_groups = glyph_groups[:-1]

                groups = [str(len(list(group))) + key for key, group in glyph_groups]

                if len(rows) > 1:
                    row_letter = next(row_letters)
                else:
                    row_letter = ' '

                out_line = '{number:0' + row_counter_length + '}{letter}| {inst}'
                instructions.append(out_line.format(number=line_number, letter=row_letter, inst=' '.join(groups)))

        return instructions

    @staticmethod
    def _root_mean_square_distance(point, tree_set):
        """
        Calculate root mean square distance of a point from points in given tree set.

        Uses centroid to avoid brute force calculation.

        .. math::
            \sqrt{\\frac{1}{N}\sum_{i=1}^N (x_i - a)^2} = \sqrt{(m - a)^2 + \\frac{1}{N}\sum_{i=1}^N (x_i - m)^2}

            N is number of points
            m is centroid of points
            x_i is a point of the set
            a is target point

        :param array_like point: point from which mean square distance is calculated
        :param tree_set: tree set to be compared against, contains centroid and mean square from centroid
        :type tree_set: :class:`~typograph.tree_set`
        :return: root mean square distance of point from points given by tree set
        :rtype: :class:`float`
        """
        centroid = tree_set.centroid
        mean_square_from_centroid = tree_set.mean_square_from_centroid
        square_distance_from_centroid = ((np.array(point) - centroid) ** 2).sum()
        return np.sqrt(square_distance_from_centroid + mean_square_from_centroid)

    @staticmethod
    def _iter_all_strings():
        """
        Generator of Excel-like lowercase row letters

        e.g. a, b, c, ... z, aa, ab
        useful for cases in which instructions require multiple lines per character row

        :return: generator of excel-like string identifiers
        :rtype: generator
        """
        size = 1
        while True:
            for s in itertools.product(string.ascii_lowercase, repeat=size):
                yield "".join(s)
            size += 1

    def image_to_text(self, image, target_size=(60, 60), cutoff=0.3, resize_mode=Image.LANCZOS, clip_limit=0.02,
                      use_clahe=True, rescale_intensity=True, instruction_spacer=None, background_glyph=None):
        """
        Convert image into a glyph version, using the instance's glyphs.

        :param image: input :class:`~PIL.Image.Image` to be processed and converted
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
         Given as total number of glyphs to be used across and down
        :type target_size: (:class:`int`, :class:`int`)
        :param resize_mode: any resize mode as able to be used by :meth:`~PIL.Image.Image.resize`
        :param clip_limit: clip limit as used by :meth:`~skimage.exposure.equalize_adapthist`
        :type clip_limit: :class:`float`
        :param use_clahe: enable or disable use of :meth:`~skimage.exposure.equalize_adapthist` on input image
        :type use_clahe: :class:`bool`
        :param rescale_intensity: enable or disable use of :meth:`~skimage.exposure.rescale_intensity`
        :type rescale_intensity: :class:`bool`
        :param cutoff: cutoff level for near-enough glyph replacement. A value of 0.0 will permit no replacements
        :type cutoff: :class:`float`
        :param instruction_spacer: glyph to be used to represent moving the typing position one step, without adding ink
        :type instruction_spacer: :class:`Glyph`
        :param background_glyph: glyph to fill background of transparent image with
        :type background_glyph: :class:`Glyph`
        :return: a :class:`~typo_graphics.typograph.typed_art` object, containing construction, output and instructions, after preprocessing
        :rtype: :class:`~typo_graphics.typograph.typed_art`
        """

        preprocessed_image = self._preprocess(image=image, target_size=target_size, resize_mode=resize_mode,
                                              clip_limit=clip_limit, use_clahe=use_clahe,
                                              rescale_intensity=rescale_intensity, background_glyph=background_glyph)

        calc, output, inst_str = self._convert(image=preprocessed_image, target_size=target_size, cutoff=cutoff,
                                               instruction_spacer=instruction_spacer, background_glyph=background_glyph)
        return typed_art(calc, output, inst_str)

    def _convert(self, image, target_size, cutoff, instruction_spacer, background_glyph):
        """
        Raw conversion of image to glyphs, no preprocessing is performed.

        :param image: input :class:`~PIL.Image.Image` to be processed and converted
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
         Given as total number of glyphs to be used across and down
        :type target_size: (:class:`int, :class:`int`)
        :param cutoff: cutoff level for near-enough glyph replacement. A value of 0.0 will permit no replacements
        :type cutoff: :class:`float`
        :param instruction_spacer: glyph to be used to represent moving the typing position one step, without adding ink
        :type instruction_spacer: :class:`Glyph`
        :return: a :class:`~typo_graphics.typograph.typed_art` object, containing construction, output and instructions
        :rtype: :class:`~typo_graphics.typograph.typed_art`
        """

        target_width, target_height = target_size

        image_data = list(image.getdata())
        target_parts = self._chunk(image_data, target_width=target_width)

        result = []
        for section in target_parts:
            glyph, distance = self._find_closest_glyph(section, cutoff=cutoff, background_glyph=background_glyph)
            result.append(glyph)

        calculation = self._compose_calculation(result, target_width=target_width, target_height=target_height)
        output = self._compose_output(result, target_width=target_width, target_height=target_height)

        if instruction_spacer is None:
            blank = Image.new("L", (25, 48), 'white')
            instruction_spacer = Glyph(name='sp', image=blank)

        instruction_string = '\n'.join(self._instructions(result, spacer=instruction_spacer,
                                                          target_width=target_width, target_height=target_height))

        return calculation, output, instruction_string
