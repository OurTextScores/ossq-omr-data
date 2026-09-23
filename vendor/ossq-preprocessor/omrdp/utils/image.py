import operator
import cv2
import numpy as np


def search_letter_box_by_axis(img, nrange, axis, ratio, margin, default=None, compare_fn=operator.gt):
  line_size = img.shape[1-axis]
  nrange = list(nrange)
  
  for i in nrange:
    slice_tup = tuple( i if d == axis else slice(None) for d in range(2) )
    line = img[slice_tup]
    
    # default: (line.sum() / line_size) > ratio
    if compare_fn(line.sum() / line_size, ratio):
      return i + margin
  
  return default if default is not None else nrange[0]


def crop_white_space(img, margin=10, ratio=0.5, compare_fn=operator.gt):
  h, w = img.shape[:2]

  i_g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
  _, ith = cv2.threshold(i_g, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
  
  inrm = 1 - (ith / 255)

  # scan through y axis until meet some non-black things
  yaxis = range(h)
  yst = search_letter_box_by_axis(inrm, yaxis, 0, ratio, -margin, compare_fn=compare_fn)
  yed = search_letter_box_by_axis(inrm, reversed(yaxis), 0, ratio, margin, compare_fn=compare_fn)
  yst = max(0, yst)
  yed = min(h, yed)
  
  # scan through x axis until meet some non-black things
  xaxis = range(w)
  xst = search_letter_box_by_axis(inrm, xaxis, 1, ratio, -margin, compare_fn=compare_fn)
  xed = search_letter_box_by_axis(inrm, reversed(xaxis), 1, ratio, margin, compare_fn=compare_fn)
  xst = max(0, xst)
  xed = min(w, xed)
  
  return img[yst:yed, xst:xed]


def make_background_white(img):
  """Composite BGRA onto white, including antialiased edges; preserve BGR input."""
  if img is None:
    raise ValueError("cannot composite an unreadable image")
  if img.ndim != 3 or img.shape[2] != 4:
    return img
  alpha = img[:, :, 3:4].astype(np.float32) / 255.0
  return np.rint(img[:, :, :3] * alpha + 255.0 * (1.0 - alpha)).astype(np.uint8)