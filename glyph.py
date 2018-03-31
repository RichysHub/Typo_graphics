from PIL import Image, ImageChops


class Glyph:
    """
    Represents the ink typed into one monospaced space.

    This can comprise of multiple component glyphs, which are retained in :attr:`components`.
    In the case that the glyph is as typed, this will contain simply a reference to self.

    Exposes following instance attributes:
     - :attr:`name`, the name of the glyph.
     - :attr:`image`, :class:`~PIL.Image.Image` image of the glyph.
     - :attr:`components`, the typed keys that compose this glyph.
     - :attr:`samples`, tuple of ints governing how the glyph is down-sampled for matching.
     - :attr:`fingerprint`, scaled :class:`~PIL.Image.Image` showing how glyph is internally processed.
     - :attr:`fingerprint_display`, rescaled version of :attr:`fingerprint`, to size of original :attr:`image`.

    Explicitly supports summation with other glyph objects, which represent typing the two glyph atop one another.
    """
    def __init__(self, name, image, components=None, samples=(3, 3)):
        """
        Create glyph object.

        :param name: name of glyph, used both internally and when creating instructions with glyphs.
        :type name: :class:`str`
        :param image: an :class:`~PIL.Image.Image` of the glyph. Likely sourced from scanned typewritten page.
        :type image: :class:`~PIL.Image.Image`
        :param components: glyphs that are used to create this glyph.
         If not specified, will default to containing this glyph.
        :type components: [:class:`Glyph`]
        :param samples: size specified in an integer, integer tuple for the fingerprint to be scaled to.
         Specified as number of pixels across, by number of pixels. Can also pass integer to be used in both dimensions.
        :type samples: (:class:`int`, :class:`int`) or :class:`int`
        """
        self.name = name
        self.image = image

        if isinstance(samples, int):
            samples = (samples, samples)

        self.samples = samples
        self.fingerprint = self.image.convert("L").resize(samples, Image.BOX)
        self.fingerprint_display = self.fingerprint.resize(self.image.size)

        if components:
            self.components = components
        else:
            self.components = [self]

    def __add__(self, other):
        """
        Addition override.

        Addition of glyphs encapsulates overlaying the two glyphs on a typewriter.
        This would be achieved by first typing `glyph1`, moving the carriage back, and typing `glyph2` in the same space.
        Image combination is achieved with :func:`~PIL.ImageChops.darker`

        If the :attr:`~Glyph.samples` of the two glyphs are not equal, a :exc:`ValueError` is raised.

        The returned :class:`Glyph`
        Addition of two glyphs returns a new glyph object, combining images with :func:`~PIL.ImageChops.darker`,
        and combining names with a space.

        :param other: glyph to add.
        :type other: :class:`Glyph`
        :return: composite glyph of this, and the `other` glyph.
        :rtype: :class:`Glyph`
        :raises ValueError: if :attr:`~Glyph.samples` attribute of the two glyphs do not match.
        :raises TypeError: if addition is attempted with an object **not** of type :class:`Glyph`.
        :raises ValueError: if :attr:`Glyph.image.mode` attribute of the two glyphs do not match.
        """
        if not isinstance(other, Glyph):
            raise TypeError('can only combine glyph (not "{}") with glyph'.format(type(other)))

        if self.samples != other.samples:
            raise ValueError('Cannot combine glyphs with unequal samples {} =/= {}'.format(self.samples, other.samples))

        if self.image.mode != other.image.mode:
            raise ValueError('Cannot combine glyphs with unequal image modes, {} =/= {}'
                             .format(self.image.mode, other.image.mode))

        composite = ImageChops.darker(self.image, other.image)
        components = sorted(self.components + other.components, key=lambda g: g.name)
        name = ' '.join([g.name for g in components])
        return Glyph(name=name, image=composite, components=components, samples=self.samples)

    def __str__(self):
        """
        String override.

        Returns the name attribute for the glyph.
        :return: name of the glyph.
        :rtype: :class:`string`
        """
        return self.name

    def __eq__(self, other):
        """
        Equivalence override

        :param other: glyph to compare against.
        :type other: :class:`Glyph`
        :return: True if the name, image and samples of the two glyphs match, otherwise False
        :rtype: :class:`boolean`
        """

        if isinstance(self, other.__class__):
            return self.name == other.name and\
                   self.image == other.image and\
                   self.samples == other.samples

        return False

    def show(self):
        self.image.show(title=self.name)
