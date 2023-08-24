import numpy as np

from pydicom.pixel_data_handlers.util import apply_voi_lut, apply_modality_lut

from skimage.morphology import remove_small_objects
from skimage.measure import label
from skimage.measure import regionprops


def reset_mask_stack(current_labels):

    new_labels = {}
    for k, v in current_labels.items():
        new_labels[k] = None
    return new_labels


def adjust_image(ds, window_center, window_width):

    arr = ds.pixel_array.copy()
    ds.WindowCenter = window_center
    ds.WindowWidth = window_width
    voi_out = apply_modality_lut(arr, ds)
    voi_out = apply_voi_lut(voi_out, ds)  # apply VOI LUT or windowing operation
    out = voi_out
    bitdepth = ds.BitsAllocated
    if ds.PhotometricInterpretation == 'MONOCHROME1':  # ranges from bright to dark with ascending pixel values
        out = out.max() - out
    out = out.reshape((ds.Rows, ds.Columns))
    out = out.astype(np.float64)
    out += -out.min()  # NOTE: converting to uint16 with negative values ruins the image
    if out.max() > 0:
        out /= out.max()
    out *= pow(2, bitdepth) - 1
    out = out.astype(np.uint16)
    return out


def remove_outliers(mask_stack):

    mask_stack = mask_stack > 0
    labels = label(mask_stack)
    regions = regionprops(labels)
    if len(regions) > 0:
        min_size = sorted(regions, key=lambda r:r.area)[-1].area - 1
    else:
        min_size = 1
    mask_stack = remove_small_objects(mask_stack, min_size=min_size, connectivity=3)
    if mask_stack.dtype == bool:
        mask_stack = mask_stack.astype("uint8")
        mask_stack *= 255
    return mask_stack
