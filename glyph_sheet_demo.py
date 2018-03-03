from typo_graphics import typograph
from contextlib import suppress
import os
import json
from math import ceil
from PIL import Image

# look for name_map, if present
glyph_directory = './Glyphs'
with suppress(FileNotFoundError):
    with open(os.path.join(glyph_directory, 'name_map.json'), 'r', encoding="utf-8") as fp:
        glyph_names = json.load(fp)

glyphs = []
names = []
# Load images from the input directory
for filename in os.listdir(glyph_directory):
    if filename.endswith(".png"):

        name = os.path.splitext(filename)[0]
        name = glyph_names.get(name, name)
        path = os.path.join(glyph_directory, filename)
        image = Image.open(path)
        # Paste onto new image to allow equivalence test later
        pasted_image = Image.new("RGBA", image.size)
        pasted_image.paste(image, (0, 0, *image.size))
        glyphs.append(pasted_image)
        names.append(name)

# calculate glyph sheet dimensions
glyph_width, glyph_height = glyphs[0].size
rows = 6
spacing = (25, 48)
columns = ceil(len(glyphs)/rows)
width = (columns * glyph_width) + ((columns-1) * spacing[0])
height = (rows * glyph_height) + ((rows-1) * spacing[1])

glyph_sheet = Image.new("RGBA", (width, height), "white")

# iterate through the glyphs found, and add to the glyph sheet
for index, glyph in enumerate(glyphs):
    i_y = index // columns
    i_x = index % columns
    box = (i_x * (glyph_width + spacing[0]), i_y * (glyph_height + spacing[1]),
           ((i_x + 1) * glyph_width) + (i_x * spacing[0]), ((i_y + 1) * glyph_height) + (i_y * spacing[1]))
    glyph_sheet.paste(glyph, box)

glyph_sheet.show()

# Create Typograph instance using this glyph sheet
art = typograph.Typograph.from_glyph_sheet(glyph_sheet, number_glyphs=len(glyphs), glyph_names=names,
                                           spacing=spacing, grid_size=(columns, rows), glyph_depth=1)

# iterate through the extracted glyphs, and verify they match the input images
for name, glyph in art.glyphs.items():
    input_image = glyphs[names.index(name)]
    if glyph.image != input_image:
        glyph.image.show()
        input_image.show()
        raise ValueError("glyph '{}' not reproduced correctly".format(name))
else:
    print("All glyphs extracted from glyph sheet correctly")
