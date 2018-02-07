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


# glyph_list = list(glyphs.items())
# glyph_list = sample(glyph_list, 10)
# glyphs = dict(glyph_list)
# desired_characters = '.:+=_-/"()'
# glyphs = {k: v for k, v in glyphs.items() if k in desired_characters}

art = art_typing.ArtTyping(glyphs, glyph_depth=2)

target = Image.open('./dog.png')

calc, out, ins = art.image_to_text(target, cutoff=0)
out.show()
# print(ins)