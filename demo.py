from PIL import Image
from typo_graphics import Typograph

# Create Typograph instance
typograph = Typograph(glyph_depth=2)

# convert the input image into an image composed of glyphs
target = Image.open('./dog.png')
calc, out, ins = typograph.image_to_text(target, cutoff=0)

# display the output that the instructions would render
out.show()
