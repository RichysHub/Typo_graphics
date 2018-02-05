import art_typing
from contextlib import suppress
import os
import json
from PIL import Image

glyph_directory = './Glyphs'

with suppress(FileNotFoundError):
    with open(os.path.join(glyph_directory, 'name_map.json'), 'r') as fp:
        glyph_names = json.load(fp)

glyphs = {}
for filename in os.listdir(glyph_directory):
    if filename.endswith(".png"):

        name = os.path.splitext(filename)[0]
        name = glyph_names.get(name, name)
        path = os.path.join(glyph_directory, filename)
        image = Image.open(path)
        glyphs.update({name: image})

art = art_typing.art_typing(glyphs, glyph_depth=2)

target = Image.open('./dog.png')

calc, out, ins = art.image_to_text(target, )

out.show()
print(ins)