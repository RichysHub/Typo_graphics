import art_typing
from contextlib import suppress
import os
import json
from PIL import Image
from PIL import ImageChops
from random import sample

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

glyph_list = list(glyphs.items())
glyph_list_sample = sample(glyph_list, 20)

output = Image.new("L", (27*25, 24*48))
for i in range(1, 26):
    art = art_typing.ArtTyping(glyphs, glyph_depth=1, samples=(i, min(i*2, 48)))
    for j, (name, image)in enumerate(glyph_list_sample):
        calc, out, ins = art.image_to_text(image, target_size=(1, 1), cutoff=0)
        output.paste(out, ((i-1)*25, (j+2)*48, i*25, (j+3)*48))

for j, (name, image)in enumerate(glyph_list_sample):
    output.paste(image, (26*25, (j+2)*48, 27*25, (j+3)*48))


# Input images are glyph images
# Our code should match these perfectly with the same glyph
# This is only guaranteed at samples=(25, 48)
# Code will run through lots of samples, and find match
# Composed output has target spaced away to the right

# This works PERFECT if we disable the line:
# sized_picture = exposure.rescale_intensity(sized_picture, out_range=self.value_extrema)

# The line:
# self.value_extrema = (150, 250)
# certainly improves reproduction, if the rescale_intensity is present

# Something in the rescaling intensity is throwing it off, and making • overly present
output.show()

# I suppose this is reasonable. We are adjusting a single glyph image to match the full range
# Perhaps a better test would be to take the full set of glyphs, and do this

column_image = Image.new("L", (25, 48*(len(glyph_list))))
for j, (name, image)in enumerate(glyph_list):
    column_image.paste(image, (0, j*48, 25, (j+1)*48))

output = Image.new("L", (25*27, 48*(len(glyph_list)+2)))
for i in range(1, 26):
    art = art_typing.ArtTyping(glyphs, glyph_depth=1, samples=(i, min(i*2, 48)))
    calc, out, ins = art.image_to_text(column_image, target_size=(1, len(glyph_list)), cutoff=0)
    output.paste(out, ((i-1)*25, 48*2, i*25, 48*(len(glyph_list)+2)))

output.paste(column_image, (26*25, 48*2, 27*25, 48*(len(glyph_list)+2)))

output.show()
