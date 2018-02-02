from PIL import Image, ImageChops
from contextlib import suppress
import json
import os

class glyph:
    def __init__(self, name=None, image=None, components=None, samples=(3, 3)):
        self.name = name
        self.image = image
        self.fingerprint = self.image.convert("L") \
            .resize(samples, Image.BOX)
        self.fingerprint_display = self.fingerprint.resize(self.image.size)

        if components:
            self.components = components
        else:
            self.components = [self]

    # With no global GLYPH_DIR, should this be from full filepath, from file handle object?
    # Perhaps an option to pass the name_map dict (that opens up options to not use a file for it)
    # Whatever is calling this will preopen the name_map, and can pass through
    # At that point, can't it just set the name as an override?
    @classmethod
    def from_file(cls, filename, **kwargs):
        name = os.path.splitext(filename)[0]
        # looks for name map, and any name alias
        # TODO: probably better in whatever will be making the glyphs
        # --> perhaps an extra override_name arguement that defaults to None
        with suppress(FileNotFoundError):
            with open(os.path.join(GLYPH_DIR, 'name_map.json'), 'r') as fp:
                glyph_names = json.load(fp)
                name = glyph_names.get(name, name)
        image = Image.open(os.path.join(GLYPH_DIR, filename))
        return cls(name=name, image=image, **kwargs)

    def __add__(self, other):
        if not isinstance(other, glyph):
            raise TypeError('can only combine glyph (not "{}") with glyph'.format(type(other)))

        if self.samples != other.samples:
            raise ValueError('Cannot combine glyphs with unequal samples {} =/= {}'.format(self.samples, other.samples))

        name = self.name + ' ' + other.name
        composite = ImageChops.darker(self.image, other.image)
        components = sorted(self.components + other.components, key=lambda g: g.name)
        return glyph(name=name, image=composite, components=components)

    def __str__(self):
        return self.name