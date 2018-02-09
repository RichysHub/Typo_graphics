from glyph import Glyph
from collections import namedtuple
import functools
import itertools
import operator
from PIL import Image
import os
import numpy as np
from scipy.spatial import cKDTree
import string
from skimage import exposure


tree_set = namedtuple('tree_set', ['glyph_set', 'tree', 'centroid',
                                   'mean_square_from_centroid', 'stack_size'])

# TODO dump list
# Support for transparent images, with any glyph as background
# Enhanced image production for single glyph stacking
# --> looks to be issue with how we calculate self.value_extrema
# support for loading glyphs in from other sources
# --> directory with name_map
# --> Sprite sheet style format with {offsets, glyph sizes} specified


class ArtTyping:

    # going with the glyphs being passed as a dict with {name:image}
    def __init__(self, glyph_images, samples=(3, 3), glyph_depth=2):
        self.samples = samples
        self.sample_x, self.sample_y = samples
        self.glyphs = {}
        for name, image in glyph_images.items():
            glyph_ = Glyph(name, image, samples=samples)
            # TODO perhaps we no longer need this dict format
            self.glyphs.update({glyph_.name: glyph_})

        # TODO ugly, would be cleaner if glyphs were in a sequence
        self.glyph_width, self.glyph_height = list(self.glyphs.values())[0].image.size
        self.glyph_depth = glyph_depth
        self.tree_sets = self.calculate_trees()
        self.average_values = self.average_glyph_values()
        self.value_extrema = self.glyph_value_extrema()

    @classmethod
    def from_glyphsheet(cls, glyph_sheet, number_glyphs=None, glyph_dimensions=None, grid_size=None,
                        glyph_names=None, spacing=(0, 0), **kwargs):

        if not number_glyphs:
            raise TypeError("from_glyphsheet() missing required argument 'number_glyphs'")

        if not (glyph_dimensions or grid_size):
            raise TypeError("from_glyphsheet() missing required argument "
                            "'grid_size' or 'glyph_dimensions'")

        sheet_width, sheet_height = glyph_sheet.size
        spacing_x, spacing_y = spacing

        if grid_size:
            grid_width, grid_height = grid_size
            glyph_width = (sheet_width - (spacing_x * (grid_width - 1))) / grid_width
            glyph_height = (sheet_height - (spacing_y * (grid_height - 1))) / grid_height
            if not (glyph_width.is_integer() and glyph_height.is_integer()):
                raise ValueError("incorrect glyph counts for image and dimensions given")
            glyph_width = int(glyph_width)
            glyph_height = int(glyph_height)
        else:
            glyph_width, glyph_height = glyph_dimensions
            grid_width = (sheet_width + spacing_x) / (glyph_width + spacing_x)
            grid_height = (sheet_height + spacing_y) / (glyph_height + spacing_y)

        glyph_images = {}
        for i_y in range(grid_height):
            for i_x in range(grid_width):
                box = (i_x * (glyph_width + spacing_x), i_y * (glyph_height + spacing_y),
                       ((i_x + 1) * glyph_width) + (i_x * spacing_x), ((i_y + 1) * glyph_height) + (i_y * spacing_y))
                glyph = glyph_sheet.crop(box)
                name_index = (i_y * grid_width) + i_x

                if glyph_names:
                    name = glyph_names[name_index]
                else:
                    name = 'g{}'.format(name_index)

                glyph_images.update({name: glyph})

                if len(glyph_images) == number_glyphs:
                    return cls(glyph_images=glyph_images, **kwargs)

    # ~~ GLYPH WORK ON INIT ~~

    def load_glyphs(self, directory):
        glyphs = {}
        for filename in os.listdir(directory):
            # TODO extend to support other file types
            if filename.endswith(".png"):
                glyph_ = Glyph.from_file(filename)
                glyphs.update({glyph_.name: glyph_})
        return glyphs

    def calculate_trees(self):
        tree_sets = []

        for stack_size in range(1, self.glyph_depth + 1):
            glyph_set = list(self.combine_glyphs(stack_size).values())
            glyph_data = [list(glyph.fingerprint.getdata()) for glyph in glyph_set]
            tree = cKDTree(glyph_data)
            centroid = np.mean(glyph_data, axis=0)
            mean_square_from_centroid = np.mean(((glyph_data - centroid) ** 2).sum(axis=1))

            tree_sets.append(tree_set(glyph_set=glyph_set, tree=tree, centroid=centroid,
                                      mean_square_from_centroid=mean_square_from_centroid,
                                      stack_size=stack_size))

        return tree_sets

    def combine_glyphs(self, depth):
        glyph_combinations = itertools.combinations(iter(self.glyphs.values()), depth)
        output = {}
        for combination in glyph_combinations:
            new = functools.reduce(operator.add, combination)
            output.update({new.name: new})
        return output

    def average_glyph_values(self):
        average_values = []
        for tree_set in self.tree_sets:
            for glyph in tree_set.glyph_set:
                vals = list(glyph.fingerprint.getdata())
                average_value = sum(vals) / len(vals)
                average_values.append(average_value)
        return average_values

    def glyph_value_extrema(self):
        return min(self.average_values), max(self.average_values)

    # ~~ IMAGE PROCESSING ~~

    def chunk(self, image_data, target_width):
        chunks = []
        height = len(image_data) // (target_width * self.sample_y * self.sample_x)
        for y in range(height):
            rows = range(self.sample_y * y, self.sample_y * (y + 1))
            for x in range(target_width):
                columns = range(self.sample_x * x, self.sample_x * (x + 1))
                chunk = [image_data[column + row * target_width * self.sample_x] for row in rows for column in columns]
                chunks.append(chunk)
        return chunks

    @staticmethod
    def fit_to_aspect(image, aspect_ratio):
        current_aspect = image.width / image.height
        if current_aspect < aspect_ratio:  # Image too tall
            perfect_height = image.width / aspect_ratio
            edge = (image.height - perfect_height) / 2
            image = image.crop((0, edge, image.width, perfect_height + edge))
        else:  # Image too wide
            perfect_width = image.height * aspect_ratio
            edge = (image.width - perfect_width) / 2
            image = image.crop((edge, 0, perfect_width + edge, image.height))

        return image

    def preprocess(self, image, target_size=(60, 60), resize_mode=Image.LANCZOS, clip_limit=0.02,
                   use_clahe=True, rescale_intensity=True):

        target_width, target_height = target_size
        desired_aspect = (self.glyph_width * target_width) / (self.glyph_height * target_height)
        image = self.fit_to_aspect(image, desired_aspect)

        sized_picture = image.resize((target_width * self.sample_x, target_height * self.sample_y), resize_mode)
        sized_picture = sized_picture.convert("L")

        if use_clahe or rescale_intensity:
            sized_picture = np.asarray(sized_picture)

            if min(target_size) > 1 and use_clahe:
                sized_picture = exposure.equalize_adapthist(sized_picture, clip_limit=clip_limit)

            # TODO Something is screwy with the current contrast methods, need to investigate
            self.value_extrema = (150, 250)

            if rescale_intensity:
                sized_picture = exposure.rescale_intensity(sized_picture, out_range=self.value_extrema)

            sized_picture = Image.fromarray(sized_picture.astype("uint8"))

        return sized_picture

    # ~~ OUTPUT CREATION ~~

    # Could be split in 2, if wanted to. perform the histogram once, then apply on func call
    def equalize_glyphs(self, image, mask=None):
        h = image.histogram(mask)
        target_indices = []
        for i in range(256):
            count = self.average_values.count(i)
            if count:
                target_indices.extend([i] * count)

        histo = [_f for _f in h if _f]
        step = (functools.reduce(operator.add, histo) - histo[-1]) // len(target_indices)

        lut = []
        n = step // 2
        for i in range(256):
            position = min(n // step, len(target_indices) - 1)
            lut.append(target_indices[position])
            n += h[i]

        return image.point(lut)

    def find_closest_glyph(self, target, cutoff=0.3):

        # TODO: may want to easy out if we're at glyph depth of 1?

        neighbours = []
        for tree_set in self.tree_sets:
            tree = tree_set.tree
            distance, index = tree.query(target)
            neighbours.append((tree_set, distance, index))

        best_tree_set, best_distance, best_index = min(neighbours, key=lambda x: x[1])

        max_stack_size = best_tree_set.stack_size

        for tree_set, distance, index in neighbours[:max_stack_size-1]:

            distance_diff = distance - best_distance
            stack_size_diff = best_tree_set.stack_size - tree_set.stack_size
            rmd = self.root_mean_distance(target, tree_set)

            if (distance_diff / (stack_size_diff * rmd)) < cutoff:
                return tree_set.glyph_set[index], distance

        return best_tree_set.glyph_set[best_index], best_distance

    def compose_calculation(self, result, target_width, target_height):
        calculation = Image.new("L", (target_width * self.glyph_width, target_height * self.glyph_height))
        for i, glyph_ in enumerate(result):
            x = self.glyph_width * (i % target_width)
            y = self.glyph_height * (i // target_width)
            calculation.paste(glyph_.fingerprint_display, (x, y, x + self.glyph_width, y + self.glyph_height))
        return calculation

    def compose_output(self, result, target_width, target_height):
        output = Image.new("L", (target_width * self.glyph_width, target_height * self.glyph_height))
        for i, glyph_ in enumerate(result):
            x = self.glyph_width * (i % target_width)
            y = self.glyph_height * (i // target_width)
            output.paste(glyph_.image, (x, y, x + self.glyph_width, y + self.glyph_height))
        return output

    def instructions(self, result_glyphs, spacer, target_width, target_height, trailing_spacer=False):
        instructions = []

        row_counter_length = str(len(str(target_height)))

        lines = [result_glyphs[i * target_width: (i + 1) * target_width] for i in range(target_height)]
        for line_number, line in enumerate(lines):
            line_columns = []
            last_column = []
            for character in line:
                components = character.components
                elements = max(len(last_column), len(components))
                column = [spacer] * elements
                indexes = list(range(0, elements))
                deferred = []
                # Match up position of characters that were also in last composite glyph
                for glyph_atom in components:
                    if glyph_atom in last_column:
                        index = last_column.index(glyph_atom)
                        column[index] = glyph_atom
                        indexes.remove(index)
                    else:
                        deferred.append(glyph_atom)
                # Remianing components fill in the remianing spaces
                for glyph_atom, index in zip(deferred, indexes):
                    column[index] = glyph_atom

                last_column = column
                line_columns.append(column)

            rows = list(itertools.zip_longest(*line_columns, fillvalue=spacer))
            row_letters = self.iter_all_strings()

            for row_number, row in enumerate(rows):
                glyph_groups = itertools.groupby(row, key=lambda glyph: glyph.name)
                glyph_groups = [(key, list(group)) for key, group in glyph_groups]

                if not trailing_spacer:
                    # remove last group if it contains the spacer character
                    if glyph_groups[-1][1][0] == spacer:
                        glyph_groups = glyph_groups[:-1]

                groups = [str(len(list(group))) + key for key, group in glyph_groups]

                if len(rows) > 1:
                    row_letter = next(row_letters)
                else:
                    row_letter = ' '

                out_line = '{number:0' + row_counter_length + '}{letter}| {inst}'
                instructions.append(out_line.format(number=line_number, letter=row_letter, inst=' '.join(groups)))

        return instructions

    @staticmethod
    def root_mean_distance(point, tree_set):
        centroid = tree_set.centroid
        mean_square_from_centroid = tree_set.mean_square_from_centroid
        square_distance_from_centroid = ((np.array(point) - centroid) ** 2).sum()
        return np.sqrt(square_distance_from_centroid + mean_square_from_centroid)

    @staticmethod
    def iter_all_strings():
        size = 1
        while True:
            for s in itertools.product(string.ascii_lowercase, repeat=size):
                yield "".join(s)
            size += 1

    def image_to_text(self, image, target_size=(60, 60), cutoff=0.3, resize_mode=Image.LANCZOS, clip_limit=0.02, use_clahe=True, rescale_intensity=True, instruction_spacer=None):

        preprocessed_image = self.preprocess(image, target_size=target_size, resize_mode=resize_mode,
                                             clip_limit=clip_limit, use_clahe=use_clahe, rescale_intensity=rescale_intensity)

        calc, output, inst_str = self._convert(preprocessed_image, target_size, cutoff, instruction_spacer)
        return calc, output, inst_str

    def _convert(self, image, target_size=(60, 60), cutoff=0.3, instruction_spacer=None):

        target_width, target_height = target_size

        image_data = list(image.getdata())
        target_parts = self.chunk(image_data, target_width=target_width)

        result = []
        for section in target_parts:
            glyph, distance = self.find_closest_glyph(section, cutoff=cutoff)
            result.append(glyph)

        calculation = self.compose_calculation(result, target_width=target_width, target_height=target_height)
        output = self.compose_output(result, target_width=target_width, target_height=target_height)

        if not instruction_spacer:
            blank = Image.new("L", (25, 48), 'white')
            instruction_spacer = Glyph(name='sp', image=blank)

        instruction_string = '\n'.join(self.instructions(result, spacer=instruction_spacer,
                                                         target_width=target_width, target_height=target_height))

        return calculation, output, instruction_string
