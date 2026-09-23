from collections import defaultdict

def load_bboxs(
  file_path, 
  *, 
  confidence_threshold=0.0,
  merge_threshold=None, 
  with_class=False, 
  without_postprocess=False
):
  bboxs = []
  
  with open(file_path, 'r') as f:
    lines = f.readlines()
    
    for line in lines:
      # line format:
      # with_class=False: (lx, ly, rx, ry, conf)
      # with_class=True: (cls, lx, ly, rx, ry, conf)
      bbox = [ p for p in line.strip().split(' ') ] 
      if with_class:
        bbox = [int(float(bbox[0]))] + [ int(p) for p in bbox[1:-1] ] + [ float(bbox[-1]) ]
      else:
        bbox = [ int(p) for p in bbox[:-1] ] + [ float(bbox[-1]) ]
      bboxs.append( bbox )
  
  if without_postprocess:
    return bboxs
  
  bboxs = [ b[:-1] for b in bboxs if b[-1] >= confidence_threshold ]
  
  # merge overlapping bboxs
  if merge_threshold is not None:
    if with_class:
      bboxs = merge_yolo_bboxs_classwise(bboxs, min_ratio=merge_threshold)
    else:
      bboxs = merge_yolo_bboxs(bboxs, min_ratio=merge_threshold)
  
  # sort y coordinate first
  if with_class:
    bboxs = sorted( bboxs, key=lambda x: (x[2], x[1]) )
  else:
    bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) ) 
  
  return bboxs


def save_bboxs(bboxs, file_path):
  with open(file_path, 'w') as f:
    for bbox in bboxs:
      f.write(f'{" ".join(map(str, bbox))}\n')


def zip_bboxs_confs(output):
  bboxs = output.boxes.xyxy.int().tolist()
  confs = output.boxes.conf.tolist()

  bboxs = [ (*coords, conf) for coords, conf in zip(bboxs, confs) ]
  # sort by y, x
  bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) )

  return bboxs


def get_interpolated(value, src_min, src_max, tgt_min, tgt_max):
  delta = (tgt_max - tgt_min) / (src_max - src_min)
  return (value - src_min) * delta + tgt_min


def get_box_width(box):
  lx, ly, rx, ry = box
  return rx - lx


def get_box_height(box):
  lx, ly, rx, ry = box
  return ry - ly


def get_box_area(box):
  lx, ly, rx, ry = box
  width = get_box_width(box)
  height = get_box_height(box)

  return width * height


def get_bbox_center(box):
  tl_x, tl_y, br_x, br_y, *_ = box
  return tl_x + (br_x - tl_x) // 2, tl_y + (br_y - tl_y) // 2


def is_approximate_bbox(src, target, axis=1, max_dist=5):
  s_center = get_bbox_center(src)
  t_center = get_bbox_center(target)

  return abs(s_center[axis] - t_center[axis]) < max_dist


def get_approximates_bbox(source_box, boxs, target_idx, axis=1, max_dist=5):
  approxs = []
  for idx, box in enumerate(boxs):
    if idx > target_idx:
      if is_approximate_bbox(source_box, box, axis=axis, max_dist=max_dist):
        approxs.append((box, idx))
  
  return approxs


def group_bboxs_by_pos(bboxs, axis=1, max_dist=5):
  # axis x: 0, y: 1
  bboxs = sorted(bboxs, key=lambda b: b[axis])

  bbox_groups = []
  index = 0

  while True:
    if index > len(bboxs) - 1:
      break

    curr = bboxs[index]

    # overlapping box indexs
    approxs = get_approximates_bbox(
      curr,
      bboxs,
      index,
      axis=axis,
      max_dist=max_dist
    )

    if len(approxs) > 0:
      approx_boxs = [tup[0] for tup in approxs]
      approx_boxs = [curr] + approx_boxs

      bbox_groups.append(approx_boxs)

      # remove approxs
      approx_indices = [tup[1] for tup in approxs]

      approx_indices.sort(reverse=True)
      for approx_idx in approx_indices:
        assert approx_idx < len(bboxs), f'index out of range: {approx_idx} / {len(bboxs) - 1}'
        del bboxs[approx_idx]

    else:
      bbox_groups.append([curr])

    index += 1

  return bbox_groups


def calc_iou(source, target):
  # IOU: intersection over union
  # tl: top-left / br: bottom-right
  s_tl_x, s_tl_y, s_br_x, s_br_y = source
  t_tl_x, t_tl_y, t_br_x, t_br_y = target

  i_tl_x = max(s_tl_x, t_tl_x)
  i_tl_y = max(s_tl_y, t_tl_y)
  i_br_x = min(s_br_x, t_br_x)
  i_br_y = min(s_br_y, t_br_y)

  i_w = max(0, i_br_x - i_tl_x)
  i_h = max(0, i_br_y - i_tl_y)
  i_area = i_w * i_h

  if not i_w or not i_h:
    return 0

  s_area = (s_br_x - s_tl_x) * (s_br_y - s_tl_y)
  t_area = (t_br_x - t_tl_x) * (t_br_y - t_tl_y)
  u_area = s_area + t_area - i_area

  if not u_area:
    return 0

  iou = i_area / u_area

  return iou


def is_inside_margin_area(point, size, margin):
  return point <= margin  # or point >= size - margin


def get_group_bbox(group):
  lx = min([b[0] for b in group])
  ly = min([b[1] for b in group])
  rx = max([b[2] for b in group])
  ry = max([b[3] for b in group])

  return (lx, ly, rx, ry)


def get_overlaps_match_bbox(bboxs, soruce_bbox, soruce_idx, min_ratio=0.2):
  overlaps = []
  for idx, bbox in enumerate(bboxs):
    if (idx > soruce_idx and (iou := calc_iou(soruce_bbox, bbox)) > min_ratio):
      overlaps.append((idx, iou))

  return overlaps


def merge_match_bboxs(bboxs, min_ratio=0.2):
  bboxs_merged = []
  index = 0

  while True:
    if index > len(bboxs) - 1:
      break

    curr = bboxs[index]

    # overlapping box indexs
    overlaps = get_overlaps_match_bbox(bboxs, curr, index, min_ratio)

    if len(overlaps) > 0:
      # merge ovelapping boxes
      curr = get_group_bbox([bboxs[tup[0]] for tup in overlaps] + [curr])

      # remove overlaps
      overlap_indices = [tup[0] for tup in overlaps]
      overlap_indices.sort(reverse=True)
      for overlap_idx in overlap_indices:
        assert overlap_idx < len(bboxs), f'index out of range: {overlap_idx} / {len(bboxs) - 1}'
        del bboxs[overlap_idx]

    bboxs_merged.append(curr)

    index += 1

  return bboxs_merged


def merge_overlap_bboxs(sources, targets):
  # filter overlapping bboxs
  merged_sources = [[lx, ly, rx, ry] for lx, ly, rx, ry in sources]

  for i, s_b in enumerate(sources):
    overlaps = []

    for j, t_b in enumerate(targets):
      iou = calc_iou(s_b, t_b)

      if iou > 0:
        overlaps.append(j)
        merged_sources[i] = get_group_bbox([s_b, t_b])

    if len(overlaps) > 0:
      overlaps = sorted(overlaps, reverse=True)
      for j in overlaps:
        assert j < len(targets), f'index out of range: {j} / {len(targets) - 1}'
        del targets[j]

  return merged_sources, targets


def filter_parallel_bboxs(sources, targets, margin=0):
  merged_sources = []

  for i, s_b in enumerate(sources):
    s_tl_x, s_tl_y, s_br_x, s_br_y = s_b
    indices = []

    for j, t_b in enumerate(targets):
      t_tl_x, t_tl_y, t_br_x, t_br_y = t_b

      if (calc_iou((0, s_tl_y, t_br_x, s_br_y), t_b) > 0.5 and t_tl_x > s_br_x):
        s_b = get_group_bbox([s_b, t_b])
        indices.append(j)

      elif (calc_iou((0, s_tl_y, t_br_x, s_br_y), t_b) > 0.3 and (t_br_x < s_tl_x or t_tl_x > s_br_x)):
        indices.append(j)

    if len(indices) > 0:
      indices = sorted(indices, reverse=True)
      for j in indices:
        del targets[j]

    if s_b[2] != s_br_x:
      s_b = list(s_b)
      s_b[2] += margin
      s_b = tuple(s_b)

    merged_sources.append(s_b)

  return merged_sources, targets


def group_approx_bboxs(sources, targets, max_dist=5, x_tol=5):
  left_overs = []
  bbox_groups = []

  for i, s_b in enumerate(sources):
    group = [s_b]
    indices = []

    for j, t_b in enumerate(targets):
      s_tl_x, s_tl_y, s_br_x, s_br_y = s_b
      t_tl_x, t_tl_y, t_br_x, t_br_y = t_b
      t_h = t_br_y - t_tl_y

      dist = None

      if t_tl_y < s_tl_y:
        dist = abs(s_tl_y - t_tl_y - t_h)

      elif t_br_y > s_br_y:
        dist = abs(t_tl_y - s_br_y - t_h)

      if dist and dist <= max_dist:
        if t_tl_x < (s_tl_x + x_tol) or t_br_x > (s_br_x):
          left_overs.append(t_b)

        else:
          group.append(t_b)

        indices.append(j)

    bbox_groups.append(s_b)

    if len(indices) > 0:
      indices = sorted(indices, reverse=True)
      for j in indices:
        del targets[j]

  return bbox_groups, left_overs


def get_group_bbox_attr(group, calc_fn, num_sample=0, tol=10):
  group_values = sorted([calc_fn(b) for b in group], reverse=True)
  group_value = group_values[0]

  if len(group_values) > 1:
    filtered_values = [
      x for x in group_values[1:] if abs(group_values[0] - x) > tol
    ]
    if len(filtered_values) > len(group) / 2:
      group_value = (
        filtered_values[0] 
        if num_sample < 1 
        else sum(filtered_values[:num_sample]) / len(filtered_values[:num_sample])
      )

  return group_value


def merge_approx_bboxs(sources, targets, max_dist=5, x_tol=5, max_merge=20):
  left_overs = []
  merged_bboxs = []

  for i, s_b in enumerate(sources):
    indices = []
    merge_cnt = 0

    for j, t_b in enumerate(targets):
      s_tl_x, s_tl_y, s_br_x, s_br_y = s_b
      t_tl_x, t_tl_y, t_br_x, t_br_y = t_b

      dist = max_dist * 2
      is_top = False

      if t_tl_y <= s_tl_y:
        dist = s_tl_y - t_br_y
        is_top = True

      elif t_br_y >= s_br_y:
        dist = t_tl_y - s_br_y

      is_approx = dist <= max_dist
      is_out_s_x_range = t_tl_x < (s_tl_x - x_tol) or t_br_x > s_br_x

      if is_approx:
        if is_out_s_x_range:
          left_overs.append(t_b)

        else:
          if (is_top and merge_cnt < max_merge) or not is_top:
            s_b = get_group_bbox([s_b, t_b])
            merge_cnt += is_top

        indices.append(j)

    merged_bboxs.append(s_b)

    if len(indices) > 0:
      indices = sorted(indices, reverse=True)
      for j in indices:
        del targets[j]

  return merged_bboxs, left_overs


def calc_intersection_over_min(source, target):
  """Intersection area / area of the smaller box."""
  s_tl_x, s_tl_y, s_br_x, s_br_y = source
  t_tl_x, t_tl_y, t_br_x, t_br_y = target

  i_w = max(0, min(s_br_x, t_br_x) - max(s_tl_x, t_tl_x))
  i_h = max(0, min(s_br_y, t_br_y) - max(s_tl_y, t_tl_y))
  i_area = i_w * i_h

  if not i_area:
    return 0

  s_area = (s_br_x - s_tl_x) * (s_br_y - s_tl_y)
  t_area = (t_br_x - t_tl_x) * (t_br_y - t_tl_y)
  min_area = min(s_area, t_area)

  return i_area / min_area if min_area else 0


def _get_overlaps_min_ratio(bboxs, source, source_idx, min_ratio):
  overlaps = []
  for idx, bbox in enumerate(bboxs):
    if idx > source_idx and calc_intersection_over_min(source, bbox) > min_ratio:
      overlaps.append(idx)
  return overlaps


def _merge_pass(bboxs, min_ratio):
  merged = []
  index = 0
  while index <= len(bboxs) - 1:
    curr = bboxs[index]
    overlaps = _get_overlaps_min_ratio(bboxs, curr, index, min_ratio)
    if overlaps:
      curr = get_group_bbox([bboxs[i] for i in overlaps] + [curr])
      for i in sorted(overlaps, reverse=True):
        del bboxs[i]
    merged.append(curr)
    index += 1
  return merged


def merge_yolo_bboxs_classwise(bboxs, min_ratio=0.2, n_iter=100):
  """Merge overlapping same-class bboxes.

  Args:
    bboxs: list of (cls, lx, ly, rx, ry)
    min_ratio: merge when intersection / area(smaller box) > min_ratio

  Returns:
    list of (cls, lx, ly, rx, ry), sorted by (y, x)
  """

  by_class = defaultdict(list)
  for cls, *coords in bboxs:
    by_class[cls].append(coords)

  result = []
  for cls, coords_list in by_class.items():
    if len(coords_list) < 2:
      result.extend([cls] + c for c in coords_list)
      continue

    prev = 0
    for _ in range(n_iter):
      coords_list = sorted(coords_list, key=get_box_area, reverse=True)
      coords_list = _merge_pass(coords_list, min_ratio)
      if len(coords_list) == prev:
        break
      prev = len(coords_list)

    result.extend([cls] + list(c) for c in coords_list)

  return result


def merge_yolo_bboxs(bboxs, min_ratio=0.2, n_iter=100):
  if len(bboxs) < 2:
    return bboxs
  
  prev = 0
  for _ in range(n_iter):
    bboxs = sorted( bboxs, key=lambda x: get_box_area(x), reverse=True )
    bboxs = _merge_pass(bboxs, min_ratio=min_ratio)
    
    if len(bboxs) == prev:
      break
    
    prev = len(bboxs)
  
  return bboxs