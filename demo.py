import art_typing
from PIL import Image

glyph_directory = './Glyphs'
art = art_typing.ArtTyping.from_directory(glyph_directory, glyph_depth=2)

target = Image.open('./dog.png')
calc, out, ins = art.image_to_text(target, cutoff=0)

out.show()
