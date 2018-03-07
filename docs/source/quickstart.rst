Getting started
===============

.. currentmodule:: typo_graphics

Using the Typograph class
-------------------------

The primary class of Typo_graphics is the :class:`Typograph` class.
The simplest way to create an instance is without any arguments passed:

    >>> from typo_graphics import Typograph
    >>> typograph = Typograph()

This :class:`Typograph` object will use the default glyphs,
you can examine the glyphs by their names:

    >>>typograph.glyphs['W'].show()

