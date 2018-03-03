Using a new glyph set
=====================

In order to use a new set of glyphs, they must be passed to the :class:`~typograph.Typograph` upon creation.
There are three ways to instantiate this class, each correspoding to a different way to pass glyph information.

:meth:`~typograph.Typograph.__init__` will accept a dictionary of :class:`~glyph.Glyph` objects,
keyed with the glyph names. This is ideal if you are generating the glyphs dynamically, or wish to preprocess glyphs.

:meth:`~typograph.Typograph.from_directory` can be used if the glyphs are stored as seperate images, within a directory.
This method will look for a ``json`` format file in the same directory by the name of ``name_map.json``,
otherwise glyphs will be named in accordance with their filenames.

:meth:`~typograph.Typograph.from_glyph_sheet` can be used to parse a sheet of glyphs.
Such a glyph sheet could be created dynamically, or could be a scan of a typed page of glyphs.