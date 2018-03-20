Development
===========

.. currentmodule:: typo_graphics

If you want to know more about the development of Typo_graphics, this section is for you.

Inspiration
-----------

This project began when I purchased a Silver Reed SR100 Tabulator typewriter, second hand, for just £1.25.
I had never owned a typewriter before, and I picked it up out of some latent interest in the mechanics, and of typography.

.. figure:: ../../../Doc_Images/SR100.png
    :scale: 75%
    :align: center

    Silver Reed SR100 Typewriter.

This typewriter model doesn't have a ``1`` key, the ``l`` is used in substitute. Similarly, there is no key for ``!``.

Some of the characters that are missing can be made by overtyping, typing a character,
moving the carriage back, and typing another.
To type a ``!``, one must first type ``'``, backspace, and overtype ``.``.

.. figure:: ../../../Doc_Images/Exclamation.png
    :align: center

    Exclamation mark from apostrophe and full stop.

This got me interested in what other combinations exist.
I tried to type out a few such combinations, but with 82 glyphs on the typewriter, attempting to type all would a large task.
Of those I had typed, I found ``:`` and ``-`` would form a ``÷``, but in general it was hard to spot anything of much use.

.. figure:: ../../../Doc_Images/Obelus.png
    :align: center

    Obelus from hyphen and colon.

Trying to find reference material online for what combinations would form what characters, I found little of relevance.
What I did find, was instructions to produce a soldier from O, X, &, /, W, and _ using variable line spacing.
A quick and easy way to make something unusual from a typewriter.

.. figure:: ../../../Doc_Images/Soldiers.png
    :align: center

    Soldiers, formed by stacking characters using variable line spacing.

Further looking into producing this type of images, I came across the book Artyping [Nelson1939]_.
In this book Nelson explores ways to create patterns from characters, for bordering letters, and later showcases some typewritten images.
Soldiers, similar to those above, also feature.

In looking for how to reproduce these more complex images, I found Bob Neill's Book of Typewriter Art [Neill1982]_, which contains page after page of instructions.
However, a problem arose; all of the instructions heavily use the ``@`` key, one which my SR100 lacks.
The author suggests that letters may be substituted, but this is not ideal, and the subject matter is often very dated.

At this time I decided I would build my own program to produce such instructions for my own machine,
for which I had already devised some of the internal logic.


Existing work
-------------

The process of making images from characters is well established in ASCII art.

In looking for simple ASCII art generators, I found many to be very underwhelming.
Many of these would depend on a predetermined scale of brightness, such as ``['.', ',', '+', 'X']``.
Not only did this make the code nontransferable to machines without such characters, but I felt it underutilised the characters.
If two characters have the same average brightness, perhaps ``"`` and ``/``, the above would make no distinction between them,
however they would produce drastically different results.

More advances ASCII art generators **do** appreciate the character forms, but are still lacking.
ASCII art is limited to single characters per space; no overtyping of characters can be done, unlike on the typewriter,
where the user is free to return the carriage without feeding the paper.

It was clear that using such generators was not an acceptable solution, and that something custom would have to be made.

What makes Typo_graphics different?
-----------------------------------

The core tenets that underpin Typo_graphics:

* Remain font independent
* Utilise the characters to their full extent
* Use the typewriters ability to overtype characters, where useful to the image.

Typo_graphics aims to be usable on a wide range of typewriters as possible.
This flexibility would also allow use with block printing, or monospace fonts, though in the latter case overtyping need be disabled.

The main output for Typo_graphics is the instruction set generated.
:meth:`~Typograph.image_to_text` also produces an output image, which is mainly intended as reference while typing, to place oneself.
The output, however, is perfectly usable, without the need to type the instructions out.

.. _instruction_format:

The instruction format
----------------------

The instruction format is heavily borrowed from [Neill1982]_.

Lines of the image are denoted by an integer, starting from 0.
Within each line, characters are grouped together,
and a number prepended to each to indicate how many times that characters should be typed in succession.

Here is an extract from the instructions for the :ref:`single depth Australian shepherd <shep_single>`:

.. literalinclude:: ../../../Doc_Images/aus_shep_single_depth-instructions.txt
    :language: text
    :lines: 1-10

If overtyping is used by the image, and therefore a single image line requires two or more typing passes,
line numbers have letter(s) appended. An example of this can be seen in the instructions for the :ref:`Australian shepherd <aus_shep>`.

.. literalinclude:: ../../../Doc_Images/aus_shep_crop-instructions.txt
    :language: text
    :lines: 1-10

In contrast to the Neill format, Typo_graphics does not expect the character grid to be square.
Instead, images are expected to be typed using single line spacing, such that the top of one row of glyphs sits touching the bottom of the previous row.

In practice, the code works equally well for greater line spacing, by including said space into the :class:`Glyph` images, though the result will likely have a banded look.
Using a glyph size smaller than the line spacing would also work, though characters that extend past their bounds may interfere with the image.

.. [Nelson1939] Artyping, Julius Nelson, 1939 (viewable https://archive.org/details/Artyping )
.. [Neill1982] Bob Neill's Book of Typewriter Art (with special computer program), Bob Neill, 1982 (viewable https://loriemersondotnet.files.wordpress.com/2013/01/typewriterart.pdf )