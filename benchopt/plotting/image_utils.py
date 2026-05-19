"""Helpers for converting array-API compatible objects to base64 data URIs."""
import base64
import io

import numpy as np


def _is_array(obj):
    """Return True for numpy arrays and any array-API compatible object."""
    return hasattr(obj, '__array__') or hasattr(obj, '__array_namespace__')


def _array_to_png_src(arr):
    """Convert a 2-D array (any array-API type) to a base64 PNG data URI."""
    from PIL import Image
    arr = np.asarray(arr)
    arr = np.clip(arr, 0, 1)
    mode = 'L' if arr.ndim == 2 else 'RGB'
    img = Image.fromarray((arr * 255).astype(np.uint8), mode=mode)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return (
        'data:image/png;base64,' + base64.b64encode(buf.read()).decode('ascii')
    )


def _arrays_to_gif_src(frames, fps=5):
    """Convert a list of 2-D arrays (any array-API type) to a base64 GIF."""
    from PIL import Image
    imgs = []
    for f in frames:
        arr = np.asarray(f)
        arr = np.clip(arr, 0, 1)
        arr = (arr * 255).astype(np.uint8)
        mode = 'L' if arr.ndim == 2 else 'RGB'
        imgs.append(Image.fromarray(arr, mode=mode))
    buf = io.BytesIO()
    imgs[0].save(
        buf, format='GIF', save_all=True, append_images=imgs[1:],
        duration=int(1000 / fps), loop=0,
    )
    buf.seek(0)
    return (
        'data:image/gif;base64,' + base64.b64encode(buf.read()).decode('ascii')
    )
