from typo_graphics import Typograph
import numpy as np
from PIL import Image
from skimage import exposure
from contextlib import suppress
import os
from progressbar import ProgressBar
import warnings
from math import ceil, floor


image_paths = ['Output/dog.png', 'Output/Copyright free/waterfall.png',
               'Output/Copyright free/aus_shep_crop.png',
               'Input/Mikko2.jpg', 'Input/Possible fish.jpg', 'Output/Copyright free/flower2.png',
               'docs/build/html/_images/SR100.png']

image_directories = []  # ['Glyphs/']

# This is a LOT of images, use with caution
# range can contain anything [0, 100)
# image_directories.extend(['E:/Users/Richard/Documents/Programming/Python/Python 3/'
#                           'PyCharmProjects/PeterIMDB/wiki/{i:02}'.format(i=i) for i in range(1)])

for directory in image_directories:
    for filename in os.listdir(directory):
        with suppress(IOError):  # skips over any files that Image cannot open
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                path = os.path.join(directory, filename)
                image = Image.open(path)
                if min(image.size) > 5:
                    image_paths.append(path)


max_size = (60, 60)
max_width, max_height = max_size
clip_limit = 0.02
glyph_depth = 3
background_glyph = None
verbose = False

typograph = Typograph(glyph_depth=glyph_depth)

glyph_width = typograph.glyph_width
glyph_height = typograph.glyph_height
sample_width, sample_height = typograph.samples


def pre_rescale(image, clip_limit):
    greyscale_image = image.convert("L")
    image_array = np.asarray(greyscale_image)

    # TODO: may want to investigate how they perform without the CLAHE step
    image_array = exposure.equalize_adapthist(image_array, clip_limit=clip_limit)
    return image_array


def post_rescale(image_array):
    greyscale_image = Image.fromarray(image_array.astype("uint8"))
    return greyscale_image


def preprocess(image_array):
    """
    current _preprocess
    """
    value_extrema = typograph.value_extrema
    rescaled_array = exposure.rescale_intensity(image_array, out_range=value_extrema)

    return rescaled_array


def force_150_220(image_array):
    """
    current _preprocess
    """
    value_extrema = (150, 220)
    rescaled_array = exposure.rescale_intensity(image_array, out_range=value_extrema)

    return rescaled_array


def in_range_change(image_array):
    """
    In range being set to 0, 255, rather than image extrema
    """
    value_extrema = typograph.value_extrema
    rescaled_array = exposure.rescale_intensity(image_array, in_range='dtype', out_range=value_extrema)
    return rescaled_array


def expand_out_range(image_array):
    """
    Expanding the out range
    """
    value_extrema = typograph.value_extrema

    mean_value = sum(value_extrema)/2
    min_val, max_val = value_extrema
    value_range = max_val - min_val

    new_max = min([255, int(mean_value + 0.75 * value_range)])
    new_min = max([0, int(mean_value - 0.75 * value_range)])

    rescaled_array = exposure.rescale_intensity(image_array, out_range=(new_min, new_max))

    return rescaled_array


def expand_out_range_1(image_array):
    """
    Expanding the out range
    """
    value_extrema = typograph.value_extrema

    mean_value = sum(value_extrema)/2
    min_val, max_val = value_extrema
    value_range = max_val - min_val

    new_max = min([255, int(mean_value + 1 * value_range)])
    new_min = max([0, int(mean_value - 1 * value_range)])

    rescaled_array = exposure.rescale_intensity(image_array, out_range=(new_min, new_max))

    return rescaled_array


def expand_out_range_1_5(image_array):
    """
    Expanding the out range
    """
    value_extrema = typograph.value_extrema

    mean_value = sum(value_extrema)/2
    min_val, max_val = value_extrema
    value_range = max_val - min_val

    new_max = min([255, int(mean_value + 1.5 * value_range)])
    new_min = max([0, int(mean_value - 1.5 * value_range)])

    rescaled_array = exposure.rescale_intensity(image_array, out_range=(new_min, new_max))

    return rescaled_array


def expand_out_range_2(image_array):
    """
    Expanding the out range
    """
    value_extrema = typograph.value_extrema

    mean_value = sum(value_extrema)/2
    min_val, max_val = value_extrema
    value_range = max_val - min_val

    new_max = min([255, int(mean_value + 2 * value_range)])
    new_min = max([0, int(mean_value - 2 * value_range)])

    rescaled_array = exposure.rescale_intensity(image_array, out_range=(new_min, new_max))

    return rescaled_array


def condense_out_range(image_array):
    """
    Condense the out range
    """
    value_extrema = typograph.value_extrema

    mean_value = sum(value_extrema)/2
    min_val, max_val = value_extrema
    value_range = max_val - min_val

    new_max = min([255, int(mean_value + 0.25 * value_range)])
    new_min = max([0, int(mean_value - 0.25 * value_range)])

    rescaled_array = exposure.rescale_intensity(image_array, out_range=(new_min, new_max))

    return rescaled_array


def standard_deviation_out_range(image_array):
    """
    Use mean ± standard deviation, rather than extrema
    """
    mean = np.mean(typograph.average_values)
    standard_dev = np.std(typograph.average_values)
    rescaled_array = exposure.rescale_intensity(image_array, out_range=(mean - standard_dev, mean + standard_dev))
    return rescaled_array


def two_standard_deviation_out_range(image_array):
    """
    Use mean ± 2 standard deviation, rather than extrema
    """
    mean = np.mean(typograph.average_values)
    standard_dev = 2 * np.std(typograph.average_values)
    rescaled_array = exposure.rescale_intensity(image_array, out_range=(mean - standard_dev, mean + standard_dev))
    return rescaled_array


def three_standard_deviation_out_range(image_array):
    """
    Use mean ± 3 standard deviation, rather than extrema
    """
    mean = np.mean(typograph.average_values)
    standard_dev = 3 * np.std(typograph.average_values)
    rescaled_array = exposure.rescale_intensity(image_array, out_range=(mean - standard_dev, mean + standard_dev))
    return rescaled_array


def no_rescale(image_array):
    """Don't do anything to it"""
    image_array *= 255
    return image_array


# approaches = [preprocess, force_150_220, in_range_change, expand_out_range, condense_out_range, standard_deviation_out_range,
#               two_standard_deviation_out_range, three_standard_deviation_out_range, no_rescale, expand_out_range_1, expand_out_range_1_5, expand_out_range_2]

approaches = [force_150_220, preprocess, expand_out_range, expand_out_range_1, expand_out_range_1_5, expand_out_range_2]

total_scores = {approach.__name__: 0 for approach in approaches}

out_images = Image.new("L", (glyph_width * max_width * len(approaches),
                             glyph_height * max_height * len(image_paths)), "white")

with ProgressBar(max_value=len(image_paths)) as bar:
    for image_index, path in enumerate(image_paths):
        image = Image.open(path)

        for approach_index, approach in enumerate(approaches):

            def wrapped_approach(image, target_size, clip_limit, enhance_contrast, rescale_intensity, background_glyph):
                if background_glyph is not None:
                    image_bands = image.getbands()
                    if "A" in image_bands:
                        alpha_channel = image.split()[image_bands.index("A")]
                    else:
                        alpha_channel = Image.new("L", image.size, "white")
                greyscale_image = image.convert("L")
                if enhance_contrast or rescale_intensity:
                    image_array = np.asarray(greyscale_image)

                    if min(target_size) > 1 and enhance_contrast:
                        image_array = exposure.equalize_adapthist(image_array, clip_limit=clip_limit)

                    if rescale_intensity:
                        image_array = approach(image_array)

                    image_array = approach(image_array)

                    greyscale_image = Image.fromarray(image_array.astype("uint8"))

                if background_glyph is not None:
                    greyscale_image.putalpha(alpha_channel)
                return greyscale_image

            typograph._preprocess = wrapped_approach

            typed_art, distance = typograph.image_to_text(image, max_size=max_size, rescale_intensity=True, fit_mode='Scale')

            total_scores[approach.__name__] += distance

            center_x = glyph_width * max_width * (approach_index + .5)
            center_y = glyph_height * max_height * (image_index + .5)
            left = floor(typed_art.output.width/2.0)
            right = ceil(typed_art.output.width/2.0)
            top = floor(typed_art.output.height/2.0)
            bottom = ceil(typed_art.output.height/2.0)

            out_images.paste(typed_art.output, (int(center_x - left),
                                                int(center_y - top),
                                                int(center_x + right),
                                                int(center_y + bottom)))

            if verbose:
                print("{method} method gave total distance of {dist:.0f} "
                      "for image {image}".format(method=approach.__name__, dist=distance, image=image_index))
        bar.update(image_index)
    if verbose:
        print('-----')

print('=============')
rankings = sorted(list(total_scores.items()), key=lambda x: x[1])
print('~~~Total scores~~~')
for rank, (method, score) in enumerate(rankings):
    print('#{rank}: {method} with a total distance of {score:.0f}'.format(rank=rank+1, method=method, score=score))

out_images.show()

out_images.save('E:/Users/Richard/Desktop/comparison_out.png')
