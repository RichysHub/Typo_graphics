import typograph
from contextlib import suppress
import os
import json
from PIL import Image

glyph_directory = './Glyphs'

with suppress(FileNotFoundError):
    with open(os.path.join(glyph_directory, 'name_map.json'), 'r', encoding="utf-8") as fp:
        glyph_names = json.load(fp)

glyphs = {}
for filename in os.listdir(glyph_directory):
    if filename.endswith(".png"):

        name = os.path.splitext(filename)[0]
        name = glyph_names.get(name, name)
        path = os.path.join(glyph_directory, filename)
        image = Image.open(path)
        glyphs.update({name: image})

# Input images are glyph images
# Our code should match these perfectly with the same glyph
# This is only guaranteed at samples=(25, 48)
# Code will run through lots of samples, and find match
# Composed output has target spaced away to the right

# rescale_intensity is disabled, as it throws off the matching, and makes • overly present

glyph_list = list(glyphs.items())
glyph_list.sort(key=lambda item: item[0])

column_image = Image.new("L", (25, 48*(len(glyph_list))))
for j, (name, image)in enumerate(glyph_list):
    column_image.paste(image, (0, j*48, 25, (j+1)*48))

output = Image.new("L", (25*27, 48*(len(glyph_list)+2)))
for i in range(1, 26):
    art = typograph.Typograph(glyphs, glyph_depth=1, samples=(i, min(i * 2, 48)))
    calc, out, ins = art.image_to_text(column_image, target_size=(1, len(glyph_list)), cutoff=0,
                                       use_clahe=False, rescale_intensity=False)
    output.paste(out, ((i-1)*25, 48*2, i*25, 48*(len(glyph_list)+2)))

output.paste(column_image, (26*25, 48*2, 27*25, 48*(len(glyph_list)+2)))

output.show()
