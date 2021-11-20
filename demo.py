from PIL import Image
from typo_graphics import Typograph

# Create Typograph instance
typograph = Typograph(glyph_depth=2)

# convert the input image into an image composed of glyphs
target = Image.open('./docs/source/Images/aus_shep_crop.png')
calc, out, ins = typograph.image_to_text(target)

# display the output that the instructions would render
out.show()
