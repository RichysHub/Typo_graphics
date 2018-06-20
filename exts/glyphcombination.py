import posixpath
from hashlib import sha1 as sha
from os import path

from PIL import Image
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import ensuredir
from sphinx.util.compat import Directive
from typo_graphics import Typograph

from sphinx.ext.graphviz import figure_wrapper

# sphinx extension to allow for easy inclusion of glyph construction images
# code based on sphinxcontrib-proceduralimage


def align(argument):
    """Conversion function for the "align" option."""
    return directives.choice(argument, ('left', 'center', 'right'))


typograph = Typograph()


class glyphcombination(nodes.General, nodes.Element):
    pass


class Glyphcombination(Directive):
    """
    Directive to generate an image of a glyph decomposition.

    Arguments specify glyphs to use in the combination
    separated by whitespace
    'com' provided as alternative to ','

    ##content is included as a caption, in the same fashion as figure directive
    ##has option align, which matches figure directive
    """
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'align': align
    }

    def run(self):
        base, *arguments = self.arguments[0].split()

        # have to provide an alternative entry method for ',' for csv-table usage
        if base == "com":
            base = ","

        try:
            glyph = typograph.glyphs[base]
        except KeyError:
            return [self.state_machine.reporter.warning(
                'Ignoring "glyphcombination" directive with invalid required glyph, {}'.format(base),
                line=self.lineno)]

        for character in arguments:

            if character == "com":
                character = ","

            try:
                glyph += typograph.glyphs[character]
            except KeyError:
                return [self.state_machine.reporter.warning(
                    'Ignoring "glyphcombination" directive with invalid optional glyph, {}'.format(character),
                    line=self.lineno)]

        node = glyphcombination()
        node['glyph'] = glyph
        node['options'] = self.options

        if self.content:
            node = figure_wrapper(self, node, '\n'.join(self.content))
            node['caption'] = '\n'.join(self.content)

        if 'align' in self.options:
            node['align'] = self.options['align']

        return [node]


def render_glyphcombination(self, glyph):

    components = glyph.components
    number_components = len(components)
    if number_components == 1:
        return glyph.image
    else:
        glyph_width, glyph_height = glyph.image.size
        out_width = ((2 * number_components) + 1) * glyph_width
        out_image = Image.new(glyph.image.mode, (out_width, glyph_height), "white")

        for index, component in enumerate(components):
            box = (2 * index * glyph_width, 0, ((2 * index) + 1) * glyph_width, glyph_height)
            out_image.paste(component.image, box)

        out_image.paste(glyph.image, (2 * number_components * glyph_width, 0,
                                      ((2 * number_components) + 1) * glyph_width, glyph_height))

    return out_image


def make_glyphcombination_files(self, node, glyph, prefix='glyphcombination'):
    # if the image has already been made, take it from the cache

    hashkey = glyph.name.encode('utf-8')
    filename = '{}-{}.{}'.format(prefix, sha(hashkey).hexdigest(), "png")

    relative_filename = posixpath.join(self.builder.imgpath, filename)
    output_filename = path.join(self.builder.outdir, '_images', filename)

    if not path.isfile(output_filename):  # if image not already created

        image = render_glyphcombination(self, glyph)

        if image is None:
            relative_filename = None
        else:
            ensuredir(path.dirname(output_filename))
            image.save(output_filename)

    return relative_filename


def render_glyphcombination_html(self, node, glyph, options, prefix='glyphcombination'):

    relative_filename = make_glyphcombination_files(self, node, glyph, prefix)
    if 'caption' not in node:
        atts = {'class': 'glyphcombination',
                'src': relative_filename}
        if node.get('align'):
            atts['class'] += " align-" + node['align']

        self.body.append(self.starttag(node, 'img', **atts))
    raise nodes.SkipNode


def html_visit_glyphcombination(self, node):
    render_glyphcombination_html(self, node, node['glyph'], node['options'])


def setup(app):
    app.add_node(glyphcombination,
                 html=(html_visit_glyphcombination, None))
    app.add_directive('glyphcombination', Glyphcombination)
