Concepts
========

.. currentmodule:: typo_graphics

This section contains some more in depth detail about the decisions involved in creating Typo_graphics,
as well as some of the logic that built the foundations for some of the methods.
This section will feature some mathematical rigour, where deemed necessary.

Glyphs
------

Typewriters are, for the most part, monospace writing machines.
As such they are only able of placing ink within a bounding box, the space of one glyph.

Anything that can be typed, either with a single keypress, or by holding a modifier key such as Shift, is referred to as a glyph.
Glyphs produced in this way are referred to as typeable. Typeable glyphs are what one would think of as a character on a typewriter.

In addition to typeable glyphs, Typo_graphics considers composite glyphs. These are glyphs created by overtyping one glyph upon another.
Typo_graphics considers only the problem of composing monospace glyphs, not duospace or variable width characters.

Samples
-------

When considering the shape of a glyph, there is a certain amount of detail that can be ignored.
When a glyph is created, a second image is made, scaled down. It is this image that is used internally for matching to the image.

To what level this image is scaled down can affect the results obtained. By default, glyphs are scaled to an image 3 pixels by 3 pixels.
Higher samples tend to take longer to process, but give more accurate results.
Lower samples are much quicker, but will focus less on glyph shape, and more on average brightness of the glyph as a whole.

With samples of (3, 3), each pixel will be an average value of that ninth of the input glyph image.
This allows for concepts such as how bright the center ninth of the pixel is, which will be used when matching.

This sample sized version of a glyphs image can be accessed with :attr:`Glyph.fingerprint`.
An additional version of this image, scaled back up to the original glyph size is also creates, :attr:`Glyph.fingerprint_display`.

Chunking
--------

In order to match glyphs, we must first split our image up into glyph size chunks.
This is the action of :meth:`Typograph._chunk`, which takes the input image and renders regions of pixels,
equal to the sample size of the glyphs.

Each chunk of the image is treated entirely independently.
This approach therefore does pose problems in extending the program to duospace fonts, or for half line spacing.
In both of these cases, the chunks would have interdependency.

Glyph matching
--------------

Matching glyphs to parts of images is a nontrivial task.
From chunking we have produced pixel chunks, corresponding to sample shaped regions of the input image.
By default these will contain 9 values, ranging from 0 to 255.

If we ignore the combination glyphs, the SR100 typewriter offers 82 typeable glyphs.
While this may seem a lot, it pales in comparison to the 256^9 = 4,722,366,482,869,645,213,696 possible 9 pixel chunks.

The matching problem, it was found, can be viewed as analogous to the nearest neighbour problem,
and therefore tackled with known approaches.

Nearest neighbour
^^^^^^^^^^^^^^^^^

How does matching a glyph to a set of pixels become a nearest neighbour problem?

First let us consider the simplest case, where samples is (1, 1).
In this case, nothing about glyph shape matters, all that goes into the calculation is the average luminosity value.
This average value is effectively a brightness score, a position on the scale from 0 to 255,
where 0 would be an entirely black glyph, and 255, an entirely white one.

Very empty characters, like the full stop would have a very high value.

.. figure:: ../../Glyphs/dot.png
    :align: center

    The full stop, a very empty character.

Whereas very full characters, like the dollar sign, are much heavier with ink.

.. figure:: ../../Glyphs/dollar.png
    :align: center

    The dollar sign, a very heavy character.

Analysing all the glyphs in the SR100 set, we could form a scale from 0 to 255.
Whenever we want to match a pixel of the image, we would look for the glyph closest to the average value of said pixel.
That glyph would be our closest match, and would be used for that region of the image.

Extending this, consider the case in which it is (1, 2), that is to say, 1 sample across and 2 down.
In this case, our fingerprint images now give the concepts of upper half value, and lower half value.

.. figure:: ../../Glyphs/under.png
    :align: center

    The underscore, a very bottom heavy character.

Characters that are very bottom heavy, such as the underscore will have be dark in the lower half, and near white in the upper.
The reverse of this would be true of upper heavy characters such as quotation marks.

.. figure:: ../../Glyphs/quote.png
    :align: center

    The quotation mark, a very top heavy character.

To match a glyph now, however, we have to consider the value of both halves, in conjunction.
To visualise, we imagine that the typeable glyphs exist on a 2d plane,
with the x axis being the lower half value, and the y axis the upper half value.

Our image chunk is now a point in this 2D space, and we can use euclidean distance to find how far it is from every glyph.
In doing so, we can pick the shortest 'distance', which is our closest glyph.

Calculating the distance to every glyph, however, is very costly.
This is an example of the nearest neighbour problem in two dimensions.
Much more optimal approaches exist, such as the k-d tree that Typo_graphics utilises.

As samples increases, so does the dimensionality of the nearest neighbour search.
At (3, 3), we are using 9 dimensional space.
The specific implementation of k-d tree, :class:`~scipy.spatial.cKDTree` openly admits its searches are not much more
efficient than brute force, for high numbers of dimensions. This is an open problem.

Close enough matching
^^^^^^^^^^^^^^^^^^^^^

When we include the combination glyphs that Typo_graphics uses, by default stacking to a depth of 2,
often the best match is a 2-glyph stack. This would be expected just based on the number of each type,
there is an order of magnitude more combination glyphs.

However, typing a combination glyph is usually more work than typing a single glyph.
The exact handling of this is imprecise, it does not include considerations of having to press the shift key,
or perhaps having to switch to a specific mode on an electronic typewriter.
It also assumes that advancing the carriage one space (normally just pressing the spacebar) is not an expensive action.

What we can say, is that typing 2 glyphs is harder than 1.
The most labour intensive way would be to type one glyph, backspace, and overtype another.
We know, that to type two glyphs, will be at least as difficult as to type one glyph, then another.

Assuming the backspace is just like any other key,
the effort to type a 2-glyph stack is thus: :math:`2 E_1 \leq E_2 \leq 3 E_1`.
Where :math:`E_1` is the effort to type a single glyph, and :math:`E_2` that of a 2-glyph stack.
We will work on the lowest bound for this, and claim :math:`E_2 = 2 E_1` and that :math:`E_2` will be equal to :math:`E_1`,
plus some 'extra effort', :math:`\varepsilon`.

We would only have elected to use the 2-glyph stack in the first place,
if it were closer to the pixel chunk in the n-dimensional neighbour search space.
As such, the value of :math:`d_1 - d_2` is known to be positive,
if :math:`d_n` is the distance from the pixel chunk to the glyph stack.

In order to get a sense of scale for this :math:`d_1 - d_2`, let us introduce :math:`\bar{d}`.
This :math:`\bar{d}` is the distance from our pixel chunk to a glyph, on average.
We will ignore the specifics on how we calculate :math:`\bar{d}` for now.

We can say that if :math:`\dfrac{d_1 - d_2}{\bar{d}}` is small enough, the single stack is close enough,
and it is easier to substitute the 2-glyph stack with it.
Also, if it is a lot of extra effort to type the 2-glyph stack, we would accept a less close match.

The proposed form is then,

.. math::

    \frac{d_1 - d_2}{\varepsilon \bar{d}} < c

Where :math:`c` is some tunable cutoff value.

To generalise, to compare two stacks of a, and b glyphs, where :math:`a > b`,

.. math::

    \frac{d_b - d_a}{\varepsilon (a - b) \bar{d}} < c

We can then combine the :math:`\varepsilon` and :math:`c` parameters into a single cutoff value,

.. math::

    \frac{d_b - d_a}{(a - b) \bar{d}} < \text{cutoff}

This cutoff value is directly implemented as the keyword parameter `cutoff` for :meth:`~Typograph.image_to_text`.
The default value is 0, which will disable this 'close-enough' evaluation.
A value of 1 would result in only single glyphs being used.

Centroid calculation
^^^^^^^^^^^^^^^^^^^^

Calculating :math:`\bar{d}`, the distance of our chunk to a glyph, on average, if done naively, is a very costly procedure.
For each chunk, of which we expect on the order of several thousand,
we would have to calculate distances in 9 dimensional space to thousands of glyphs.

In order to tackle this hefty workload in a smarter way, we employ use of a centroid.
Upon creation of each :class:`~typo_graphics.typograph.tree_set`, the centroid of the glyphs in that collection is calculated.
The centroid is defined as the average position in sample parameter space, so by default it will be a 9 dimensional point.

:math:`\bar{d}` is the Root Mean Square Distance (RMSD) to glyphs in the collection.
As stated before, to manually calculate this would be to calculate all distance squares, take a mean, and then square root.

We can introduce the centroid :math:`m`, to alleviate this issue.

.. math::

    \text{RMSD} &= \sqrt{\frac{1}{N}\sum_{i=1}^N (x_i - p)^2}

    (x_i - p)^2 &= (x_i - m + m - p)^2

                &= (x_i - m)^2 + (m - p)^2 + 2(x_i - m)(m - p)

Where :math:`x_i` denote glyph positions, and :math:`p` our chunk point in the sample space.
However, we know that :math:`(m - p)` is constant,

.. math::

    N (\text{RMSD})^2 &= \sum_{i=1}^N (x_i - p)^2

                      &= N(m-p)^2 + \sum_{i=1}^N \{(x_i - m)^2 + 2(x_i - m)(m - p)\}

                      &= N(m-p)^2 + \sum_{i=1}^N (x_i - m)^2 + 2(m-p)\sum_{i=1}^N (x_i - m)

But, by definition of the centroid, the second summation vanishes,

.. math::

    \text{RMSD} = \sqrt{(m-p)^2 + \frac{1}{N}\sum_{i=1}^N (x_i - m)^2}

The second term inside the square root is simply the mean square distance from centroid,
which is a constant over the :class:`~typo_graphics.typograph.tree_set`, and can also be calculated at creation time.

This derivation allows us to calculate :math:`\bar{d}`, needing only to calculate its distance from one point, the centroid.

Instruction format
------------------


Sorting instructions
^^^^^^^^^^^^^^^^^^^^
