Tutorial
========

This tutorial is aimed at introducing the concepts of Typo_graphics, and to get you started converting images to text.
Starting with the most basic uses, and introducing some of the more complex capabilities.


.. currentmodule:: typo_graphics

Basic use
---------

The primary class of Typo_graphics is the :class:`Typograph` class.
The :class:`Typograph` object encapsulates all the processing of glyphs need to transform an image.
If we want to convert several images with the same settings, we need only creates one
:class:`Typograph` object, which avoids repeat processing calculations.

Simple Typograph creation
^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest way to create an instance is without any arguments passed:

.. code-block:: python

    from typo_graphics import Typograph

    typograph = Typograph()


This :class:`Typograph` object will use the default glyphs,
you can examine the glyphs by their names:

.. code-block:: python

    typograph.glyphs['9'].show()

.. glyphdisplay:: 9
    :align: center

    Glyph image for the character ``9``.

The :attr:`~Typograph.glyphs` dictionary will contain all 82 of the glyphs typeable with the SR100 typewriter.

Convert image to glyphs
^^^^^^^^^^^^^^^^^^^^^^^

To convert an image into glyph form, we need only pass a PIL :class:`~PIL.Image.Image` object
to the :meth:`~Typograph.image_to_text` method, as follows:

.. code-block:: python

    from PIL import Image

    target_image = Image.open('dog.png')
    result = typograph.image_to_text(target_image)


.. figure:: ../../../Doc_Images/aus_shep_crop.png
    :align: center

    Input image of Australian shepherd dog.

.. _aus_shep:

This `result`, which will be a :class:`~typo_graphics.typograph.TypedArt` object contains our output.
From this object we can extract the instructions and our reference output image.

.. code-block:: python

    print(result.instructions)

.. literalinclude:: ../../../Doc_Images/aus_shep_crop-instructions.txt
    :language: text
    :lines: 1-16

The first 16 lines of the instructions file are shown here. As the image uses a glyph depth of two, this corresponds to 8 typed lines.
The entire image is rendered here with 32 lines, 60 characters wide.

.. code-block:: python

        result.output.show()

.. figure:: ../../../Doc_Images/aus_shep_crop-output.png
    :align: center

    Reference image from conversion, useful for preview, and for help when typing. Best viewed at a slight distance.


Tuning the result
-----------------

In order to control the appearance of the image, several keyword arguments are available,
for both :meth:`~Typograph.image_text`, and during the instantiation of :class:`Typograph`.

A few are detailed here, see the :ref:`API` for more details.

Larger or smaller images
^^^^^^^^^^^^^^^^^^^^^^^^

When converting an image, :meth:`~Typograph.image_to_text` will make best use of the available space,
scaling the image to best fit within the page. By default, the page is defined to have space for an image 60 characters wide,
and 60 characters tall.

These parameters can be altered by passing a tuple to :meth:`~Typograph.image_to_text` as the keyword argument `max_size`.
These dimensions specify a bounding box, (width, height) in glyphs, within which the image will be scaled.

For example, if you can only fit 30 characters width, and 20 high on the page, we would alter the previous code to:

.. code-block:: python

    from PIL import Image
    from typo_graphics import Typograph

    typograph = Typograph()
    target_image = Image.open('dog.png')
    result = typograph.image_to_text(target_image, max_size=(30, 20))

    result.output.show()

.. figure:: ../../../Doc_Images/aus_shep_30-output.png
    :align: center

    Image of Australian shepherd within a 30 glyph width.

In specifying `max_size`, either one or both of the dimensions can be set to ``None``.
If a single dimension is ``None``, it will be assumed to have infinite space, the image will be scaled to the other dimension.
If both are ``None``, the size of the input image will be closely matched in the output image.

The default fit mode is to scale the image to within the bounds.
If, instead the keyword argument of `fit_mode` is set to "Crop", the image will be minimally cropped, centered on the image.
Cropping requires both dimensions of `max_size` be specified.

Very small scales
^^^^^^^^^^^^^^^^^

At very small scales, the ability to represent all the features of an image with glyphs becomes harder and harder.
The results may surprise you, however. The following is a demonstration of recreating a triangle as it rotates.

.. figure:: ../../../Doc_Images/rotating_triangle.gif
    :align: center

    From left to right: scanned image of typewritten image, the input image,
    the values for glyphs :class:`Typograph` has determined are the best match,
    and the glyphs rendered as :attr:`~typograph.TypedArt.output` with the outline of the triangle overlaid in blue.

I hope you will agree that the ability to convey motion within just 20 glyphs per frame is staggering.


Glyph depth
^^^^^^^^^^^

By default, :class:`Typograph` will stack the glyphs from the SR100 to a depth of 2, that is to say,
it is allowed to add one glyph on top of another, but cannot add more than that.

This stacking drastically increases the possible glyphs, and helps to create darker glyphs than are typeable.
You can control the depth to which glyphs are stacking, by passing an integer to the keyword argument, `glyph_depth`.

.. _shep_single:

The following reproduces the dog image we have seen previously, but without stacking glyphs, by setting `glyph_depth` to 1.

.. code-block:: python

    from PIL import Image
    from typo_graphics import Typograph

    typograph = Typograph(glyph_depth=1)
    target_image = Image.open('dog.png')
    result = typograph.image_to_text(target_image)

    result.output.show()

.. figure:: ../../../Doc_Images/aus_shep_single_depth-output.png
    :align: center

    Reproducing the Australian shepherd dog image, with no glyph overtyping.

.. Note::

    This keyword is on instantiation, not use, as it affects how glyphs are processed and stored internally.

The Glyph class
---------------

The :class:`Glyph` class is used extensively in Typo_graphics to encapsulate the options for what can be typed in a monospaced space.

As we have already seen, by default :class:`Typograph` will construct :class:`Glyph` objects for all of the glyphs from my SR100.
All the possible 2-glyph combinations thereof will also be created as :class:`Glyph` objects, but these are stored separately.

Each glyph object contains an image of its glyph, :attr:`~Glyph.image`. This can be viewed by calling :meth:`~Glyph.show` on the glyph.

A :class:`Glyph` object can be created from a string name, and an :class:`~PIL.Image.Image`.
This name is used extensively in :class:`Typograph`, and is returned by the :meth:`~Glyph.__str__` method.

.. _spacebar_glyph:

The following creates a new glyph, with a solid white image, representing pressing the spaceabar:

.. code-block:: python

    from PIL import Image
    from typo_graphics import Glyph

    blank_image = Image.new((25, 48), "white")
    space = Glyph(name='sp', image=blank_image)

When instantiated in this way, the :attr:`~Glyph.components` with contain only a reference to ``self``.
This is in contrast to when we create :class:`Glyph` objects by overlaying two glyphs atop one another.

The action of overtyping is replicated by adding the two glyphs together. This will return a new :class:`Glyph`,
with their images overlaid. We can show this, using the SR100 :class:`Glyph` objects loaded in with :class:`Typograph`.

.. code-block:: python

    from typo_graphics import Glyph, Typograph

    typograph = Typograph()
    full_stop = typograph.glyphs["."]
    apostrophe = typograph.glyphs["'"]

    exclamation_mark = full_stop + apostrophe
    exclamation_mark.show()

.. figure:: ../../../Doc_Images/exclamation_mark.png
    :align: center

    Exclamation mark :class:`Glyph` image, composed from an apostrophe and a full stop.

Combined glyphs are named according to their components, separated by whitespace.

    >>> exclamation_mark.name
    "' ."

The :attr:`~Glyph.components` attribute contains references to the glyphs that composed the combination glyphs,
here the apostrophe, and the full stop. Components are sorted. This allows glyph addition to be commutative,
so that order of addition is not important.

    >>> [glyph.name for glyph in exclamation_mark.components]
    ["'", '.']

Using Transparency
------------------

By default, :class:`Typograph` will ignore transparency in images.
This can result in transparent regions being treated as if they were solid black.

:meth:`Typograph.image_to_text` accepts the keyword argument `background_glyph`,
which if not ``None`` will enable transparency.

If a :class:`Glyph` object is passed to `background_glyph`, it will be tiled in any region deemed transparent.
In the borders of the transparency, where the image is neither fully opaque, nor fully transparent,
the background glyph is incorporated into the image.

The following creates a :class:`Typograph` object, and uses it to convert a transparent image:

.. code-block:: python

    from PIL import Image
    from typo_graphics import Typograph

    typograph = Typograph()
    plus = typograph.glyphs['+']

    target_image = Image.open('transparent.png')
    result = typograph.image_to_text(target_image, background_glyph=plus)

With this, the image is now overlaid atop a grid of + characters.

The following image set shows the original transparent image, followed by the results when:

1. No `background_glyph` is given, and therefore transparency is not used.
2. `background_glyph` is the plus character, +.
3. `background_glyph` is the :ref:`spacebar glyph <spacebar_glyph>` we created earlier.
4. `background_glyph` is the forward slash character, /.

.. figure:: ../../../Doc_Images/Transparency.png
    :align: center

    Transparent image, recreated with different background glyphs.

Note how at the edges of the transparent shape, where characters are in places that are not fully transparent or opaque,
the background glyph choice affects the glyphs used.
As is default with :class:`Typograph`, these images are created with the SR100 glyph set,
with glyphs stacked up to 2 per space.

It should be noted that `background_glyph` is treated separately from other glyphs,
and so will not be used in opaque regions of the image, unless also present in :attr:`Typograph.glyphs`.

This allows for instance, use of the spacebar glyph for transparency, without allowing the spacebar to be used in the main part of the image.

Using a different set of glyphs
-------------------------------

Typo_graphics was designed to be as independent of font as possible, making few assumptions about characters other than that they are monospaced.
By default Typo_graphics will use the glyph images scanned from my Silver Reed SR100.
These will work perfectly well for typewriters with the same or similar glyphs,
but customisation to the specific machine will produce best results.

In order to use a new set of glyphs, they must be passed to the :class:`~Typograph` upon creation.
There are three ways to instantiate this class, each corresponding to a different way to pass glyph information.

Passing glyphs to Typograph
^^^^^^^^^^^^^^^^^^^^^^^^^^^

:class:`Typograph` will accept a dictionary of :class:`~Glyph` objects,
keyed with the glyph names. This is ideal if you are generating the glyphs dynamically, or wish to preprocess glyphs.

However, often we have our glyph images ready and stored. :class:`Typograph` offers two factory methods,
for use in these cases.

Working from a directory of images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`~Typograph.from_directory` can be used if the glyphs are stored as separate images, within a directory.
This method will look for a ``json`` format file in the same directory by the name of ``name_map.json``,
otherwise glyphs will be named in accordance with their file names.

``name_map.json`` is simply the serialisation of a dictionary, with key, value pairs corresponding to filenames
(without extension) and the desired string name.
The name map for the SR100 glyphs is used to correct the names of capital letters (``A.png`` and ``a.png`` are deemed equal by Windows for example),
as well as including non-valid filename characters such as the question mark.

.. literalinclude:: ../../Glyphs/name_map.json
    :language: json
    :encoding: utf-8

``name_map.json`` is to use "utf-8" encoding, and as such, unicode characters are allowed, if they are a better match.
For the SR100 set, • is used for the dot to separate shillings and pence.

Not all characters need be listed in the name map, anything not listed will simply continue to use the filename, sans extension.
This is why ``a`` does not feature, its image is stored as ``a.png``.

Using a glyph sheet
^^^^^^^^^^^^^^^^^^^

The glyph sheet format allows you to contain all your glyph images, within one image, akin to a sprite sheet.
The most common use case would be for the glyph sheet to be a scan of a typed page of glyphs.
This would require only minor manipulation, to align the image with the page, and remove excess space.

:meth:`~Typograph.from_glyph_sheet` will parse the glyph sheet, splitting it up into the individual glyphs.

In addition to the image, the total number of glyphs must be passed as an integer, as well as some information on how the glyphs are arranged.
Either the dimensions of the grid can be specified, ie. 9 rows, of a maximum of 10 glyphs would be passed as the tuple, (10,9).
Alternatively, the size of the glyphs in (width in pixels, height in pixels) can be passed.

In both cases, the spacing between glyphs must also be given. Glyph names can be passed as a list from top left to bottom right,
if omitted names will be assigned sequentially.

.. code-block:: python

    from PIL import Image
    from typo_graphics import Typograph

    glyph_sheet = Image.open("glyph_sheet.png")
    number_glyphs = 82
    grid_size = (10, 9)

    typograph.from_glyph_sheet(glyph_sheet=glyph_sheet, number_glyphs=number_glyphs, grid_size=grid_size)

Manipulating Typograph's glyphs
-------------------------------

We've seen how we can create a :class:`Typograph` object using glyphs from several sources.
However, what if we want to manipulate the glyphs post instantiation?
:class:`Typograph` exposes two methods for this, :meth:`~Typograph.add_glyph` and :meth:`~Typograph.remove_glyph`.

Adding glyphs
^^^^^^^^^^^^^

We saw earlier how to make a :ref:`spacebar glyph <spacebar_glyph>`,
but how do we get our :class:`Typograph` object to use it in images?

.. code-block:: python

    from PIL import Image
    from typo_graphics import Glyph, Typograph

    blank_image = Image.new((25, 48), "white")
    space = Glyph(name='sp', image=blank_image)
    typograph = Typograph()

    typograph.add_glyph(space)

Any subsequent uses of :meth:`~Typograph.image_to_text` will use the spacebar glyph above to compose the image.

However, if we look for our glyph in `typograph.glyphs`, it will be surprisingly absent.

    >>> 'a' in typograph.glyphs
    True
    >>> 'sp' in typograph.glyphs
    False

So, what is going on? Well, by default :meth:`Typograph.add_glyph` adds our glyph to a separate list of standalone glyphs.

Standalone glyphs
^^^^^^^^^^^^^^^^^

Any :class:`Glyph` objects, present in :attr:`Typograph.glyphs` will be used in combinations.
By default, :attr:`~Typograph.glyph_depth` will be 2, meaning that `typograph` will have constructed and stored all 2-glyph combinations.

The default behaviour of :meth:`~Typograph.add_glyph`, however, is to not use the glyph in combinations.
This might seem odd, but it allows glyphs like the spacebar glyph shown above to be added, and used, without combining them.

In glyph addition, the spacebar acts similar to how zero does in regular arithmetic.
Adding a spacebar glyph to any other glyph, doesn't change that glyph's appearance.
Therefore, if we were to allow spacebar to combine, it would produce 82 additional 2-glyph combinations,
that have the identical image to our base glyphs.

By default, :meth:`~Typograph.add_glyph` will in fact place the glyph within the attribute :attr:`Typograph.standalone_glyphs`.
These glyphs are treated in the same way when matching into an image, but are kept from combinations.

    >>> 'a' in typograph.standalone_glyphs
    False
    >>> 'sp' in typograph.standalone_glyphs
    True

If you **do** want your added glyph to be combined, this is as simple as passing ``True`` to the keyword argument `use_in_combinations`.
The following would add the spacebar glyph into the general glyph pool, for use in combinations,
a reminder that this is **not recommended**, for performance reasons detailed above.

.. code-block:: python

    from PIL import Image
    from typo_graphics import Glyph, Typograph

    blank_image = Image.new((25, 48), "white")
    space = Glyph(name='sp', image=blank_image)
    typograph = Typograph()

    typograph.add_glyph(space, use_in_combinations=True)

..

    >>> 'sp' in typograph.standalone_glyphs
    False
    >>> 'sp' in typograph.glyphs
    True

:class:`Typograph` will keep the two dictionaries of glyphs, :attr:`Typograph.glyphs` and :attr:`Typograph.standalone_glyphs` mutually exclusive.
No glyph should appear in both. As such, adding a glyph to either will simultaneous search and remove it from the other.

    >>> 'sp' in typograph.glyphs
    True
    >>> typograph.add_glyph(space, use_in_combinations=False)
    >>> 'sp' in typograph.glyphs
    False
    >>> 'sp' in typograph.standalone_glyphs
    True

Adding glyphs directly to either of these dictionaries, without using :meth:`~Typograph.add_glyph` will produce erroneous behaviour.

Removing glyphs
^^^^^^^^^^^^^^^

Let us imagine that in using typo_graphics, one of the keys to your typewriter has become stuck.
As such, we now want not to include anything from that key in our images, we need remove them.

Of course, we could remove the image from the directory, if using :meth:`~Typograph.from_directory`,
or we could edit the glyph sheet if using :meth:`~Typograph.from_glyph_sheet`. However, there is an easier way.

Say that the ``M`` key has become stuck, and we want to not use ``M`` or ``m`` glyphs.
Glyphs can be removed by name, as follows:

.. code-block:: python

    from typo_graphics import Typograph

    typograph = Typograph()

    capital_m = typograph.remove_glyph("M")
    lowercase_m = typograph.remove_glyph("m")
    capital_m.show()
    lowercase_m.show()

.. figure:: ../../../Doc_Images/M_and_m.png
    :align: center

    Capital and lowercase m glyphs, removed from :class:`Typograph` instance.

Removed glyphs are returned, in case they wish to be used, which is why we can show them here. If the glyph is not found,
``None`` will be returned instead.
By doing this, we have removed these two glyphs from :attr:`Typograph.glyphs`, which will now only contain 80 items, not the 82 it had prior.

    >>> len(typograph.glyphs)
    80

These glyphs will now not be used in future calls to :meth:`Typograph.image_to_text`,
neither alone or within combinations.

Without additional arguments, :meth:`~Typograph.remove_glyph` will remove the given glyph from both `typograph.glyphs` and `typograph.standalone_glyphs`,
wherever it may appear. If, however, you wish to control the removal, the keyword argument `remove_from` can be specified.

The following are valid values for `remove_from`

    * ``"Combinations"`` or ``"C"`` to remove from combinations (:attr:`Typograph.glyphs`).
    * ``"Standalone"`` or ``"S"`` to remove from standalone glyphs (:attr:`Typograph.standalone_glyphs`).
    * ``"Both"`` or ``"B"`` to remove from both.

Recall that :class:`Typograph` maintains that no glyph appear in both dictionaries simultaneously,
and as such ``"Both"`` is to be interpreted as searching for the glyph in both, and removing it from any it appears in.

    >>> 'a' in typograph.glyphs
    True
    >>> typograph.remove_glyph('a', "Standalone")
    None
    >>> 'a' in typograph.glyphs
    True
    >>> a = typograph.remove_glyph('a', "Combinations")
    >>> 'a' in typograph.glyphs
    False

One way to use :meth:`~Typograph.remove_glyph` and :meth:`~Typograph.add_glyph` together, is to extract a glyph, and insert a new one in its place.

Propose that somehow your ``M`` key had, instead of sticking, suffered damage,
and was now was typing a capital M at the equivalent of 10 pixels below the normal position.

We will use :func:`PIL.ImageChops.offset` to implement this offsetting.

.. code-block:: python

    from PIL.ImageChops import offset
    from typo_graphics import Typograph, Glyph

    typograph = Typograph()

    capital_m = typograph.remove_glyph('M')
    shifted_image = offset(capital_m.image, 0, 10)
    new_capital_m = Glyph(name='M', image=shifted_image)

    typograph.add_glyph(new_capital_m, use_in_combinations=True)

