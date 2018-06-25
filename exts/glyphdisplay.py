"""
Sphinx extension for inclusion of images of glyphs and glyph constructions

Provides two directives,
glyphdisplay
glyphdecomposition

which are backed by one node, the glyphdisplay node

Code based on sphinxcontrib-proceduralimage
"""

import posixpath
from functools import reduce
from hashlib import sha1 as sha
from operator import add
from os import path

from PIL import Image
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.ext.graphviz import figure_wrapper
from sphinx.util import ensuredir
from sphinx.util.compat import Directive
from typo_graphics import Typograph


def align(argument):
    """Conversion function for the "align" option."""
    return directives.choice(argument, ('left', 'center', 'right'))


def presentation(argument):
    """Conversion function for the "presentation" option."""
    return directives.choice(argument, ('list', 'composition', 'decomposition'))


typograph = Typograph()


class glyphdisplay(nodes.General, nodes.Element):
    pass


class Glyphdisplay(Directive):
    """
    Directive to generate an image of a glyph decomposition.

    Arguments specify glyphs to use in the combination
    separated by whitespace
    'com' provided as alternative to ','

    content is included as a caption, in the same fashion as figure directive
    has align option: left, center, or right
    has presentation option: list, composition, or decomposition

    -list
    glyphs provided are reproduced, in order

    -composition
    glyphs provided are all combined, and only this resulting glyph is shown

    -decomposition
    all glyphs are combined, this images is then shown preceded by the images of all component glyphs

    has spacing option: [0, inf)

    how many glyphs widths should be used as spacing between characetrs
    default is 1

    """
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'align': align,
        'presentation': presentation,
        'spacing': directives.nonnegative_int,
    }

    def run(self):

        # have to provide an alternative entry method for ',' for csv-table usage
        arguments = self.arguments[0].replace('com', ',').split()

        try:
            glyphs = [typograph.glyphs[argument] for argument in arguments]
        except KeyError as ke:
            return [self.state_machine.reporter.warning(
                'Ignoring "glyphdisplay" directive with invalid glyph, {}'.format(ke),
                line=self.lineno)]

        node = glyphdisplay()
        node['glyphs'] = glyphs
        node['options'] = self.options

        if self.content:
            node = figure_wrapper(self, node, '\n'.join(self.content))
            node['caption'] = '\n'.join(self.content)

        if 'align' in self.options:
            node['align'] = self.options['align']

        return [node]


def render_glyphdisplay(self, glyphs, options):
    """
    Given a set of glyphs, and the options for the directive, return the image for the directive
    """

    presentation_choice = options.get('presentation', 'list')  # default is list display
    spacing = options.get('spacing', 1)  # by default, we space out the output with 1 glyph space

    if presentation_choice == 'composition':
        # combine all the glyphs, and just take the result
        glyph = reduce(add, glyphs)
        glyphs = [glyph]

    if presentation_choice == 'decomposition':
        if len(glyphs) > 1:
            # we combine the glyphs, and peel out the components so that they are sorted
            glyph = reduce(add, glyphs)
            glyphs = glyph.components
            # add the glyph on the end, to show the result
            glyphs.append(glyph)

    number_glyphs = len(glyphs)

    if number_glyphs == 1:
        # handles composition, list of 1, decomposition of 1
        return glyphs[0].image
    else:
        glyph_width, glyph_height = glyphs[0].image.size

        out_width = number_glyphs * glyph_width + (number_glyphs - 1) * spacing * glyph_width
        out_image = Image.new(glyphs[0].image.mode, (out_width, glyph_height), "white")

        spacing_factor = spacing + 1

        for index, glyph in enumerate(glyphs):
            box = (spacing_factor * index * glyph_width, 0, ((spacing_factor * index) + 1) * glyph_width, glyph_height)
            out_image.paste(glyph.image, box)

    return out_image


def make_glyphdisplay_files(self, node, glyphs, options, prefix='glyphdisplay'):
    """
    Given a set of glyphs and options, returns the relative filename for the resulting image
    """

    # Create a hash key, for uniquely saving each image.
    # Options are included, so that a combined !, and a decomposed one result in differing hashes.
    hash_factors = [glyph.name for glyph in glyphs] + [*options]
    hashkey = b''.join(factor_part.encode('utf-8') for factor_part in hash_factors)
    filename = '{}-{}.{}'.format(prefix, sha(hashkey).hexdigest(), "png")

    relative_filename = posixpath.join(self.builder.imgpath, filename)
    output_filename = path.join(self.builder.outdir, '_images', filename)

    if not path.isfile(output_filename):  # if image not already created
        image = render_glyphdisplay(self, glyphs, options)

        if image is None:
            relative_filename = None
        else:
            ensuredir(path.dirname(output_filename))
            image.save(output_filename)

    return relative_filename


def render_glyphdisplay_html(self, node, glyphs, options, prefix='glyphdisplay'):
    """
    From the node, glyphs and any options, correctly renders the node
    """

    relative_filename = make_glyphdisplay_files(self, node, glyphs, options, prefix)
    if 'caption' not in node:
        atts = {'class': 'glyphdisplay',
                'src': relative_filename}
        if node.get('align'):
            atts['class'] += " align-" + node['align']

        self.body.append(self.starttag(node, 'img', **atts))
    raise nodes.SkipNode


def html_visit_glyphdisplay(self, node):
    render_glyphdisplay_html(self, node, node['glyphs'], node['options'])


class Glyphdecomposition(Glyphdisplay):
    """
    Simple alias for a glyphdisplay node, for which the presentation is set to decomposition

    Included so as to make the combinations page much less cumbersome in source
    """

    def run(self):
        self.options.update({'presentation': 'decomposition'})
        return super().run()


def setup(app):
    app.add_node(glyphdisplay,
                 html=(html_visit_glyphdisplay, None))
    app.add_directive('glyphdisplay', Glyphdisplay)
    app.add_directive('glyphdecomposition', Glyphdecomposition)
