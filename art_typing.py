from glyph import glyph
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


class art_typing():
    # tunable params
    # clip_limit for adapthist
    # cutoff for matching
    # samples
    # output size
    # glyphs
    # --> directory
    # --> full sheet
    # image resize method

    def __init__(self, samples=(3,3), glyph_depth=2):
        self.samples = samples
        self.sample_x, self.sample_y = samples

        self.tree_sets = self.calculate_trees(glyphs=glyphs, glyph_depth=glyph_depth)


    # We will have some option:
    # call for JUST output image
    # call for JUST instructions
    # call for both (should this be encapsulated in something, or just a tuple?)

    # ~~ GLYPH WORK ON INIT ~~

    def load_glyphs(self, directory):
        glyphs = {}
        for filename in os.listdir(directory):
            # TODO extend to support other filetypes
            if filename.endswith(".png"):
                glyph_ = glyph.from_file(filename)
                glyphs.update({glyph_.name: glyph_})
        return glyphs

    def calculate_trees(self, glyphs, glyph_depth):
        tree_sets = []

        for stack_size in range(1, glyph_depth + 1):
            glyph_set = list(self.combine_glyphs(glyphs, stack_size).values())
            glyph_data = [list(glyph.fingerprint.getdata()) for glyph in glyph_set]
            tree = cKDTree(glyph_data)
            centroid = np.mean(glyph_data, axis=0)
            mean_square_from_centroid = np.mean(((glyph_data - centroid) ** 2).sum(axis=1))

            tree_sets.append(tree_set(glyph_set=glyph_set, tree=tree, centroid=centroid,
                                      mean_square_from_centroid=mean_square_from_centroid,
                                      stack_size=stack_size))

        return tree_sets

    def combine_glyphs(self, glyphs, depth):
        glyph_combinations = itertools.combinations(iter(glyphs.values()), depth)
        output = {}
        for combination in glyph_combinations:
            new = functools.reduce(operator.add, combination)
            output.update({new.name: new})
        return output

    def average_glyph_value(self, tree_sets):
        average_values = []
        for tree_set in tree_sets:
            for glyph in tree_set.glyph_set:
                vals = list(glyph.fingerprint.getdata())
                average_value = sum(vals) / len(vals)
                average_values.append(average_value)
        return average_values

    # ~~ IMAGE PROCESSING ~~

    def chunk(self, list_, width, chunk_width, chunk_height):
        chunks = []
        height = len(list_) // (width * chunk_height * chunk_width)
        for y in range(height):
            rows = range(chunk_height * y, chunk_height * (y + 1))
            for x in range(width):
                columns = range(chunk_width * x, chunk_width * (x + 1))
                chunk = [list_[column + row * width * chunk_width] for row in rows for column in columns]
                chunks.append(chunk)
        return chunks

    def fit_to_aspect(self, image, aspect_ratio):
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

    def equalize_glyphs(self, image, average_vals, mask=None):
        h = image.histogram(mask)
        target_indices = []
        for i in range(256):
            count = average_vals.count(i)
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

    # ~~ OUTPUT CREATION ~~

    def find_closest_glyph(self, target, tree_sets, cutoff=0.3):
        neighbours = []
        for tree_set in tree_sets:
            tree = tree_set.tree
            distance, index = tree.query(target)
            neighbours.append((tree_set, distance, index,))

        best_tree_set, best_distance, best_index = min(neighbours, key=lambda x: x[1])

        max_stack_size = best_tree_set.stack_size

        for tree_set, distance, index in neighbours[:max_stack_size]:

            distance_diff = distance - best_distance
            stack_size_diff = best_tree_set.stack_size - tree_set.stack_size
            rmd = self.root_mean_distance(target, tree_set)

            if (distance_diff / stack_size_diff * rmd) < cutoff:
                return tree_set.glyph_set[index]

        return best_tree_set.glyph_set[best_index]

    def compose_calculation(self, result, target_width, target_height):
        calculation = Image.new("L", (target_width * 25, target_height * 48))
        for i, glyph_ in enumerate(result):
            w = 25
            h = 48
            x = w * (i % target_width)
            y = h * (i // target_width)
            calculation.paste(glyph_.fingerdisplay, (x, y, x + w, y + h))
        return calculation

    def compose_output(self, result, target_width, target_height):
        output = Image.new("L", (target_width * 25, target_height * 48))
        for i, glyph_ in enumerate(result):
            w = 25
            h = 48
            x = w * (i % target_width)
            y = h * (i // target_width)
            output.paste(glyph_.image, (x, y, x + w, y + h))
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

    # Both of these are sort of generic, perhaps pushable into a utils.py

    def root_mean_distance(self, point, tree_set):
        centroid = tree_set.centroid
        mean_square_from_centroid = tree_set.mean_square_from_centroid
        square_distance_from_centroid = ((np.array(point) - centroid) ** 2).sum()
        return np.sqrt(square_distance_from_centroid + mean_square_from_centroid)

    def iter_all_strings(self):
        size = 1
        while True:
            for s in itertools.product(string.ascii_lowercase, repeat=size):
                yield "".join(s)
            size += 1

    def image_to_text(self, image, target_size=None, resize_mode=Image.LANCZOS, clip_limit=0.02):

        target_width, target_height = target_size

        desired_aspect = (25 * target_width) / (48 * target_height)

        image = self.fit_to_aspect(image, desired_aspect)

        sized_picture = image.resize((target_width * self.sample_x, target_height * self.sample_y), resize_mode)
        sized_picture = sized_picture.convert("L")

        sized_picture = exposure.equalize_adapthist(np.asarray(sized_picture), clip_limit=clip_limit)

        average_vals = self.average_glyph_value(self.tree_sets)
        lightest_value = max(average_vals)
        darkest_value = min(average_vals)

        sized_picture = exposure.rescale_intensity(sized_picture, out_range=(darkest_value, lightest_value))
        if exposure.is_low_contrast(sized_picture):
            print('LOW CONTRAST WARNING')
        sized_picture = Image.fromarray((sized_picture).astype('uint8'))
        target_parts = self.chunk(list(sized_picture.getdata()), width=target_width, chunk_width=self.sample_x, chunk_height=self.sample_y)

        result = []
        for section in target_parts:
            result.append(self.find_closest_glyph(section, self.tree_sets, cutoff=0))

        calculation = self.compose_calculation(result)
        output = self.compose_output(result)

        blank = Image.new("L", (25, 48), 'white')
        space = glyph(name='sp', image=blank)

        instruction_string = '\n'.join(self.instructions(result, space, target_width, target_height))

        return (calculation, output, instruction_string)

