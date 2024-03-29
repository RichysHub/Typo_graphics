import functools
import itertools
import json
import operator
import os
import string
from collections import namedtuple, Counter
from contextlib import suppress

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.spatial.distance import euclidean
from skimage import exposure
from typo_graphics import Glyph

TreeSet = namedtuple('TreeSet', ['glyph_set', 'tree', 'centroid',
                                 'mean_square_from_centroid', 'stack_size'])
TreeSet.__doc__ = """
Named tuple container for information regarding sets of glyphs

May be unpacked, or accessed using member names
:attr:`~typo_graphics.typograph.TreeSet.glyph_set`,
:attr:`~typo_graphics.typograph.TreeSet.tree`,
:attr:`~typo_graphics.typograph.TreeSet.centroid`,
:attr:`~typo_graphics.typograph.TreeSet.mean_square_from_centroid`,
:attr:`~typo_graphics.typograph.TreeSet.stack_size`

:param glyph_set: list containing a collection of glyphs 
:type glyph_set: [:class:`Glyph`]
:param tree: a :class:`~scipy.spatial.cKDTree` instantiated with the glyphs
 of :attr:`~typo_graphics.typograph.TreeSet.glyph_set`
:type tree: :class:`~scipy.spatial.cKDTree`
:param array_like centroid: position of centroid in :attr:`~Glyph.sample_x` * :attr:`~Glyph.sample_y` parameter space
:param mean_square_from_centroid: mean square distance of glyphs from centroid
:type mean_square_from_centroid: :class:`float`
:param stack_size: number of fundamental glyphs used to compose each glyph
 in :attr:`~typo_graphics.typograph.TreeSet.glyph_set`
:type stack_size: :class:`int`
"""

TypedArt = namedtuple('TypedArt', ['calculation', 'output', 'instructions'])
TypedArt.__doc__ = """
Named tuple container for output of :meth:`~Typograph.image_to_text`

May be unpacked, or accessed using member names
:attr:`~typo_graphics.typograph.TypedArt.calculation`,
:attr:`~typo_graphics.typograph.TypedArt.output`,
:attr:`~typo_graphics.typograph.TypedArt.instructions`

:param calculation: an :class:`~PIL.Image.Image` object, showing the :attr:`~Glyph.fingerprint_display` images, 
 composed according to the result
:type calculation: :class:`~PIL.Image.Image`
:param output: an :class:`~PIL.Image.Image` object, showing the composed glyph result
:type output: :class:`~PIL.Image.Image`
:param instructions: string of instruction lines, separated by \n
:type instructions: :class:`string`
"""


class Typograph:
    """
    Class for processing glyphs for the creation of images.

    This class primarily is designed to be used to convert an image into a set of instructions,
    that can be typed on a typewriter to reproduce the image.

    Class methods :meth:`~Typograph.from_glyph_sheet` and
    :meth:`~Typograph.from_directory` present other initialisation options.

    Class attribues:
     - :attr:`inbuilt_typewriters`, list of inbuilt typewriters for which glyphs can be loaded.
     - :attr:`glyph_sheet_paths`, dictionary of paths to inbuilt typewriter glyph sheets.

    Exposes :meth:`~Typograph.image_to_text` , which can be used to convert any supplied image into glyph format.

    Exposes following instance attributes:
     - :attr:`glyphs`, dictionary of typeable glyphs, keyed by glyph names, used in combinations.
     - :attr:`standalone_glyphs`, dictionary of typeable glyphs, keyed by glyph names, that are only to be used alone.
     - :attr:`glyph_depth`, integer detailing maximum glyphs that are combined together for each combination glyph.
     - :attr:`sample_x`, integer of samples across the glyph images.
     - :attr:`sample_y`, integer of samples down the glyph images.
     - :attr:`samples`, tuple of ints governing how glyphs are down-sampled for matching.
     - :attr:`tree_sets`, list of :class:`~typo_graphics.typograph.TreeSet` objects containing all combination glyphs,
        and associated values.
    """
    def __init__(self, *, glyph_images=None, samples=(3, 3), glyph_depth=2, typewriter=None, carriage_width=None):
        """
        Create :class:`Typograph` object, optionally pass glyph images to use.

        Defaults to using glyphs for the SR100 typewriter inbuilt glyph set.

        :param glyph_images: dictionary of images, keyed with glyph names.
        :type glyph_images: {:class:`str`: :class:`~PIL.Image.Image`}
        :param samples: number of samples across and down, used to match glyphs to input images.
         If only :class:`int` given, uses that value for both directions.
        :type samples: (:class:`int`, :class:`int`) or :class:`int`
        :param glyph_depth: maximum number of glyphs to stack into single characters.
        :type glyph_depth: :class:`int`
        :param typewriter: name of typewriter for which output is created. If glyph images are not provided, this name
         is used to look for an inbuilt typewriter's glyph set.
         Valid values for which are given in :attr:`Typograph.inbuilt_typewriters`.
        :type typewriter: :class:`str`
        :param carriage_width: maximum width of glyphs typeable on the typewriter carriage.
        :type carriage_width: :class:`int`
        """
        if isinstance(samples, int):
            samples = (samples, samples)

        self.samples = samples
        self.sample_x, self.sample_y = samples
        self.typewriter = typewriter
        self.carriage_width = carriage_width
        if glyph_images is None:
            from typo_graphics import package_directory

            if typewriter is None or typewriter.lower() not in map(str.lower, self.inbuilt_typewriters):
                typewriter = 'SR100'

            typewriter = typewriter.lower()

            path_lookup = {name.lower(): path for name, path in self.glyph_sheet_paths.items()}
            glyph_sheet_path = path_lookup[typewriter]
            glyph_sheet = os.path.join(package_directory, glyph_sheet_path)
            glyph_images, self.typewriter, carriage_width = self._extract_from_glyph_sheet(glyph_sheet)

            # Carriage width is explicitly allowed to be overridden in the init
            if self.carriage_width is None:
                self.carriage_width = carriage_width

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

    glyph_sheet_paths = {'SR100': './Glyphs/SR100.png',
                         'Imperial': './Glyphs/Imperial.png',
                         'Super Riter': './Glyphs/Super Riter.png',
                         'Blue Bird': './Glyphs/Blue Bird.png',
                         'Linea 98': './Glyphs/Linea 98.png',
                         'Linea 98 half-linespace': './Glyphs/Linea 98 half-linespace.png',
                         'Brailler': './Glyphs/Brailler.png',
                         }
    inbuilt_typewriters = list(glyph_sheet_paths.keys())

    # TODO: typewriter and carriage_width are useful for other methods of creating a Typograph object. May be moved
    @classmethod
    def from_glyph_sheet(cls, glyph_sheet, number_glyphs=None, glyph_dimensions=None, grid_size=None,
                         glyph_names=None, spacing=None, **kwargs):
        """
        Create :class:`Typograph` object with glyphs as extracted from `glyph_sheet`

        Allows for a single :class:`~PIL.Image.Image` to be used to provide glyph images.

        :param glyph_sheet: glyph sheet :class:`~PIL.Image.Image`, to be split into glyphs,
         a filename for such image, or an open binary file object.
        :type glyph_sheet: :class:`~PIL.Image.Image` or :class:`string` or open file
        :param number_glyphs: total number of glyphs present in `glyph_sheet`,
         if omitted, glyph_names must be present, and its length will be used.
        :type number_glyphs: :class:`int` or None
        :param glyph_dimensions: pixel dimensions of glyphs given as (width, height).
        :type glyph_dimensions: (:class:`int`, :class:`int`)
        :param grid_size: if given, number of (rows, columns) that glyphs are arranged in.
        :type grid_size: (:class:`int`, :class:`int`)
        :param glyph_names: list of unique glyph names listed left to right, top to bottom.
        :type glyph_names: [:class:`str`]
        :param spacing: tuple of integer pixel spacing between adjacent glyphs,
         as number of pixels between glyphs horizontally and vertically.
        :type spacing: (:class:`int`, :class:`int`)
        :param kwargs: optional keyword arguments as for :class:`Typograph`.
        :return: An :class:`Typograph` object using glyphs images extracted from `glyph_sheet`
        :rtype: :class:`Typograph`
        :raises TypeError: if `number_glyphs` is not given.
        :raises TypeError: if neither `grid_size` or `glyph_dimensions` are specified.
        :raises ValueError: if duplicates in glyph_names
        """

        glyph_images, typewriter, carriage_width = cls._extract_from_glyph_sheet(glyph_sheet=glyph_sheet,
                                                                                 number_glyphs=number_glyphs,
                                                                                 glyph_dimensions=glyph_dimensions,
                                                                                 grid_size=grid_size,
                                                                                 glyph_names=glyph_names,
                                                                                 spacing=spacing)

        # We update the kwargs, if these values were not given
        meta_data = {'typewriter': typewriter, 'carriage_width': carriage_width}
        meta_data.update(kwargs)
        return cls(glyph_images=glyph_images, **meta_data)

    @staticmethod
    def _extract_from_glyph_sheet(glyph_sheet, number_glyphs=None, glyph_dimensions=None, grid_size=None,
                                  glyph_names=None, spacing=None):

        """
        Given an image, or file for that image, split out individual glyph images from a glyph sheet.

        :param glyph_sheet: glyph sheet :class:`~PIL.Image.Image`, to be split into glyphs,
         a filename for such image, or an open binary file object.
        :type glyph_sheet: :class:`~PIL.Image.Image` or :class:`string` or open file
        :param number_glyphs: total number of glyphs present in `glyph_sheet`,
         if omitted, glyph_names must be present, and its length will be used.
        :type number_glyphs: :class:`int` or None
        :param glyph_dimensions: pixel dimensions of glyphs given as (width, height).
        :type glyph_dimensions: (:class:`int`, :class:`int`)
        :param grid_size: if given, number of (rows, columns) that glyphs are arranged in.
        :type grid_size: (:class:`int`, :class:`int`)
        :param glyph_names: list of unique glyph names listed left to right, top to bottom.
        :type glyph_names: [:class:`str`]
        :param spacing: tuple of integer pixel spacing between adjacent glyphs,
         as number of pixels between glyphs horizontally and vertically.
        :type spacing: (:class:`int`, :class:`int`)
        :return: tuple containing: list of glyph :class:`~PIL.Image.Image` objects, string name of typewriter,
         and total width of typewriter carriage.
        :raises FileNotFoundError: if image path does not resolve.
        """

        if not isinstance(glyph_sheet, Image.Image):
            # handle open file objects, and paths, retrieving data from any meta file
            # Bit messy
            (glyph_sheet, number_glyphs, glyph_dimensions, grid_size,
             glyph_names, spacing, typewriter, carriage_width) = Typograph._parse_glyph_sheet_file(
             glyph_sheet, number_glyphs, glyph_dimensions, grid_size,
             glyph_names, spacing)
        else:
            typewriter = None
            carriage_width = None

        if (glyph_dimensions is None) and (grid_size is None):
            raise TypeError("from_glyph_sheet() missing required keyword argument "
                            "'grid_size' or 'glyph_dimensions'")

        if number_glyphs is None:
            if glyph_names is None:
                raise TypeError("from_glyph_sheet() missing required keyword argument "
                                "'number_glyphs' or 'glyph_names'")
            else:
                number_glyphs = len(glyph_names)

        if glyph_names and len(glyph_names) != len(set(glyph_names)):
            duplicates = [name for name, count in Counter(glyph_names).items() if count > 1]
            raise ValueError("duplicate names in glyph_names: {}.".format(duplicates))

        sheet_width, sheet_height = glyph_sheet.size
        if spacing is None:
            spacing = (0, 0)
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
                    return glyph_images, typewriter, carriage_width

    @staticmethod
    def _parse_glyph_sheet_file(glyph_sheet, number_glyphs=None, glyph_dimensions=None, grid_size=None,
                                glyph_names=None, spacing=None):
        """
        Handle opening of file, loading any associated meta file, and extracting meta data.

        :param glyph_sheet: glyph sheet :class:`~PIL.Image.Image`, to be split into glyphs,
         a filename for such image, or an open binary file object.
        :type glyph_sheet: :class:`~PIL.Image.Image` or :class:`string` or open file

        :param number_glyphs: total number of glyphs present in `glyph_sheet`,
         if omitted, glyph_names must be present, and its length will be used.
        :type number_glyphs: :class:`int` or None
        :param glyph_dimensions: pixel dimensions of glyphs given as (width, height).
        :type glyph_dimensions: (:class:`int`, :class:`int`)
        :param grid_size: if given, number of (rows, columns) that glyphs are arranged in.
        :type grid_size: (:class:`int`, :class:`int`)
        :param glyph_names: list of unique glyph names listed left to right, top to bottom.
        :type glyph_names: [:class:`str`]
        :param spacing: tuple of integer pixel spacing between adjacent glyphs,
         as number of pixels between glyphs horizontally and vertically.
        :type spacing: (:class:`int`, :class:`int`)
        :return: tuple of :class:`~PIL.Image.Image` glyph image, followed by extracted values of number_glyphs,
         glyph_dimensions, grid_size, glyph_names and spacing, if no value was given
        :raises FileNotFoundError: if image path does not resolve.
        """

        glyph_sheet_image = Image.open(glyph_sheet)

        if isinstance(glyph_sheet, (bytes, str)):
            # is path of some description
            path_name = glyph_sheet
        else:
            # assume it's an open file object
            path_name = glyph_sheet.name

        base_path, _ = os.path.splitext(path_name)
        meta_path = base_path + '.json'

        meta_data = {}
        with suppress(FileNotFoundError):
            with open(meta_path, 'r', encoding="utf-8") as fp:
                meta_data = json.load(fp)

        if number_glyphs is None:
            number_glyphs = meta_data.get('number_glyphs', None)

        if (glyph_dimensions is None) and (grid_size is None):
            glyph_dimensions = meta_data.get('glyph_dimensions', None)
            grid_size = meta_data.get('grid_size', None)

        if glyph_names is None:
            glyph_names = meta_data.get('glyph_names', None)

        if spacing is None:
            spacing = meta_data.get('spacing', None)

        typewriter = meta_data.get('typewriter', None)

        carriage_width = meta_data.get('carriage_width', None)

        return (glyph_sheet_image, number_glyphs, glyph_dimensions, grid_size,
                glyph_names, spacing, typewriter, carriage_width)

    @classmethod
    def from_directory(cls, glyph_directory, **kwargs):
        """
        Create :class:`Typograph` object loading glyph images from a given directory.

        In addition to images, the directory can contain a name_map.json file
        giving alias names for glyphs located in the directory.

        :param glyph_directory: A file path for directory containing glyph images.
        :type glyph_directory: :class:`str`
        :param kwargs: optional keyword arguments as for :class:`Typograph`.
        :return: An :class:`Typograph` object using glyphs images found from directory.
        :rtype: :class:`Typograph`
        """
        glyph_images = cls._get_glyphs_from_directory(glyph_directory)
        return cls(glyph_images=glyph_images, **kwargs)

    @staticmethod
    def _get_glyphs_from_directory(glyph_directory):
        """
        Fetch glyph images from `glyph_directory` into dictionary keyed with names.

        :param glyph_directory: A file path for directory containing glyph images.
        :type glyph_directory: :class:`str`
        :return:  dictionary of images, keyed with glyph names.
        :rtype: {:class:`str`: :class:`~PIL.Image.Image`}
        """
        try:  # look for a name_map.json
            with open(os.path.join(glyph_directory, 'name_map.json'), 'r', encoding="utf-8") as fp:
                glyph_names = json.load(fp)
        except FileNotFoundError:  # didn't find it, sub a blank name_map
            glyph_names = {}

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

        :return: list of tree sets.
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

            tree_sets.append(TreeSet(glyph_set=glyph_set, tree=tree, centroid=centroid,
                                     mean_square_from_centroid=mean_square_from_centroid,
                                     stack_size=stack_size))

        return tree_sets

    def _combine_glyphs(self, depth):
        """
        Calculate all unique combinations of `depth` number of glyphs.

        :param depth: number of glyphs to combine into composite glyphs.
        :type depth: :class:`int`
        :return: dictionary of combination glyphs, using glyph names as keys.
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

        :return: list of average pixel values, no given order.
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
        Extrema of average pixel values for all glyphs.

        :return: tuple of (min, max) pixel values.
        :rtype: (:class:`float`, :class:`float`)
        """
        return min(self.average_values), max(self.average_values)

    def _recalculate_glyphs(self):
        """
        Update glyph relevant attributes, for use whenever glyphs are changed.

        Updates:
        :attr:`~Typograph.tree_sets`
        :attr:`~Typograph.average_values`
        :attr:`~Typograph.value_extrema`
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

        :param glyph: glyph to add.
        :type glyph: :class:`Glyph`
        :param use_in_combinations: use this glyph in combinations, default False.
        :type use_in_combinations: :class:`bool`
        """
        if use_in_combinations:
            self.standalone_glyphs.pop(glyph.name, None)
            self.glyphs.update({glyph.name: glyph})
        else:
            self.glyphs.pop(glyph.name, None)
            self.standalone_glyphs.update({glyph.name: glyph})

        self._recalculate_glyphs()

    def remove_glyph(self, glyph, remove_from="Both"):
        """
        Remove glyph from available pool.

        Glyphs can be explicitly removed from combinations, standalone, or both.

        Glyphs are removed by name, if passed a :class:`Glyph` instance, will use the :attr:`~Glyph.name` attribute.

        * ``"Combinations"`` or ``"C"`` to remove from combinations
        * ``"Standalone"`` or ``"S"`` to remove from standalone glyphs
        * ``"Both"`` or ``"B"`` to remove from both

        Returns the glyph instance removed, or None if the glyph was not found.

        :param glyph: glyph to remove.
        :type glyph: :class:`Glyph` or :class:`str`
        :param remove_from: string identifier for where to remove from.
        :return: glyph removed or :class:`None`.
        :rtype: :class:`Glyph` or :class:`None`
        """
        if isinstance(glyph, Glyph):
            glyph = glyph.name

        remove_from = remove_from.lower()

        from_combination = None
        from_standalone = None

        if remove_from in ("both", "b", "combinations", "c"):
            from_combination = self.glyphs.pop(glyph, None)
        if remove_from in ("both", "b", "standalone", "s"):
            from_standalone = self.standalone_glyphs.pop(glyph, None)

        self._recalculate_glyphs()

        return from_combination or from_standalone

    # ~~ IMAGE PROCESSING ~~

    def _crop_to_max_size(self, image, max_size, resize_mode):
        """
        Return copy of image, cropped to fit within `max_size`.

        Cropping is applied evenly to both sides of image, so as to preserve center.

        Image is cropped so that max_size glyphs fit inside the image, then scaled to max_size(0) * self.samples(0) by
        max_size(1) * self.samples(1) pixels. As such, output image may appear squashed or stretched.

        :param image:  An :class:`~PIL.Image.Image` object.
        :type image: :class:`~PIL.Image.Image`
        :param max_size: maximum size in glyphs across and down.
        :type max_size: (:class:`int`, :class:`int`)
        :param resize_mode: any resize mode as able to be used by :meth:`~PIL.Image.Image.resize`.
        :return: Tuple of an :class:`~PIL.Image.Image` object cropped to fit within `max_size`,
         and the `max_size` tuple, to match return signature of :meth:`~Typograph._scale_to_max_size`.
        :rtype: (:class:`~PIL.Image.Image`, (:class:`int`, :class:`int`))
        """
        current_aspect = image.width / image.height
        max_width, max_height = max_size
        aspect_ratio = (self.glyph_width * max_width) / (self.glyph_height * max_height)

        if current_aspect < aspect_ratio:  # Image too tall
            perfect_height = image.width / aspect_ratio
            edge = (image.height - perfect_height) / 2
            image = image.crop((0, edge, image.width, perfect_height + edge))
        elif current_aspect > aspect_ratio:  # Image too wide
            perfect_width = image.height * aspect_ratio
            edge = (image.width - perfect_width) / 2
            image = image.crop((edge, 0, perfect_width + edge, image.height))

        image = image.resize((max_width * self.sample_x, max_height * self.sample_y), resize_mode)

        return image, max_size

    def _scale_to_max_size(self, image, max_size, resize_mode):
        """
        Return copy of image, scaled to fit within `max_size`.

        Values of ``None`` in `max_size` are treated as infinite available space in that dimension.
        If (``None``, ``None``), will match input image size to nearest whole glyph in each dimension.

        Output image ends up being scaled by the number of samples in that given dimension,
        as such it may appear distorted.

        :param image:  An :class:`~PIL.Image.Image` object.
        :type image: :class:`~PIL.Image.Image`
        :param max_size: maximum size in glyphs across and down.
        :type max_size: (:class:`int` or ``None``, :class:`int` or ``None``)
        :param resize_mode: any resize mode as able to be used by :meth:`~PIL.Image.Image.resize`.
        :return: Tuple of an :class:`~PIL.Image.Image` object scaled to fit within `max_size`,
         and a tuple of actual dimensions in glyphs. This elements of this tuple are, by definition, equal to or smaller
         than those in `max_size`.
        :rtype: (:class:`~PIL.Image.Image`, (:class:`int`, :class:`int`))
        """
        max_width, max_height = max_size
        image_aspect = image.width / image.height
        glyph_aspect = self.glyph_width / self.glyph_height
        scale_factor = image_aspect / glyph_aspect

        if max_width is None and max_height is None:
            result_width = image.width / self.glyph_width
            result_height = image.height / self.glyph_height
        elif max_width is None:
            result_height = max_height
            result_width = max_height * scale_factor
        elif max_height is None:
            result_width = max_width
            result_height = max_width / scale_factor
        else:
            result_width = max_width
            result_height = max_width / scale_factor
            if result_height > max_height:
                result_height = max_height
                result_width = max_height * scale_factor

        result_width, result_height = int(result_width), int(result_height)
        image = image.resize((result_width * self.sample_x, result_height * self.sample_y), resize_mode)

        return image, (result_width, result_height)

    def _preprocess(self, image, target_size, clip_limit, enhance_contrast, rescale_intensity, background_glyph):
        """
        Preprocess input image to better be reproduced by glyphs.

        :param image: input :class:`~PIL.Image.Image` to be processed.
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
         Given as total number of glyphs to be used across and down.
        :type target_size: (:class:`int`, :class:`int`)
        :param clip_limit: clip limit as used by :func:`~skimage.exposure.equalize_adapthist`.
        :type clip_limit: :class:`float`
        :param enhance_contrast: enable or disable use of :func:`~skimage.exposure.equalize_adapthist` on input image.
        :type enhance_contrast: :class:`bool`
        :param rescale_intensity: control, or disable the effect of :func:`~skimage.exposure.rescale_intensity`.
         Values higher than 1 cause values near the extremes, to be pushed into those extremes.
         A value lover than 1 will tend to move all values toward the average glyph value.
         If `None` is passed, the rescaling is skipped. This is preferred over passing unity.
        :type rescale_intensity: :class:`float`, :class:`int` or `None`
        :return: image after preprocessing has been applied.
        :rtype: :class:`~PIL.Image.Image`
        """
        if background_glyph is not None:
            image_bands = image.getbands()
            if "A" in image_bands:
                alpha_channel = image.split()[image_bands.index("A")]
            else:
                alpha_channel = Image.new("L", image.size, "white")
        greyscale_image = image.convert("L")

        if enhance_contrast or rescale_intensity:
            image_array = np.asarray(greyscale_image)

            if min(target_size) > 1 and enhance_contrast:
                image_array = exposure.equalize_adapthist(image_array, clip_limit=clip_limit)

            if rescale_intensity is not None:

                mean_value = sum(self.value_extrema) / 2
                min_val, max_val = self.value_extrema
                value_range = max_val - min_val

                new_min = max([0, int(mean_value - (rescale_intensity / 2) * value_range)])
                new_max = min([255, int(mean_value + (rescale_intensity / 2) * value_range)])

                out_range = (new_min, new_max)

                image_array = exposure.rescale_intensity(image_array, out_range=out_range)

            greyscale_image = Image.fromarray(image_array.astype("uint8"))

        if background_glyph is not None:
            greyscale_image.putalpha(alpha_channel)
        return greyscale_image

    def _chunk(self, image_data, target_width):
        """
        Separate `image_data` into chunks, according to :attr:`~Glyph.sample_x` and :attr:`~Glyph.self.sample_y`.

        Working from left to right, top to bottom of data representing an input image,
        produces lists of data corresponding to a region of the full image
        that are :attr:`~Glyph.sample_x` by :attr:`~Glyph.sample_y` in size.

        :param image_data: list of image data specifying pixel values in range 0->255.
        :type image_data: [:class:`int`]
        :param target_width: width of target image as measured in glyphs.
        :type target_width: :class:`int`
        :return: list of chunks, each of which are a list of integer values from source `image_data`.
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

        :param image: image to manipulate.
        :type image: :class:`~PIL.Image.Image`
        :return: input image adjusted to glyph histogram.
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
        Determine closest glyph available to `target` data.

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
        :param target_width: number of :class:`Glyph` across the `result` represents.
        :type target_width: :class:`int`
        :param target_height: number of :class:`Glyph` down the `result` represents.
        :type target_height: :class:`int`
        :return: a :class:`~PIL.Image.Image` comprised of glyph :attr:`~Glyph.fingerprint_display` images.
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

        :param result: list of :class:`Glyph`.
        :type result: [:class:`Glyph`]
        :param target_width: number of :class:`Glyph` across the `result` represents.
        :type target_width: :class:`int`
        :param target_height: number of :class:`Glyph` down the `result` represents.
        :type target_height: :class:`int`
        :return: a :class:`~PIL.Image.Image` comprised of glyph images,
         representing final output of conversion from image to glyphs.
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
        equal to the depth of the most stacked glyph in the line.

        :param result_glyphs: list of glyphs that compost the output, listed top left, across then down.
        :type result_glyphs: [:class`Glyph`]
        :param spacer: spacing glyph, relating to a movement of 1 character over, with no glyph printed.
        :type spacer: :class:`Glyph`
        :param target_width: width of image, measured in glyphs.
        :type target_width: :class:`int`
        :param target_height: height of image, measured in glyphs.
        :type target_height: :class:`int`
        :param trailing_spacer: enable inclusion of trailing spacer characters.
         This can be helpful for counting back from end of line.
        :type trailing_spacer: :class:`bool`
        :return: List of instruction strings.
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

            \text{RMSD} &= \sqrt{\\frac{1}{N}\sum_{i=1}^N (x_i - a)^2} \\\\
                        &= \sqrt{(m - a)^2 + \\frac{1}{N}\sum_{i=1}^N (x_i - m)^2}

        * :math:`N` is number of points
        * :math:`m` is centroid of points
        * :math:`x_i` is a point of the set
        * :math:`a` is target point

        :param array_like point: point from which mean square distance is calculated.
        :param tree_set: :class:`~typo_graphics.typograph.TreeSet` to be compared against, contains centroid and mean square from centroid.
        :type tree_set: :class:`~typo_graphics.typograph.TreeSet`
        :return: root mean square distance of point from points given by `tree_set`.
        :rtype: :class:`float`
        """
        centroid = tree_set.centroid
        mean_square_from_centroid = tree_set.mean_square_from_centroid
        square_distance_from_centroid = ((np.array(point) - centroid) ** 2).sum()
        return np.sqrt(square_distance_from_centroid + mean_square_from_centroid)

    @staticmethod
    def _iter_all_strings():
        """
        Generator of Excel-like lowercase row letters.

        e.g. a, b, c, ... z, aa, ab
        useful for cases in which instructions require multiple lines per character row.

        :return: generator of excel-like string identifiers.
        :rtype: generator
        """
        size = 1
        while True:
            for s in itertools.product(string.ascii_lowercase, repeat=size):
                yield "".join(s)
            size += 1

    def image_to_text(self, image, max_size=(60, 60), cutoff=0, resize_mode=Image.LANCZOS, clip_limit=0.02,
                      enhance_contrast=True, rescale_intensity=1.5, instruction_spacer=None, background_glyph=None,
                      fit_mode="Scale"):
        """
        Convert image into a glyph version, using the instance's glyphs.

        :param image: input :class:`~PIL.Image.Image` to be processed and converted.
        :type image: :class:`~PIL.Image.Image`
        :param max_size: maximum size for glyph version of image.
         Given as total number of glyphs able to be used across and down.
         If `fit_mode` is "Scale",
         values of ``None`` in `max_size` are treated as infinite available space in that dimension.
         If (``None``, ``None``), will match input image size to nearest whole glyph in each dimension.
        :type max_size: (:class:`int` or ``None``, :class:`int` or ``None``)
        :param fit_mode: mode used to adjust image to fit within `max_size`. May be "Scale" to scale image to fit,
         or "Crop" to minimally crop image, maintaining center.
         "Crop" cannot be used with ``None`` values in `max_size`.
        :type fit_mode: :class:`string`
        :param resize_mode: any resize mode as able to be used by :meth:`~PIL.Image.Image.resize`.
        :param clip_limit: clip limit as used by :func:`~skimage.exposure.equalize_adapthist`.
        :type clip_limit: :class:`float`
        :param enhance_contrast: enable or disable use of :func:`~skimage.exposure.equalize_adapthist` on input image.
        :type enhance_contrast: :class:`bool`
        :param rescale_intensity: control, or disable the effect of :func:`~skimage.exposure.rescale_intensity`.
         Values higher than 1 cause values near the extremes, to be pushed into those extremes.
         A value lover than 1 will tend to move all values toward the average glyph value.
         If `None` is passed, the rescaling is skipped. This is preferred over passing unity.
         Defaults to expanding the output range 1.5 times.
        :type rescale_intensity: :class:`float`, :class:`int` or `None`
        :param cutoff: cutoff level for near-enough glyph replacement. A value of 0.0 will permit no replacements.
        :type cutoff: :class:`float`
        :param instruction_spacer: glyph to be used to represent moving the typing position one step, without adding ink.
        :type instruction_spacer: :class:`Glyph`
        :param background_glyph: glyph to fill background of transparent image with.
        :type background_glyph: :class:`Glyph`
        :return: a :class:`~typo_graphics.typograph.TypedArt` object, containing construction, output and instructions,
         after preprocessing.
        :rtype: :class:`~typo_graphics.typograph.TypedArt`
        """
        if fit_mode.lower() == "crop":
            if None in max_size:
                raise TypeError("Crop fit mode requires both maximum dimensions be specified,"
                                " received max_size={}".format(max_size))
            image, target_size = self._crop_to_max_size(image=image, max_size=max_size, resize_mode=resize_mode)
        else:
            image, target_size = self._scale_to_max_size(image=image, max_size=max_size, resize_mode=resize_mode)

        preprocessed_image = self._preprocess(image=image, target_size=target_size, clip_limit=clip_limit,
                                              enhance_contrast=enhance_contrast, rescale_intensity=rescale_intensity,
                                              background_glyph=background_glyph)

        calc, output, inst_str = self._convert(image=preprocessed_image, target_size=target_size, cutoff=cutoff,
                                               instruction_spacer=instruction_spacer, background_glyph=background_glyph)

        return TypedArt(calc, output, inst_str)

    def _convert(self, image, target_size, cutoff, instruction_spacer, background_glyph):
        """
        Raw conversion of image to glyphs, no preprocessing is performed.

        :param image: input :class:`~PIL.Image.Image` to be processed and converted.
        :type image: :class:`~PIL.Image.Image`
        :param target_size: output size for glyph version of image.
         Given as total number of glyphs to be used across and down.
        :type target_size: (:class:`int, :class:`int`)
        :param cutoff: cutoff level for near-enough glyph replacement. A value of 0.0 will permit no replacements.
        :type cutoff: :class:`float`
        :param instruction_spacer: glyph to be used to represent moving the typing position one step,
         without adding ink.
        :type instruction_spacer: :class:`Glyph`
        :return: a :class:`~typo_graphics.typograph.TypedArt` object, containing construction, output and instructions.
        :rtype: :class:`~typo_graphics.typograph.TypedArt`
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
