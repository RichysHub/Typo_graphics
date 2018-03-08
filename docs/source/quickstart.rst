Getting started
===============

.. currentmodule:: typo_graphics

Using the Typograph class
-------------------------

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

.. figure:: ../../Glyphs/9.png
    :scale: 200%
    :align: center

    Glyph image for the character ``9``.

By default, :attr:`~Typograph.glyph_depth` will be 2,
meaning that glyphs will have been constructed for all 2 glyph combinations.

Convert image to glyphs
^^^^^^^^^^^^^^^^^^^^^^^

To convert an image into glyph form, we can use the following:

.. code-block:: python

    from PIL import Image

    target_image = Image.open('dog.png')
    result = typograph.image_to_text(target_image)

`result`, which will be a :class:`~typo_graphics.typograph.typed_art` object contains our output.
From this object we can extract the instructions, output image,
and even peer into the workings of the code by looking at the calculation image.

.. code-block:: python

    print(result.instructions)


.. code-block:: python

    result.output.show()


.. code-block:: python

    result.calculation.show()

Using a different set of glyphs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

passed directly
^^^^^^^^^^^^^^^

glyph sheet
^^^^^^^^^^^

directory
^^^^^^^^^


Adding glyphs
^^^^^^^^^^^^^

Removing glyphs
^^^^^^^^^^^^^^^

standalone glyphs
^^^^^^^^^^^^^^^^^

Transparency
^^^^^^^^^^^^

What is samples for?
^^^^^^^^^^^^^^^^^^^^

glyph depth
^^^^^^^^^^^

sizing
^^^^^^

cutoff
^^^^^^

resize mode
^^^^^^^^^^^

clip limit
^^^^^^^^^^

rescale intensity
^^^^^^^^^^^^^^^^^

enhance contrast
^^^^^^^^^^^^^^^^

instruction spacer
^^^^^^^^^^^^^^^^^^
