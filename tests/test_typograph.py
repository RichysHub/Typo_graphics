import json
import os
import tempfile
import unittest
from collections import namedtuple
from string import ascii_uppercase, punctuation

from PIL import Image
from numpy import ndarray
from scipy.spatial import cKDTree
from scipy.special import comb
from typo_graphics import Typograph, Glyph
from typo_graphics.typograph import TreeSet

GlyphSheet = namedtuple("GlyphSheet", ["glyph_sheet", "glyph_dimensions", "spacing", "glyph_images",
                                       "glyph_names", "grid_size", "number_glyphs"])

GlyphDirectory = namedtuple("GlyphDirectory", ["directory", "glyph_file_names", "glyph_end_names", "number_glyphs",
                                               "glyph_images"])


class TestTypograph(unittest.TestCase):

    def setUp(self):
        self.typograph = Typograph()
        self.teardown_files = []
        self.teardown_dirs = []

    def test_samples(self):
        """
        Samples is a tuple that defaults to (3, 3)
        """
        samples = self.typograph.samples
        default_samples = (3, 3)
        self.assertIsInstance(samples, tuple)
        self.assertEqual(samples, default_samples)

    def test_integer_samples(self):
        """
        Typograph can accept an integer it will use to create samples tuple from
        """
        int_value = 5
        typograph = Typograph(samples=int_value)
        samples = typograph.samples
        self.assertIsInstance(samples, tuple)
        self.assertEqual(samples, (int_value, int_value))

    def test_glyphs(self):
        """
        Typograph.glyphs should be a dictionary of glyphs

        each glyph should be keyed by name
        glyphs should have correct number of samples

        """
        glyphs = self.typograph.glyphs
        self.assertIsInstance(glyphs, dict)

        typograph_samples = self.typograph.samples
        for name, glyph in glyphs.items():
            self.assertIsInstance(glyph, Glyph)
            self.assertEqual(name, glyph.name)
            self.assertEqual(glyph.samples, typograph_samples)

    def test_glyph_dimensions(self):
        """
        Dimensions of glyphs should be extracted, in px
        """

        example_glyph = next(iter(self.typograph.glyphs.values()))
        glyph_size = example_glyph.image.size

        glyph_width = self.typograph.glyph_width
        self.assertIsInstance(glyph_width, int)
        self.assertEqual(glyph_width, glyph_size[0])

        glyph_height = self.typograph.glyph_height
        self.assertIsInstance(glyph_height, int)
        self.assertEqual(glyph_height, glyph_size[1])

    def test_combine_glyphs(self):
        """
        Glyphs are combined to a certain depth, and a dict returned
        """
        number_of_glyphs = 82

        for depth in range(1, 4):
            with self.subTest(depth=depth):
                number_of_glyphs_combinations = comb(number_of_glyphs, depth)

                glyph_dict = self.typograph._combine_glyphs(depth=depth)
                self.assertIsInstance(glyph_dict, dict)

                items = glyph_dict.items()
                self.assertEqual(len(items), number_of_glyphs_combinations)

                for name, glyph in items:
                    self.assertEqual(glyph.name, name)
                    self.assertIsInstance(glyph, Glyph)

    def test_tree_sets(self):
        """
        Tree sets are created
        number equal to glyph depth

        list of tree sets

        each tree set contains:
        * glyphs
        * a cKDTree
        * centroid
        * mean_square form centroid
        * stack size
        """
        default_samples = (3, 3)
        sample_product = default_samples[0] * default_samples[1]

        number_of_glyphs = 82

        tree_sets = self.typograph.tree_sets
        self.assertIsInstance(tree_sets, list)

        for tree_index, tree_set_ in enumerate(tree_sets):
            self.assertIsInstance(tree_set_, TreeSet)
            tree_set_stack_size = tree_set_.stack_size
            self.assertIsInstance(tree_set_stack_size, int)
            stack_size = tree_index + 1
            self.assertEqual(tree_set_stack_size, stack_size)

            number_of_glyphs_combinations = comb(number_of_glyphs, stack_size)

            glyph_set = tree_set_.glyph_set
            self.assertEqual(len(glyph_set), number_of_glyphs_combinations)
            self.assertIsInstance(glyph_set[0], Glyph)

            tree = tree_set_.tree
            self.assertIsInstance(tree, cKDTree)
            self.assertEqual(tree.m, sample_product)
            self.assertEqual(tree.n, number_of_glyphs_combinations)

            centroid = tree_set_.centroid
            self.assertIsInstance(centroid, ndarray)
            self.assertEqual(len(centroid), sample_product)

            mean_square_from_centroid = tree_set_.mean_square_from_centroid
            self.assertIsInstance(mean_square_from_centroid, float)

    def test_average_values(self):
        """
        Average values is a list of floats, one for each combination of glyphs
        """
        average_values = self.typograph.average_values
        self.assertIsInstance(average_values, list)
        self.assertIsInstance(average_values[0], float)

    def test_value_extrema(self):
        """
        Value extrema is a tuple of floats
        """
        value_extrema = self.typograph.value_extrema
        self.assertIsInstance(value_extrema, tuple)
        self.assertEqual(len(value_extrema), 2)
        minimum_value, maximum_value = value_extrema

        self.assertIsInstance(minimum_value, float)
        self.assertIsInstance(maximum_value, float)

        self.assertLessEqual(minimum_value, maximum_value)

    @staticmethod
    def glyph_images(number_of_images, glyph_dimensions):

        glyph_images = []

        for i in range(number_of_images):
            glyph_image = Image.new("L", glyph_dimensions, "white")
            glyph_image.putpixel((i % number_of_images, i // number_of_images), 0)
            glyph_images.append(glyph_image)

        return glyph_images

    def glyph_sheet(self):
        """
        Create a GlyphSheet object, containing the glyph sheet image, and all the required metadata to test
        """

        glyph_dimensions = (25, 50)
        spacing = (25, 50)
        number_glyphs = 5
        glyph_width, glyph_height = glyph_dimensions
        spacing_width, spacing_height = spacing
        grid_size = (number_glyphs, 1)

        total_width = (glyph_width * number_glyphs) + (spacing_width * (number_glyphs - 1))
        glyph_sheet = Image.new("L", (total_width, glyph_height))

        glyph_names = []
        glyph_images = self.glyph_images(number_glyphs, glyph_dimensions)

        for i, glyph_image in enumerate(glyph_images):
            glyph_names.append(ascii_uppercase[i])

            glyph_sheet.paste(glyph_image, (i * (glyph_width + spacing[0]), 0,
                                            ((i + 1) * glyph_width) + (i * spacing[0]), glyph_height))

        sheet = GlyphSheet(glyph_names=glyph_names, spacing=spacing, glyph_sheet=glyph_sheet,
                           glyph_dimensions=glyph_dimensions, grid_size=grid_size,
                           number_glyphs=number_glyphs, glyph_images=glyph_images)

        return sheet

    def test_from_glyph_sheet_grid_size(self):
        """
        Using the grid size, are glyphs correctly extracted from the Glyph sheet?
        """

        sheet = self.glyph_sheet()

        typograph = Typograph.from_glyph_sheet(glyph_sheet=sheet.glyph_sheet, glyph_names=sheet.glyph_names,
                                               number_glyphs=sheet.number_glyphs, spacing=sheet.spacing,
                                               grid_size=sheet.grid_size)

        self.assertEqual(len(typograph.glyphs), sheet.number_glyphs)

        for name, image in zip(sheet.glyph_names, sheet.glyph_images):
            self.assertIn(name, typograph.glyphs)
            glyph = typograph.glyphs[name]

            self.assertIsInstance(glyph, Glyph)
            self.assertEqual(glyph.image, image)

    def test_from_glyph_sheet_grid_dimensions(self):
        """
        Using the grid dimensions, are glyphs correctly extracted from the Glyph sheet?
        """

        sheet = self.glyph_sheet()

        typograph = Typograph.from_glyph_sheet(glyph_sheet=sheet.glyph_sheet, glyph_names=sheet.glyph_names,
                                               number_glyphs=sheet.number_glyphs, spacing=sheet.spacing,
                                               glyph_dimensions=sheet.glyph_dimensions)

        self.assertEqual(len(typograph.glyphs), sheet.number_glyphs)

        for name, image in zip(sheet.glyph_names, sheet.glyph_images):
            self.assertIn(name, typograph.glyphs)
            glyph = typograph.glyphs[name]

            self.assertIsInstance(glyph, Glyph)
            self.assertEqual(glyph.image, image)

    def test_from_glyph_sheet_missing_names(self):
        """
        If no names are provided, glyphs should be given sequential placeholder names
        """

        sheet = self.glyph_sheet()

        typograph = Typograph.from_glyph_sheet(glyph_sheet=sheet.glyph_sheet, number_glyphs=sheet.number_glyphs,
                                               spacing=sheet.spacing, grid_size=sheet.grid_size)

        self.assertEqual(len(typograph.glyphs), sheet.number_glyphs)

        for i in range(sheet.number_glyphs):
            glyph_name = "g{}".format(i)
            self.assertIn(glyph_name, typograph.glyphs)
            glyph = typograph.glyphs[glyph_name]
            self.assertIsInstance(glyph, Glyph)

    def test_from_glyph_sheet_duplicate_names(self):
        """
        Because glyph names are used for a dictionary, they must be unique.
        If duplicates are found in the list, a ValueError should be raised.
        """

        sheet = self.glyph_sheet()

        names = sheet.glyph_names[:-1]
        names += names[0]

        with self.assertRaises(ValueError):
            Typograph.from_glyph_sheet(glyph_sheet=sheet.glyph_sheet, number_glyphs=sheet.number_glyphs,
                                       glyph_dimensions=sheet.glyph_dimensions, glyph_names=names)

    def test_from_glyph_sheet_missing_number_given_names(self):
        """
        If the number of glyphs is not given, but the names are, we can use the length of names

        No error should be raised, and the correct number of glyphs should be extracted
        """

        sheet = self.glyph_sheet()

        typograph = Typograph.from_glyph_sheet(sheet.glyph_sheet,
                                               glyph_dimensions=sheet.glyph_dimensions, glyph_names=sheet.glyph_names)

        self.assertEqual(len(typograph.glyphs), len(sheet.glyph_names))

    def test_from_glyph_sheet_missing_number_missing_names(self):
        """
        If the number of glyphs is not given, nor are the names, a TypeError should be raised
        """

        sheet = self.glyph_sheet()
        with self.assertRaises(TypeError):
            Typograph.from_glyph_sheet(sheet.glyph_sheet, glyph_dimensions=sheet.glyph_dimensions)

    def test_from_glyph_sheet_missing_glyph_dimensions_missing_grid_size(self):
        """
        Either glyph dimensions or grid size need to be specified, else a TypeError should be raised
        """

        sheet = self.glyph_sheet()
        with self.assertRaises(TypeError):
            Typograph.from_glyph_sheet(sheet.glyph_sheet, glyph_names=sheet.glyph_names)

    def tearDown(self):
        for path in self.teardown_files:
            os.unlink(path)
        for dir_ in self.teardown_dirs:
            os.rmdir(dir_)

    def glyph_directory(self):
        directory = tempfile.mkdtemp(prefix="Typo_")
        self.teardown_dirs.append(directory)

        glyph_dimensions = (25, 50)
        number_glyphs = 5
        glyph_images = self.glyph_images(number_glyphs, glyph_dimensions)
        glyph_file_names = []
        glyph_end_names = []

        for file_name, end_name, image in zip(ascii_uppercase, punctuation, glyph_images):
            glyph_file_names.append(file_name)
            glyph_end_names.append(end_name)
            path = os.path.join(directory, file_name + '.png')
            self.teardown_files.append(path)
            image.save(path)

        glyph_directory = GlyphDirectory(directory=directory, glyph_file_names=glyph_file_names,
                                         glyph_end_names=glyph_end_names, number_glyphs=number_glyphs,
                                         glyph_images=glyph_images)

        return glyph_directory

    def test_from_directory(self):
        """
        Glyph should be loaded from the directory, into typograph.glyphs
        Names from the name map should be used for all
        """

        glyph_directory = self.glyph_directory()

        directory = glyph_directory.directory
        number_glyphs = glyph_directory.number_glyphs
        glyph_file_names = glyph_directory.glyph_file_names
        glyph_end_names = glyph_directory.glyph_end_names
        glyph_images = glyph_directory.glyph_images

        name_map = {file_name: end_name for file_name, end_name in zip(glyph_file_names, glyph_end_names)}

        name_map_path = os.path.join(directory, 'name_map.json')
        with open(name_map_path, 'w') as name_map_file:
            json.dump(name_map, name_map_file)
            self.teardown_files.append(name_map_path)

        typograph = Typograph.from_directory(glyph_directory=directory)

        self.assertEqual(len(typograph.glyphs), number_glyphs)

        for file_name, end_name, image in zip(glyph_file_names, glyph_end_names, glyph_images):
            self.assertIn(end_name, typograph.glyphs)
            self.assertNotIn(file_name, typograph.glyphs)
            glyph = typograph.glyphs[end_name]

            # Have to do some pasting trickery to avoid having a PngImageFile object
            pasted_image = Image.new("L", image.size)
            pasted_image.paste(glyph.image, (0, 0, *image.size))

            self.assertEqual(pasted_image, image)

    def test_from_directory_partial_name_map(self):
        """
        If a name map only contains some of the file names,
        others should continue to use that file name
        """
        glyph_directory = self.glyph_directory()

        directory = glyph_directory.directory
        number_glyphs = glyph_directory.number_glyphs
        glyph_file_names = glyph_directory.glyph_file_names
        glyph_end_names = glyph_directory.glyph_end_names
        glyph_images = glyph_directory.glyph_images

        cutoff = number_glyphs//2

        name_map = {file_name: end_name for file_name, end_name in zip(glyph_file_names[:cutoff], glyph_end_names)}

        name_map_path = os.path.join(directory, 'name_map.json')
        with open(name_map_path, 'w') as name_map_file:
            json.dump(name_map, name_map_file)
            self.teardown_files.append(name_map_path)

        glyph_end_names[cutoff:] = glyph_file_names[cutoff:]

        typograph = Typograph.from_directory(glyph_directory=directory)
        self.assertEqual(len(typograph.glyphs), number_glyphs)

        for file_name, end_name, image in zip(glyph_file_names, glyph_end_names, glyph_images):
            self.assertIn(end_name, typograph.glyphs)
            glyph = typograph.glyphs[end_name]

            # Have to do some pasting trickery to avoid having a PngImageFile object
            pasted_image = Image.new("L", image.size)
            pasted_image.paste(glyph.image, (0, 0, *image.size))

            self.assertEqual(pasted_image, image)

    def test_from_directory_empty_name_map(self):
        """
        If a name_map.json exists, but contains no entries, it should not affect behaviour
        """
        glyph_directory = self.glyph_directory()

        directory = glyph_directory.directory
        number_glyphs = glyph_directory.number_glyphs
        glyph_file_names = glyph_directory.glyph_file_names
        glyph_images = glyph_directory.glyph_images

        name_map = {}

        name_map_path = os.path.join(directory, 'name_map.json')
        with open(name_map_path, 'w') as name_map_file:
            json.dump(name_map, name_map_file)
            self.teardown_files.append(name_map_path)

        typograph = Typograph.from_directory(glyph_directory=directory)
        self.assertEqual(len(typograph.glyphs), number_glyphs)

        for file_name, image in zip(glyph_file_names, glyph_images):
            self.assertIn(file_name, typograph.glyphs)
            glyph = typograph.glyphs[file_name]

            # Have to do some pasting trickery to avoid having a PngImageFile object
            pasted_image = Image.new("L", image.size)
            pasted_image.paste(glyph.image, (0, 0, *image.size))

            self.assertEqual(pasted_image, image)

    def test_from_directory_missing_name_map(self):
        """
        If no name_map.json exists, the FileNotFound error that would otherwise occur should be handled.
        Glyphs should all be loaded, named according to file names
        """
        glyph_directory = self.glyph_directory()

        directory = glyph_directory.directory
        number_glyphs = glyph_directory.number_glyphs
        glyph_file_names = glyph_directory.glyph_file_names
        glyph_images = glyph_directory.glyph_images

        typograph = Typograph.from_directory(glyph_directory=directory)
        self.assertEqual(len(typograph.glyphs), number_glyphs)

        for file_name, image in zip(glyph_file_names, glyph_images):
            self.assertIn(file_name, typograph.glyphs)
            glyph = typograph.glyphs[file_name]

            # Have to do some pasting trickery to avoid having a PngImageFile object
            pasted_image = Image.new("L", image.size)
            pasted_image.paste(glyph.image, (0, 0, *image.size))

            self.assertEqual(pasted_image, image)

    def test_standalone_glyphs(self):
        """
        Standalone glyphs is a dict of glyphs, default empty
        """
        standalone_glyphs = self.typograph.standalone_glyphs
        self.assertIsInstance(standalone_glyphs, dict)
        self.assertEqual(len(standalone_glyphs), 0)

    def space_glyph(self):
        """
        Create a blank glyph, called 'space'
        """
        glyph_dimensions = next(iter(self.typograph.glyphs.values())).image.size
        blank_image = Image.new("RGBA", glyph_dimensions, "white")
        space = Glyph(name='sp', image=blank_image)
        return space

    def test_add_standalone_glyph(self):
        """
        Adding the glyph to standalone glyphs
        """
        space = self.space_glyph()
        self.typograph.add_glyph(glyph=space, use_in_combinations=False)

        standalone_glyphs = self.typograph.standalone_glyphs
        self.assertEqual(len(standalone_glyphs), 1)
        space_name = space.name
        self.assertIn(space_name, standalone_glyphs)
        standalone_glyph = standalone_glyphs[space_name]
        self.assertIsInstance(standalone_glyph, Glyph)
        self.assertIs(standalone_glyph, space)

        glyphs = self.typograph.glyphs
        self.assertNotIn(space_name, glyphs)

    def test_add_combination_glyphs(self):
        """
        Adding the glyph to glyphs
        """
        space = self.space_glyph()
        self.typograph.add_glyph(glyph=space, use_in_combinations=True)
        space_name = space.name

        standalone_glyphs = self.typograph.standalone_glyphs
        self.assertNotIn(space_name, standalone_glyphs)

        glyphs = self.typograph.glyphs
        self.assertIn(space_name, glyphs)
        entry_in_glyphs = glyphs[space_name]
        self.assertIsInstance(entry_in_glyphs, Glyph)
        self.assertIs(entry_in_glyphs, space)

    def test_add_retains_exclusivity(self):
        """
        Adding glyph to standalone removes from glyphs, and vice versa
        """
        space = self.space_glyph()
        space_name = space.name
        glyphs = self.typograph.glyphs
        standalone_glyphs = self.typograph.standalone_glyphs

        self.typograph.add_glyph(glyph=space, use_in_combinations=False)
        self.assertIn(space_name, standalone_glyphs)
        self.assertNotIn(space_name, glyphs)

        self.typograph.add_glyph(glyph=space, use_in_combinations=True)
        self.assertIn(space_name, glyphs)
        self.assertNotIn(space_name, standalone_glyphs)

        self.typograph.add_glyph(glyph=space, use_in_combinations=False)
        self.assertIn(space_name, standalone_glyphs)
        self.assertNotIn(space_name, glyphs)

    def test_remove_standalone_glyph(self):
        """
        Glyphs can be removed from standalone using "Standalone"
        "Combinations" has no effect
        """
        typograph = self.typograph
        space = self.space_glyph()
        space_name = space.name
        typograph.add_glyph(glyph=space, use_in_combinations=False)
        removed = typograph.remove_glyph(glyph=space_name, remove_from="Combinations")

        self.assertIsNone(removed)

        removed = typograph.remove_glyph(glyph=space_name, remove_from="Standalone")
        self.assertIsInstance(removed, Glyph)
        self.assertIs(removed, space)

    def test_remove_combination_glyph(self):
        """
        Glyphs can be removed from combinations using "Combinations"
        "Standalone" has no effect
        """
        typograph = self.typograph
        space = self.space_glyph()
        space_name = space.name
        typograph.add_glyph(glyph=space, use_in_combinations=True)
        removed = typograph.remove_glyph(glyph=space_name, remove_from="Standalone")

        self.assertIsNone(removed)

        removed = typograph.remove_glyph(glyph=space_name, remove_from="Combinations")
        self.assertIsInstance(removed, Glyph)
        self.assertIs(removed, space)

    def test_remove_from_both(self):
        """
        Glyphs can be removed from either using "Both"
        """
        typograph = self.typograph
        space = self.space_glyph()
        space_name = space.name

        typograph.add_glyph(glyph=space, use_in_combinations=False)
        removed = typograph.remove_glyph(glyph=space_name, remove_from="Both")
        self.assertIsInstance(removed, Glyph)
        self.assertIs(removed, space)

        typograph.add_glyph(glyph=space, use_in_combinations=True)
        removed = typograph.remove_glyph(glyph=space_name, remove_from="Both")
        self.assertIsInstance(removed, Glyph)
        self.assertIs(removed, space)

    def test_remove_glyph_with_glyph(self):
        """
        Glyphs can be removed by passing the glyph itself
        """
        typograph = self.typograph
        space = self.space_glyph()

        typograph.add_glyph(glyph=space, use_in_combinations=False)
        removed = typograph.remove_glyph(glyph=space, remove_from="Both")
        self.assertIsInstance(removed, Glyph)
        self.assertIs(removed, space)

    def test_remove_nonexistant_glyph(self):
        """
        Attempting to remove a glyph that isn't in either dictionary should return None
        """
        typograph = self.typograph
        space = self.space_glyph()
        space_name = space.name

        standalone_glyphs = typograph.standalone_glyphs
        glyphs = typograph.glyphs
        self.assertNotIn(space_name, standalone_glyphs)
        self.assertNotIn(space_name, glyphs)

        removed = typograph.remove_glyph(space_name, remove_from="Both")
        self.assertIsNone(removed)

    def test_preprocess_all_disabled(self):
        """
        If we disable everything, the image just gets converted to greyscale
        size should be preserved
        Image should not have gained an alpha channel
        """
        typograph = self.typograph

        input_image = Image.new("RGB", (300, 400), "red")
        preprocessed_image = typograph._preprocess(image=input_image, target_size=(30, 40),
                                                   enhance_contrast=False, rescale_intensity=False,
                                                   background_glyph=None, clip_limit=0)

        self.assertIsInstance(preprocessed_image, Image.Image)
        self.assertTupleEqual(preprocessed_image.size, input_image.size)

        greyscale_image = input_image.convert("L")
        self.assertEqual(preprocessed_image, greyscale_image)
        self.assertNotIn("A", preprocessed_image.getbands())

    def test_preprocess_background_glyph(self):
        """
        If a background glyph is given, the image should have an alpha channel added, if it lacks one
        """
        typograph = self.typograph
        space = self.space_glyph()
        input_image = Image.new("RGB", (300, 400), "red")
        preprocessed_image = typograph._preprocess(image=input_image, target_size=(30, 40),
                                                   enhance_contrast=False, rescale_intensity=False,
                                                   background_glyph=space, clip_limit=0)
        self.assertIn("A", preprocessed_image.getbands())

    def test_chunk(self):
        """"
        Chunk should take a list of image data, and return it in chunks
        should return a list of lists of ints
        chunks should correspond to input image data
        """
        image_data = [0, 0, 255, 255,
                      0, 0, 255, 255,
                      128, 128, 0, 255,
                      128, 128, 128, 0]

        typograph = Typograph(samples=2)
        chunks = typograph._chunk(image_data=image_data, target_width=2)

        self.assertIsInstance(chunks, list)
        self.assertIsInstance(chunks[0], list)
        self.assertIsInstance(chunks[0][0], int)

        self.assertEqual(len(chunks), 4)
        self.assertEqual(len(chunks[0]), 4)

        self.assertListEqual(chunks[0], [0, 0, 0, 0])
        self.assertListEqual(chunks[1], [255, 255, 255, 255])
        self.assertListEqual(chunks[2], [128, 128, 128, 128])
        self.assertListEqual(chunks[3], [0, 255, 128, 0])

    def test_find_closest_glyph_perfect_match(self):
        """
        Provided samples is high enough, Typograph should identify the perfect match, and its distance should be zero
        """

        typograph = self.typograph

        target_glyph = next(iter(typograph.glyphs.values()))
        target = target_glyph.fingerprint.getdata()
        closest, distance = typograph._find_closest_glyph(target=target, cutoff=0, background_glyph=None)

        self.assertIsInstance(closest, Glyph)
        self.assertIs(closest, target_glyph)
        self.assertEqual(distance, 0)

    def test_find_closest_glyph_perfect_match_combination(self):
        """
        Perfect matching should work equally with a combination glyph
        """

        typograph = self.typograph

        glyph_iter = iter(typograph.glyphs.values())
        target_glyph = next(glyph_iter) + next(glyph_iter)
        target = target_glyph.fingerprint.getdata()
        closest, distance = typograph._find_closest_glyph(target=target, cutoff=0, background_glyph=None)

        self.assertIsInstance(closest, Glyph)
        self.assertEqual(closest, target_glyph)
        self.assertEqual(distance, 0)

    def test_find_closest_glyph_cutoff_1_combination_to_single(self):
        """
        With a cutoff value of 1, the matching should match a single glyph,
        despite there being a perfect combination glyph match
        """
        typograph = self.typograph

        glyph_iter = iter(typograph.glyphs.values())
        target_glyph = next(glyph_iter) + next(glyph_iter)
        target = target_glyph.fingerprint.getdata()
        closest, distance = typograph._find_closest_glyph(target=target, cutoff=1, background_glyph=None)

        self.assertIsInstance(closest, Glyph)
        self.assertEqual(len(closest.components), 1)

    def test_find_closest_glyph_fully_transparent(self):
        """
        Using a perfect match, Typograph would otherwise match to that glyph.
        Adding an alpha channel, so image is fully transparent, as such, background glyph should be matched.
        """

        typograph = self.typograph

        glyphs = iter(typograph.glyphs.values())
        target_glyph = next(glyphs)
        background_glyph = next(glyphs)
        background_glyph = typograph.remove_glyph(background_glyph)

        target_image = target_glyph.fingerprint
        alpha_channel = Image.new("L", target_image.size)
        target_image.putalpha(alpha_channel)

        target = target_image.getdata()

        closest, distance = typograph._find_closest_glyph(target=target, cutoff=0, background_glyph=background_glyph)

        self.assertIsInstance(closest, Glyph)
        self.assertIs(closest, background_glyph)
        self.assertIsNone(distance)

    def test_background_glyph_excluded_from_main_image(self):

        typograph = self.typograph

        glyphs = iter(typograph.glyphs.values())
        background_glyph = next(glyphs)
        background_glyph = typograph.remove_glyph(background_glyph)

        target_image = background_glyph.fingerprint
        alpha_channel = Image.new("L", target_image.size, "white")
        target_image.putalpha(alpha_channel)
        target = target_image.getdata()

        closest, distance = typograph._find_closest_glyph(target=target, cutoff=0, background_glyph=background_glyph)

        self.assertIsInstance(closest, Glyph)
        self.assertIsNot(closest, background_glyph)


if __name__ == '__main__':
    unittest.main()
