import unittest

from PIL import Image, ImageChops
from typo_graphics import Glyph


class TestGlyph(unittest.TestCase):

    def setUp(self):
        """
        Basic set up, we make a few glyphs, keeping hold of the images and names we use


        """
        self.a_image = Image.open('../Glyphs/a.png')
        self.a_name = 'a'
        self.a_glyph = Glyph(name=self.a_name, image=self.a_image)

        self.z_image = Image.open('../Glyphs/z.png')
        self.z_name = 'z'
        self.z_glyph = Glyph(name=self.z_name, image=self.z_image)

        self.k_image = Image.open('../Glyphs/k.png')
        self.k_name = 'k'
        self.k_glyph = Glyph(name=self.k_name, image=self.k_image, samples=(5, 8))

        self.f_image = Image.open('../Glyphs/f.png')
        self.f_name = 'f'
        self.f_glyph = Glyph(name=self.f_name, image=self.f_image, samples=(5, 8))

    def test_name(self):
        """
        Name is reproduced as glyph.name
        """
        name_attribute = self.a_glyph.name
        self.assertEqual(name_attribute, self.a_name)

    def test_str(self):
        """
        Name is used as __str__
        """
        string_representation = str(self.a_glyph)
        self.assertEqual(string_representation, self.a_name)

    def test_image(self):
        """
        Image is reproduced as glyph.image
        """
        image_attribute = self.a_glyph.image
        self.assertIsInstance(image_attribute, Image.Image)
        self.assertEqual(image_attribute, self.a_image)

    def test_components_of_typeable_glyph(self):
        """
        Components should be a list that contains just a reference to self
        """
        components = self.a_glyph.components
        self.assertIsInstance(components, list)
        self.assertEqual(len(components), 1)

        first_component = components[0]
        self.assertIsInstance(first_component, Glyph)
        self.assertIs(first_component, self.a_glyph)

    def test_samples(self):
        """
        Samples is reproduces as glyph.samples
        Default value is (3, 3)
        """
        a_samples = self.a_glyph.samples
        self.assertIsInstance(a_samples, tuple)
        self.assertTupleEqual(a_samples, (3, 3))

        k_samples = self.k_glyph.samples
        self.assertTupleEqual(k_samples, (5, 8))

    def test_integer_samples(self):
        """
        Glyph can accept an integer it will use to create samples tuple from
        """
        int_value = 5
        glyph = Glyph(name=self.a_name, image=self.a_image, samples=int_value)
        samples = glyph.samples
        self.assertIsInstance(samples, tuple)
        self.assertEqual(samples, (int_value, int_value))

    def test_fingerprint(self):
        """
        Fingerprint is a scaled down version of image, to samples size
        Fingerprint is an "L" mode image
        """
        fingerprint = self.a_glyph.fingerprint
        self.assertIsInstance(fingerprint, Image.Image)
        self.assertTupleEqual(fingerprint.size, (3, 3))
        self.assertEqual(fingerprint.mode, "L")

    def test_fingerprint_display(self):
        """
        Fingerprint display should be size of original input image
        Scaled up version of the fingerprint image
        """
        fingerprint_display = self.a_glyph.fingerprint_display
        self.assertIsInstance(fingerprint_display, Image.Image)
        self.assertEqual(fingerprint_display.size, self.a_image.size)

        fingerprint = self.a_glyph.fingerprint
        resized_fingerprint = fingerprint.resize(self.a_image.size)
        self.assertEqual(fingerprint_display, resized_fingerprint)

    def test_add(self):
        """
        When adding two glyphs,

        returns a glyph
        name is combined
        image is combined
        components combined and sorted
        samples maintained

        cannot add glyph to anything else
        cannot add glyphs with unequal samples
        """

        combined_glyph = self.a_glyph + self.z_glyph
        self.assertIsInstance(combined_glyph, Glyph)

        combined_name = combined_glyph.name
        self.assertEqual(combined_name, self.a_name + ' ' + self.z_name)

        combined_image = combined_glyph.image
        self.assertIsInstance(combined_image, Image.Image)
        self.assertEqual(combined_image, ImageChops.darker(self.a_image, self.z_image))

        combined_components = combined_glyph.components
        self.assertEqual(len(combined_components), 2)
        self.assertEqual(combined_components[0], self.a_glyph)
        self.assertEqual(combined_components[1], self.z_glyph)

        self.assertEqual(combined_glyph.samples, self.a_glyph.samples)

        high_sample_glyph = self.k_glyph + self.f_glyph
        self.assertTupleEqual(high_sample_glyph.samples, self.k_glyph.samples)

        with self.assertRaises(TypeError):
            self.a_glyph + 42
        with self.assertRaises(TypeError):
            self.a_glyph + 'foo'
        with self.assertRaises(TypeError):
            self.a_glyph + self.z_image

        with self.assertRaises(ValueError):
            self.a_glyph + self.k_glyph

    def test_add_mode_error(self):
        """
        Adding two glyphs of different modes should raise a ValueError.
        Previously a cryptic ValueError was raised by ImageChops instead.
        """

        a_image = self.a_image.convert("L")
        a_glyph = Glyph(name=self.a_name, image=a_image)
        z_image = self.z_image.convert("RGBA")
        z_glyph = Glyph(name=self.z_name, image=z_image)

        self.assertNotEqual(a_glyph.image.mode, z_glyph.image.mode)

        with self.assertRaises(ValueError):
            a_glyph + z_glyph

    def test_glyph_commutativity(self):
        """
        Glyphs are easily made commutative. The order has no meaning, so should not matter.
        """

        a_z = self.a_glyph + self.z_glyph
        z_a = self.z_glyph + self.a_glyph

        self.assertEqual(a_z, z_a)

    def test_equivalence_identical_glyphs(self):
        """
        Glyphs that are identical in every way, should be seen as equal to one another.
        """
        a_copy = Glyph(name=self.a_name, image=self.a_image)

        self.assertEqual(self.a_glyph, a_copy)

    def test_equivalence_different_glyphs(self):
        """
        Glyphs that differ, even slightly, should be deemed different.
        """
        a_variant = Glyph(name=self.a_name + ' ', image=self.a_image)

        self.assertNotEqual(self.a_glyph, a_variant)

if __name__ == '__main__':
    unittest.main()
