from glyph import Glyph
from collections import namedtuple
import functools
import itertools
import operator
from PIL import Image
import os
import json
from contextlib import suppress
import numpy as np
from scipy.spatial import cKDTree
import string
from skimage import exposure


tree_set = namedtuple('tree_set', ['glyph_set', 'tree', 'centroid',
                                   'mean_square_from_centroid', 'stack_size'])
tree_set.__doc__ = """
Named tuple container for information regarding sets of glyphs

May be unpacked, or accessed using member names
(`glyph_set`, `tree`, `centroid`, `mean_square_from_centroid`, `stack_size`)

:param glyph_set: list containing a collection of glyphs 
:type glyph_set: list(:class:`~glyph.Glyph`)
:param tree: a :class:`~scipy.spatial.cKDTree` instantiated with the glyphs of `glyph_set`
:type tree: :class:`~scipy.spatial.cKDTree`
:param array_like centroid: position of centroid in `sample_x` * `sample_y` parameter space
:param float mean_square_from_centroid: mean square distance of glyphs from centroid
:param int stack_size: number of fundamental glyphs used to compose each glyph in `glyph_set`
"""

typed_art = namedtuple('typed_art', ['calculation', 'output', 'instructions'])

typed_art.__doc__ = """
Named tuple container for output of :meth:`~ArtTyping.image_to_text`

May be unpacked, or accessed using member names
(`calculation`, `output`, `instructions`)

:param calculation: an :class:`~PIL.Image.Image` object, showing the `fingerprint_display` images, 
composed according to the result
:type calculation: :class:`~PIL.Image.Image`
:param output: an :class:`~PIL.Image.Image` object, showing the composed glyph result
:type output: :class:`~PIL.Image.Image`
:param string instructions: string of instruction lines, separated by \n
"""

# TODO dump list
# Support for transparent images, with any glyph as background
# --> Could almost be done in a postprocess step?
# --> leaning toward not implementing, but providing a how-to recipe for this
# Enhanced image production for single glyph stacking
# --> looks to be issue with how we calculate self.value_extrema


class ArtTyping:
    """
    Class for processing glyphs for the creation of images.

    This class primarily is designed to be used to convert an image into a set of instructions,
    that can be typed on a typewriter to reproduce the image.

    Class methods :meth:`~ArtTyping.from_glyph_sheet` and
    :meth:`~ArtTyping.from_directory` present other initialisation options

    """

    def __init__(self, glyph_images, samples=(3, 3), glyph_depth=2):
        """
        Create :class:`ArtTyping` object with glyphs specified in `glyph_images`

        Exposes :meth:`~ArtTyping.image_to_text` , which can be used to convert any supplied image into glyph format

        :param glyph_images: dictionary of images, keyed with glyph names
        :type glyph_images: dict(str: :class:`~PIL.Image.Image`)
        :param samples: number of samples across and down, used to match glyphs to input images
        :type samples: tuple(int, int)
        :param int glyph_depth: maximum number of glyphs to stack into single characters
        """

        self.samples = samples
        self.sample_x, self.sample_y = samples
        self.glyphs = {}
        for name, image in glyph_images.items():
            glyph_ = Glyph(name, image, samples=samples)
            # TODO perhaps we no longer need this dict format
            self.glyphs.update({glyph_.name: glyph_})

        # TODO ugly, would be cleaner if glyphs were in a sequence
        self.glyph_width, self.glyph_height = list(self.glyphs.values())[0].image.size
        self.glyph_depth = glyph_depth
        self.tree_sets = self._calculate_trees()
        self.average_values = self._average_glyph_values()
        self.value_extrema = self._glyph_value_extrema()

    @classmethod
    def from_glyph_sheet(cls, glyph_sheet, number_glyphs=None, glyph_dimensions=None, grid_size=None,
                         glyph_names=None, spacing=(0, 0), **kwargs):
        """
        Create :class:`ArtTyping` object with glyphs as extracted from `glyph_sheet`

        Allows for a single :class:`~PIL.Image.Image` to be used to provide glyph images

        :param glyph_sheet: glyph sheet :class:`~PIL.Image.Image`, to be split into glyphs
        :type glyph_sheet: :class:`~PIL.Image.Image`
        :param int number_glyphs: total number of glyphs present in `glyph_sheet`
        :param glyph_dimensions: pixel dimensions of glyphs given as (width, height)
        :type glyph_dimensions: tuple(int, int)
        :param grid_size: if given, number of (rows, columns) that glyphs are arranged in
        :type grid_size: tuple(int, int)
        :param glyph_names: list of glyph names listed left to right, top to bottom
        :type glyph_names: list(str)
        :param spacing: tuple of integer pixel spacing between adjacent glyphs,
                        as number of pixels between glyphs horizontally and vertically
        :type spacing: tuple(int, int)
        :param kwargs: optional keyword arguments as for :class:`ArtTyping`
        :return: An :class:`ArtTyping` object using glyphs images extracted from `glyph_sheet`
        :rtype: :class:`ArtTyping`
        :raises TypeError: if `number_glyphs` is not given
        :raises TypeError: if neither `grid_size` or `glyph_dimensions` are specified
        """

        if number_glyphs is None:
            raise TypeError("from_glyphsheet() missing required argument 'number_glyphs'")

        if (glyph_dimensions is None) or (grid_size is None):
            raise TypeError("from_glyphsheet() missing required argument "
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
            grid_width = (sheet_width + spacing_x) / (glyph_width + spacing_x)
            grid_height = (sheet_height + spacing_y) / (glyph_height + spacing_y)

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
        Create :class:`ArtTyping` object loading glyph images from a given directory.

        In addition to images, the directory can contain a name_map.json file
        giving alias names for glyphs located in the directory

        :param string glyph_directory: A file path for directory containing glyph images
        :param kwargs: optional keyword arguments as for :class:`ArtTyping`
        :return: An :class:`ArtTyping` object using glyphs images found from directory
        :rtype: :class:`ArtTyping`
        """
        with suppress(FileNotFoundError):  # look for a name_map.json, but continue if not found
            with open(os.path.join(glyph_directory, 'name_map.json'), 'r', encoding="utf-8") as fp:
                glyph_names = json.load(fp)

        glyphs = {}

        for filename in os.listdir(glyph_directory):
            with suppress(IOError):  # skips over any files that Image cannot open
                name = os.path.splitext(filename)[0]
                name = glyph_names.get(name, name)
                path = os.path.join(glyph_directory, filename)
                image = Image.open(path)
                glyphs.update({name: image})

        return cls(glyphs, **kwargs)

    # ~~ GLYPH WORK ON INIT ~~

    def _calculate_trees(self):
        """
        Calculate tree sets for input glyphs, combined up to `self.glyph_depth`

        :return: list of tree sets
        :rtype: list(:class:`tree_set`)
        """
        tree_sets = []

        for stack_size in range(1, self.glyph_depth + 1):
            glyph_set = list(self._combine_glyphs(stack_size).values())
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

        :param int depth: number of glyphs to combine into composite glyphs
        :return: dictionary of combination glyphs, using glyph names as keys
        :rtype: dict
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
        :rtype: list(float)
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
        :rtype: tuple(float, float)
        """
        return min(self.average_values), max(self.average_values)

    # ~~ IMAGE PROCESSING ~~

    @staticmethod
    def _fit_to_aspect(image, aspect_ratio):
        """
        Return copy of image, cropped to `aspect_ratio`.

        Cropping is applied evenly to both sides of image, so as to preserve center

        :param image:  An :class:`~PIL.Image.Image` object
        :type image: :class:`~PIL.Image.Image`
        :param float aspect_ratio: target aspect ratio of width / height
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

    def _preprocess(self, image, target_size=(60, 60), resize_mode=Image.LANCZOS, clip_limit=0.02,
                    use_clahe=True, rescale_intensity=True):
        """
        Preprocess input image to better be reproduced by glyphs

        :param image: input :class:`~PIL.Image.Image` to be processed
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
                            Given as total number of glyphs to be used across and down
        :type target_size: tuple(int, int)
        :param resize_mode: any resize mode as able to be used by :meth:`~PIL.Image.Image.resize`
        :param float clip_limit: clip limit as used by :meth:`~skimage.exposure.equalize_adapthist`
        :param bool use_clahe: enable or disable use of :meth:`~skimage.exposure.equalize_adapthist on input image
        :param bool rescale_intensity: enable or disable use of :meth:`skimage.exposure.rescale_intensity`
        :return: image after preprocessing has been applied
        :rtype: :class:`~PIL.Image.Image`
        """

        target_width, target_height = target_size
        desired_aspect = (self.glyph_width * target_width) / (self.glyph_height * target_height)
        image = self._fit_to_aspect(image, desired_aspect)

        sized_picture = image.resize((target_width * self.sample_x, target_height * self.sample_y), resize_mode)
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

        return sized_picture

    def _chunk(self, image_data, target_width):
        """
        Separate `image_data` into chunks, according to `self.sample_x` and `self.sample_y`

        Working from left to right, top to bottom of data representing an input image,
                produces lists of data corresponding to a region of the full image
                that are `self.sample_x` by `self.sample_y` in size.

        :param image_data: list of image data specifying pixel values in range 0->255
        :type image_data: list(int)
        :param int target_width: width of target image as measured in glyphs
        :return: list of chunks, each of which are a list of integer values from source `image_data`
        :rtype: list(list(int))
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

    def _find_closest_glyph(self, target, cutoff=0.3):
        """
        Determine closest glyph available to `target` data

        `cutoff` value can be used to specify frequency with which glyphs will be
        replaced by simpler glyphs that are not quite as close to target.
        A value of 0.0 will permit no substitutions, always using the best glyph.
        Higher values will allow less similar glyphs to be used, if they comprise of fewer component pieces.

        :param target: data of target region of image, given as a list of integers, range 0->255
                        listed from left to right, top to bottom.
        :type target: list(int)
        :param float cutoff: value used to determine replacement with a
                            simpler glyph that is not quite as good a match to `target`.
        :return: tuple of best matched :class:`~glyph.Glyph` found to `target`
                 and distance between target and said glyph.
                 Distance is given as Euclidian distance in `self.sample_x` * `self.sample_y` dimensional value space
        :rtype: tuple(:class:`~glyph.Glyph`, float)
        """

        # TODO: may want to easy out if we're at glyph depth of 1?

        neighbours = []
        for tree_set in self.tree_sets:
            tree = tree_set.tree
            distance, index = tree.query(target)
            neighbours.append((tree_set, distance, index))

        best_tree_set, best_distance, best_index = min(neighbours, key=lambda x: x[1])

        max_stack_size = best_tree_set.stack_size

        for tree_set, distance, index in neighbours[:max_stack_size-1]:

            distance_diff = distance - best_distance
            stack_size_diff = best_tree_set.stack_size - tree_set.stack_size
            rmd = self._root_mean_square_distance(target, tree_set)

            if (distance_diff / (stack_size_diff * rmd)) < cutoff:
                return tree_set.glyph_set[index], distance

        return best_tree_set.glyph_set[best_index], best_distance

    def _compose_calculation(self, result, target_width, target_height):
        """
        Create calculation demonstration image, composed of glyph `fingerprint_display` images.

        Useful in seeing how glyphs are matched to input image.

        :param result: list of :class:`~glyph.Glyph`
        :type result: list(:class:`~glyph.Glyph`)
        :param int target_width: number of :class:`~glyph.Glyph` across the `result` represents
        :param int target_height: number of :class:`~glyph.Glyph` down the `result` represents
        :return: a :class:`~PIL.Image.Image` comprised of glyph `fingerprint_display` images
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

        :param result: list of :class:`~glyph.Glyph`
        :type result: list(:class:`~glyph.Glyph`)
        :param int target_width: number of :class:`~glyph.Glyph` across the `result` represents
        :param int target_height: number of :class:`~glyph.Glyph` down the `result` represents
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
        :type tree_set: :class:`tree_set`
        :return: root mean square distance of point from points given by tree set
        :rtype: float
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
                      use_clahe=True, rescale_intensity=True, instruction_spacer=None):
        """
        Convert image into a glyph version, using the instance's glyphs.

        parameters as for :meth:`~ArtTyping._preprocess`
        :param image: input :class:`~PIL.Image.Image` to be processed and converted
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
                            Given as total number of glyphs to be used across and down
        :type target_size: tuple(int, int)
        :param resize_mode: any resize mode as able to be used by :meth:`~PIL.Image.Image.resize`
        :param float clip_limit: clip limit as used by :meth:`~skimage.exposure.equalize_adapthist`
        :param bool use_clahe: enable or disable use of :meth:`~skimage.exposure.equalize_adapthist on input image
        :param bool rescale_intensity: enable or disable use of :meth:`skimage.exposure.rescale_intensity`

        parameters as for :meth:`~ArtTyping._convert`
        :param float cutoff: cutoff level for near-enough glyph replacement. A value of 0.0 will permit no replacements
        :param instruction_spacer: glyph to be used to represent moving the typing position one step, without adding ink
        :type instruction_spacer: :class:`~glyph.Glyph`
        :return: a :class:`typed_art` object, containing construction, output and instructions, after preprocessing
        :rtype: :class:`typed_art`
        """

        preprocessed_image = self._preprocess(image, target_size=target_size, resize_mode=resize_mode,
                                              clip_limit=clip_limit, use_clahe=use_clahe,
                                              rescale_intensity=rescale_intensity)

        calc, output, inst_str = self._convert(preprocessed_image, target_size, cutoff, instruction_spacer)
        return typed_art(calc, output, inst_str)

    def _convert(self, image, target_size=(60, 60), cutoff=0.3, instruction_spacer=None):
        """
        Raw conversion of image to glyphs, no preprocessing is performed.

        :param image: input :class:`~PIL.Image.Image` to be processed and converted
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
                            Given as total number of glyphs to be used across and down
        :type target_size: tuple(int, int)
        :param float cutoff: cutoff level for near-enough glyph replacement. A value of 0.0 will permit no replacements
        :param instruction_spacer: glyph to be used to represent moving the typing position one step, without adding ink
        :type instruction_spacer: :class:`~glyph.Glyph`
        :return: a :class:`typed_art` object, containing construction, output and instructions
        :rtype: :class:`typed_art`
        """

        target_width, target_height = target_size

        image_data = list(image.getdata())
        target_parts = self._chunk(image_data, target_width=target_width)

        result = []
        for section in target_parts:
            glyph, distance = self._find_closest_glyph(section, cutoff=cutoff)
            result.append(glyph)

        calculation = self._compose_calculation(result, target_width=target_width, target_height=target_height)
        output = self._compose_output(result, target_width=target_width, target_height=target_height)

        if instruction_spacer is None:
            blank = Image.new("L", (25, 48), 'white')
            instruction_spacer = Glyph(name='sp', image=blank)

        instruction_string = '\n'.join(self._instructions(result, spacer=instruction_spacer,
                                                          target_width=target_width, target_height=target_height))

        return calculation, output, instruction_string