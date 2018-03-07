from typo_graphics import typograph
from PIL import Image

# Create Typograph instance
art = typograph.Typograph(glyph_depth=2)

# convert the input image into an image composed of glyphs
target = Image.open('./dog.png')
calc, out, ins = art.image_to_text(target, cutoff=0)

# display the output that the instructions would render
out.show()
