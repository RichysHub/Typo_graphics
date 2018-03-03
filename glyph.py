from PIL import Image, ImageChops
from contextlib import suppress
import json
import os


class Glyph:
    """
    Represents the ink typed into one monospaced space.

    This can comprise of multiple component glyphs, which are retained in :attr:`components`.
    In the case that the glyph is as typed, this will contain simply a reference to self.

    Exposes following instance attributes:
     - :attr:`name`, the name of the glyph
     - :attr:`image`, :class:`~PIL.Image.Image` image of the glyph.
     - :attr:`components`,
     - :attr:`samples`, tuple of ints governing how the glyph is down-sampled for matching
     - :attr:`fingerprint`, scaled :class:`~PIL.Image.Image` showing how glyph is internally processed
     - :attr:`fingerprint_display`, rescaled version of :attr:`fingerprint`, to size of original :attr:`image`

    Explicitly supports summation with other glyph objects
    """
    def __init__(self, name=None, image=None, components=None, samples=(3, 3)):
        """
        Create glyph object

        :param str name: name of glyph, used both internally and when creating instructions with glyphs
        :param image: an :class:`~PIL.Image.Image` of the glyph. Likely sourced from scanned typewritten page.
        :type image: :class:`~PIL.Image.Image`
        :param components: glyphs that are used to create this glyph.
         If not specified, will default to containing this glyph.
        :type components: list(:class:`~glyph.Glyph`)
        :param samples: size specified in an integer, integer tuple for the fingerprint to be scaled to.
         Specified as number of pixels across, by number of pixels .
        :type samples: tuple(int, int)
        """
        self.name = name
        self.image = image
        self.samples = samples
        self.fingerprint = self.image.convert("L").resize(samples, Image.BOX)
        self.fingerprint_display = self.fingerprint.resize(self.image.size)

        if components:
            self.components = components
        else:
            self.components = [self]

    # This has been largely replaced by the glyph loading code within Typograph. This will likely be removed in future
    @classmethod
    def from_file(cls, filename, **kwargs):
        name = os.path.splitext(filename)[0]
        # looks for name map, and any name alias
        # TODO: probably better in whatever will be making the glyphs
        # --> perhaps an extra override_name argument that defaults to None
        with suppress(FileNotFoundError):
            with open(os.path.join(GLYPH_DIR, 'name_map.json'), 'r') as fp:
                glyph_names = json.load(fp)
                name = glyph_names.get(name, name)
        image = Image.open(os.path.join(GLYPH_DIR, filename))
        return cls(name=name, image=image, **kwargs)

    def __add__(self, other):
        """
        Addition override

        Addition of glyphs encapsulates overlaying the two glyphs on a typewriter.
        This would be achieved by first typing ``glyph1``, moving the carriage back, and typing ``glyph2`` in the same space.
        Image combination is achieved with :func:`~PIL.ImageChops.darker`

        If the ``samples`` of the two glyphs are not equal, a ``ValueError`` is raised.

        The returned :class:`~glyph.Glyph`
        Addition of two glyphs returns a new glyph object, combining images with :func:`~PIL.ImageChops.darker`,
        and combining names with a space

        :param other: glyph to add
        :type other: :class:`~glyph.Glyph`
        :return: composite glyph of this, and the `other` glyph
        :rtype: :class:`~glyph.Glyph`
        :raises ValueError: if ``samples`` attribute of the two glyphs do not match
        :raises TypeError: if addition is attempted with an object **not** of type :class:`~glyph.Glyph`
        """
        if not isinstance(other, Glyph):
            raise TypeError('can only combine glyph (not "{}") with glyph'.format(type(other)))

        if self.samples != other.samples:
            raise ValueError('Cannot combine glyphs with unequal samples {} =/= {}'.format(self.samples, other.samples))

        name = self.name + ' ' + other.name
        composite = ImageChops.darker(self.image, other.image)
        components = sorted(self.components + other.components, key=lambda g: g.name)
        return Glyph(name=name, image=composite, components=components, samples=self.samples)

    def __str__(self):
        return self.name
