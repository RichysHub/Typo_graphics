Using a new glyph set
=====================

.. currentmodule:: typo_graphics

By default Typo_graphics will use the glyph images scanned from my Silver Reed SR100.
These will work perfectly well for typewriters with the same or similar glyphs,
but customisation to the specific machine will produce best results.

In order to use a new set of glyphs, they must be passed to the :class:`~Typograph` upon creation.
There are three ways to instantiate this class, each corresponding to a different way to pass glyph information.

:meth:`~Typograph.__init__` will accept a dictionary of :class:`~Glyph` objects,
keyed with the glyph names. This is ideal if you are generating the glyphs dynamically, or wish to preprocess glyphs.

:meth:`~Typograph.from_directory` can be used if the glyphs are stored as separate images, within a directory.
This method will look for a ``json`` format file in the same directory by the name of ``name_map.json``,
otherwise glyphs will be named in accordance with their file names.

:meth:`~Typograph.from_glyph_sheet` can be used to parse a sheet of glyphs.
Such a glyph sheet could be created dynamically, or could be a scan of a typed page of glyphs.