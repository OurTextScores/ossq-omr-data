import warnings
from typing import Union
from types import SimpleNamespace
from pathlib import Path
from operator import itemgetter
from concurrent.futures import ProcessPoolExecutor, as_completed

import csv

from tqdm.auto import tqdm

import music21 as m21
import converter21

import musicdiff as md
from musicdiff import DetailLevel, EvaluationMetrics


PathLike = Union[str,Path]

TO_SANITIZED_HEADER_NAME_BASE = {
  'wrong clef OMR-ED': 'clef', 
  'wrong keysig OMR-ED': 'keysig', 
  'wrong timesig OMR-ED': 'timesig', 

  'wrong note OMR-ED': 'note', 
  'wrong graceness OMR-ED': 'graceness', 
  'wrong accidental OMR-ED': 'accidental', 

  'wrong tuplet OMR-ED': 'tuplet', 
  'wrong dot OMR-ED': 'dot', 

  'wrong flag/beam OMR-ED': 'flag/beam', 
  'wrong fingered tremolo OMR-ED': 'fingered tremolo', 
  'wrong ornament OMR-ED': 'ornament', 
  'wrong articulation OMR-ED': 'articulation', 

  'wrong note stem OMR-ED': 'note stem', 
  'wrong note head OMR-ED': 'note head',

  'wrong tie OMR-ED': 'tie', 
  'wrong slur OMR-ED': 'slur', 

  'entire measure insert/delete OMR-ED': 'entire measure', 
  'entire staff insert/delete OMR-ED': 'entire staff', 

  'bad kern syntax OMR-ED': 'bad kern syntax', 

  'wrong other object OMR-ED': 'other object', 
}

TO_SANITIZED_HEADER_NAME_EXTRA = {
  'wrong ottava OMR-ED': 'ottava', 
  'wrong multi-staff arpeggio OMR-ED': 'multi-staff arpeggio', 

  'wrong system break OMR-ED': 'system break', 
  'wrong page break OMR-ED': 'page break', 
  'wrong barline OMR-ED': 'barline', 
  'wrong ending OMR-ED': 'ending', 

  'wrong dynamic OMR-ED': 'dynamic', 
  'wrong crescendo OMR-ED': 'crescendo', 
  'wrong diminuendo OMR-ED': 'diminuendo', 
  'wrong direction OMR-ED': 'direction', 
  'wrong chord symbol OMR-ED': 'chord symbol', 

  'wrong staff group OMR-ED': 'staff group', 
  'wrong staff group name/abbrev OMR-ED': 'staff group name/abbrev', 
  'wrong staff group brace OMR-ED': 'staff group brace', 
  'wrong staff group barline OMR-ED': 'staff group barline', 
  
  'wrong tempo OMR-ED': 'tempo', 
  'wrong metadata OMR-ED': 'metadata', 
  'wrong staff info OMR-ED': 'staff info',  
  'wrong lyric OMR-ED': 'lyric', 
}

TO_SANITIZED_HEADER_NAME = {
  **TO_SANITIZED_HEADER_NAME_BASE, 
  **TO_SANITIZED_HEADER_NAME_EXTRA
}


def _compute_metrics(
  gt_path,
  pred_path,
  ii_path,
  max_length,
  detail
):
  # Suppress all warnings from music21
  warnings.filterwarnings('ignore', module='music21.*')
  
  try:
    metrics:EvaluationMetrics|None = md._diff_omr_ned_metrics(
      predpath=pred_path,
      gtpath=gt_path,
      detail=detail
    )
  except Exception as _:
    metrics = None

  if metrics is None: # make dummy metrics obj
    metrics = EvaluationMetrics(
      Path(gt_path),
      Path(pred_path),
      -1,
      -1,
      -1,
      dict(),
      -1.
    )
    metrics.success = False
  else:
    metrics.success = True
  
  metrics.image_path = Path(ii_path)
  metrics.max_length = max_length
  
  return metrics


# Tweaked version of musicdiff.diff_ml_training
def calc_omr_ned(
  image_paths: list[PathLike],
  max_length: int,
  prediction_paths: list[PathLike],
  ground_truth_paths: list[PathLike],
  output_file_path:PathLike,
  detail:DetailLevel|int=DetailLevel.Default,
  multi_process:bool=True,
  max_workers:int=8,
) -> SimpleNamespace:
  converter21.register()

  task_list = []
  for gt_p, pred_p, ii_p in zip(ground_truth_paths, prediction_paths, image_paths):
    task_list.append((
      gt_p,
      pred_p,
      ii_p,
      max_length,
      detail,
    ))
  
  metrics_list:list[EvaluationMetrics] = [None] * len(task_list)
  
  if multi_process:
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
      future_to_idx = {
        executor.submit(_compute_metrics, *args): idx
        for idx, args in enumerate(task_list)
      }
      for future in tqdm(
        as_completed(future_to_idx),
        total=len(task_list),
        desc=f"Calculating OMR-NED metrics with {max_workers} workers",
        dynamic_ncols=True,
      ):
        idx = future_to_idx[future]
        metrics_list[idx] = future.result()
  else:
    for idx, args in enumerate(tqdm(
      task_list,
      desc="Calculating OMR-NED metrics",
      dynamic_ncols=True,
    )):
      metrics_list[idx] = _compute_metrics(*args)
  
  
  # Save to output Path
  if output_file_path.suffix != '.tsv':
    print(f"Warning: changing output file suffix to .tsv from {output_file_path.suffix}")
    output_file_path = output_file_path.with_suffix('.tsv')
  
  # default headers
  header = ['success', 'image_path', 'gt_path', 'pred_path', 'max_length', 'omr_ned', 'gt_numsyms', 'pred_numsyms', 'omr_edit_distance'] 
  header_detail = list(TO_SANITIZED_HEADER_NAME_BASE.values()) # detailed headers

  macro_omr_ned = 0
  micro_omr_ned = 0
  total_gt_numsyms = 0
  total_pred_numsyms = 0
  total_num_success = 0

  with open(output_file_path, 'w') as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(header+header_detail)

    for item in tqdm(metrics_list, desc="Writing OMR-NED metrics", leave=False, dynamic_ncols=True):
      row = []
      for k in header:
        value = getattr(item, k, None)

        if isinstance(value, (int, float)) and value < 0:
          value = None

        if isinstance(value, Path):
          value = str(value)
        
        if k == 'success':
          value = int(value)

        row.append(value)
        
      if item.success:
        macro_omr_ned += item.omr_ned
        micro_omr_ned += item.omr_edit_distance
        total_gt_numsyms += item.gt_numsyms
        total_pred_numsyms += item.pred_numsyms
        total_num_success += 1

      for k in TO_SANITIZED_HEADER_NAME_BASE.keys():
        value = item.edit_distances_dict.get(k, None)
        row.append(value)

      writer.writerow(row)
  
  total_edit_distance = micro_omr_ned
  
  total_numsyms = total_gt_numsyms + total_pred_numsyms
  
  macro_omr_ned = macro_omr_ned / total_num_success if total_num_success > 0 else 1.
  micro_omr_ned = micro_omr_ned / total_numsyms if total_numsyms > 0 else 1.

  return SimpleNamespace(
    output_file_path=output_file_path,
    macro_average_omr_ned=macro_omr_ned,
    micro_average_omr_ned=micro_omr_ned,
    total_gt_numsyms=total_gt_numsyms,
    total_pred_numsyms=total_pred_numsyms,
    total_numsyms=total_numsyms,
    total_edit_distance=total_edit_distance,
    total_num_success=total_num_success
  )