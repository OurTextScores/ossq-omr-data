import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import strictyaml as syaml
import requests

from tqdm.auto import tqdm

from ultralytics import YOLO

from omrdp.utils import get_ts
from omrdp.utils.bbox import zip_bboxs_confs, save_bboxs


YOLO_INFO_VERSION = '0.1.0'
@dataclass
class YOLOInfo:
  version:str=field(init=False, default=YOLO_INFO_VERSION)
  data_id:str
  image_type:str # scanned or synthetic or etc
  system:dict=field(default_factory=lambda: {
    'model': "",
    'confidence_threshold': "",
    'merge_threshold': "",
    'exceptions': "", # list of systems that need special handling e.g. wrongly cropped systems
    'ignores': "", # list of systems to ignore e.g. excess bbox w/o contents
  })
  staff_height:dict=field(default_factory=lambda: {
    'model': "",
    'target_height': "",
  })
  staff_bbox:dict=field(default_factory=lambda: {
    'model': "",
    'confidence_threshold': "",
    'merge_threshold': "",
    'exceptions': "", # list of staffs that need special handling e.g. wrongly cropped staffs
    'ignores': "", # list of staffs to ignore e.g. excess bbox w/o contents
  })
  
  
  @staticmethod
  def load(yaml_path:Path):
    data = syaml.load(yaml_path.read_text()).data
    if 'version' not in data:
      raise Exception(f'Invalid YOLOInfo YAML: version not found in {yaml_path}')
    if data['version'] != YOLO_INFO_VERSION:
      raise Exception(f'YOLOInfo version mismatch: expected {YOLO_INFO_VERSION}, got {data["version"]} in {yaml_path}')
    
    del data['version']
    
    yolo_info = YOLOInfo(**data)
    return yolo_info
  
  
  def write(self, yaml_path:Path):
    yaml_path.write_text(syaml.as_document(asdict(self)).as_yaml())



YOLO_MODELS_URLS = {
  'ls-yolo-system-v2.0.0.pt': 'https://github.com/MALerLab/ls-yolo/releases/download/system-v2/ls-yolo-system-v2.0.0.pt',
  'ls-yolo-system-v3.0.0.pt': 'https://github.com/MALerLab/ls-yolo/releases/download/system-v3/ls-yolo-system-v3.0.0.pt',
  'ls-yolo-staff-height-v2.0.0.pt': 'https://github.com/MALerLab/ls-yolo/releases/download/staff-height-v2/ls-yolo-staff-height-v2.0.0.pt',
  'ls-yolo-staff-bbox-v1.0.1.pt': 'https://github.com/MALerLab/ls-yolo/releases/download/staff-bbox-v1/ls-yolo-staff-bbox-v1.0.1.pt'
}


def download_yolo_model_checkpoint(model_name:str, checkpoint_path:Path):
  r = requests.get( YOLO_MODELS_URLS[model_name], allow_redirects=True )

  if r.status_code != 200:
    raise Exception(f'Failed to download YOLO model checkpoint: {model_name} from {YOLO_MODELS_URLS[model_name]}')
  
  checkpoint_path.parent.mkdir(exist_ok=True)
  with open(checkpoint_path, 'wb') as f:
    f.write(r.content)


def load_yolo_model(checkpoint_name, checkpoint_dir:Path) -> YOLO:
  checkpoint_path = checkpoint_dir / checkpoint_name

  if not checkpoint_path.exists():
    download_yolo_model_checkpoint(checkpoint_name, checkpoint_path)
  
  yolo_model = YOLO( checkpoint_path )

  return yolo_model


def inference_by_batch(image_fns:list[Path], yolo:YOLO, batch_size:int=64, custom_process=None, device:str='cpu'):
  """
  :param image_fns: list of image file paths
  :param yolo: instance of YOLO model
  :param batch_size: batch size for YOLO inference, default is 64
  """
  num_batches = math.ceil(len(image_fns)/batch_size)

  outputs = []

  for cur_batch_idx in tqdm(range(num_batches), leave=False, desc="YOLO Inf", dynamic_ncols=True):
    batch = image_fns[cur_batch_idx*batch_size:(cur_batch_idx+1)*batch_size]
    
    if custom_process:
      batch_paths = batch
      batch = [ custom_process(b) for b in batch ]
    
    
    batch_output = yolo(batch, device=device, verbose=False)
    
    if custom_process:
      for bo, bp in zip(batch_output, batch_paths):
        bo.path = str(bp)

    outputs += batch_output
  
  return outputs


def process_yolo_system_output(output):
  bboxs = output.boxes.xyxy

  # skip if no bbox
  if len(bboxs) < 1:
    return False

  bboxs = zip_bboxs_confs(output)

  image_path = Path(output.path)
  yolo_bbox_path = image_path.with_name( image_path.stem + '_yolo_bboxs.txt' )

  save_bboxs(bboxs, yolo_bbox_path)

  return yolo_bbox_path


def detect_systems_by_batch(image_fns:list[Path], yolo:YOLO, batch_size:int=64, device:str='cpu'):
  """
  :param image_fns: list of image file paths
  :param yolo: instance of YOLO model
  :param batch_size: batch size for YOLO inference, default is 64
  """
  
  outputs = inference_by_batch(
    image_fns, 
    yolo=yolo, 
    batch_size=batch_size,
    device=device
  )

  # move model back to cpu
  if device != 'cpu':
    yolo.to('cpu')
  
  yolo_bbox_paths = []
  
  for output in outputs:
    yolo_bbox_path = process_yolo_system_output(output)
    if yolo_bbox_path:
      yolo_bbox_paths.append(yolo_bbox_path)
  

  return yolo_bbox_paths


def process_yolo_staff_height_output(output):
  bboxs = output.boxes.xyxy

  # skip if no bbox
  if len(bboxs) < 1:
    return False

  bboxs = zip_bboxs_confs(output)

  image_path = Path(output.path)
  staff_height_path = image_path.with_name( image_path.stem + '_staff_heights.txt' )

  save_bboxs(bboxs, staff_height_path)

  average_staff_height = sum([ y2 - y1 for (_, y1, _, y2, _) in bboxs ])
  average_staff_height /= len(bboxs)

  return average_staff_height


def detect_staff_heights_by_batch(crop_image_fns:list[Path], yolo:YOLO, batch_size:int=64, device:str='cpu'):
  """
  :param crop_image_fns: list of cropped image file paths
  :param yolo: instance of YOLO model
  :param batch_size: batch size for YOLO inference, default is 64
  """
  def crop_left_half(image_fn:Path):
    img = cv2.imread(image_fn, cv2.IMREAD_UNCHANGED)
    return img[:, :img.shape[1]//2]  # left half

  outputs = inference_by_batch(
    crop_image_fns, 
    yolo=yolo, 
    batch_size=batch_size, 
    custom_process=crop_left_half,
    device=device
  )
  
  staff_heights = []
  
  for output in outputs:
    average_staff_height = process_yolo_staff_height_output(output)
    staff_heights.append(average_staff_height)
  
  return staff_heights


def resize_systems(crop_image_fns:list[Path], staff_heights:list[float], target_height:int=18, out_dirname:str='crop_resized'):
  """
  :param crop_image_fns: list of cropped image file paths
  :param staff_heights: list of average staff heights corresponding to the cropped images
  :param target_height: target height for resizing, default is 18
  """
  for crop_image_fn, staff_height in zip(crop_image_fns, staff_heights):
    if not staff_height:
      # need logging
      continue

    img = cv2.imread(crop_image_fn, cv2.IMREAD_UNCHANGED)
    ratio = target_height / staff_height
    r_w = int(img.shape[1] * ratio)
    r_h = int(img.shape[0] * ratio)

    i_r = cv2.resize(img, (r_w, r_h), interpolation=cv2.INTER_AREA)

    i_r_p = crop_image_fn.parent.parent / out_dirname
    i_r_p.mkdir(exist_ok=True, parents=False)

    i_r_p = i_r_p / crop_image_fn.name

    if cv2.imwrite(i_r_p, i_r) is False:
      pass
      # need logging