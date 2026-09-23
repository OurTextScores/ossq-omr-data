import io
from operator import contains
import colorsys

import numpy as np
import cv2
from PIL import Image

from music21 import converter
import converter21

from IPython.display import display, Image as IPImage, HTML
import ipywidgets as widgets
from IPython.display import clear_output

from modules.lmxe.lmxe.LMXEFile import LMXEFile
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.utils import split_tokens_by_key_token

from .bbox import load_bboxs
from .musescore import run_musescore_converter
from .image import crop_white_space, make_background_white

converter21.register()


def hsl_to_rgb(h, s, l):
  r, g, b = colorsys.hls_to_rgb(h/360, l/100, s/100)
  return int(r*255), int(g*255), int(b*255)


class Preview:
  def __init__(self, data_list, index=0):
    self.data_list = data_list
    self.current_index = index
    
    # Create widgets
    self.prev_button = widgets.Button(description="Previous")
    self.next_button = widgets.Button(description="Next")
    self.counter = widgets.Label(value="")
    
    # Set up button callbacks
    self.prev_button.on_click(self.on_prev_clicked)
    self.next_button.on_click(self.on_next_clicked)
    
    # Create layout containers
    self.image_output = widgets.Output()
    self.symbolic = widgets.Textarea(
      value='',
      layout=widgets.Layout(width='700px', height='800px'),
      disabled=True
    )
  
  
  def _init_main_layout(self):
    # arrange / modify the layout as needed
    raise NotImplementedError("Subclasses should implement this method")
  
  
  def update_display(self):
    raise NotImplementedError("Subclasses should implement this method")
  
  
  def on_prev_clicked(self, b):
    """Handle previous button click"""
    if self.current_index > 0:
      self.current_index -= 1
      self.update_display()
  
  
  def on_next_clicked(self, b):
    """Handle next button click"""
    if self.current_index < len(self.data_list) - 1:
      self.current_index += 1
      self.update_display()
  
  
  def show(self):
    """Display the interface"""
    display(self.main_layout)



class ImageComparePreview(Preview):
  def __init__(self, data_list, index=0):
    # data_list: [(image_path, image_path), ...]
    super().__init__(data_list, index)
    
    self._init_main_layout()
    
    # Display initial content
    self.update_display()
  
  
  def _init_main_layout(self):
    self.image_output1 = widgets.Output()
    self.image_output2 = widgets.Output()
    
    self.path_label1 = widgets.Label(value="")
    self.path_label2 = widgets.Label(value="")
    
    button_box = widgets.HBox([self.prev_button, self.counter, self.next_button])
    top_box = widgets.VBox([self.path_label1, self.path_label2])
    
    left_side = widgets.VBox([self.image_output1])
    right_side = widgets.VBox([ self.image_output2])
    content_box = widgets.HBox([left_side, right_side])
    
    self.main_layout = widgets.VBox([
      button_box,
      top_box,
      content_box
    ])
  
  
  def update_display(self):
    """Update the displayed image and text"""
    if not self.data_list:
      return
    
    self.counter.value = f"({self.current_index + 1}/{len(self.data_list)})"  
    
    i_p1, i_p2 = self.data_list[self.current_index]
    
    # Update path label
    self.path_label1.value = f"Left: {i_p1}"
    self.path_label2.value = f"Right: {i_p2}"
    
    # Update image
    with self.image_output1:
      clear_output(wait=True)
      display(IPImage(filename=i_p1, width=600))
    
    with self.image_output2:
      clear_output(wait=True)
      display(IPImage(filename=i_p2, width=600))
    
    
    # Update button states
    self.prev_button.disabled = (self.current_index == 0)
    self.next_button.disabled = (self.current_index == len(self.data_list) - 1)
  
  
  def on_prev_clicked(self, b):
    """Handle previous button click"""
    if self.current_index > 0:
      self.current_index -= 1
      self.update_display()
  
  
  def on_next_clicked(self, b):
    """Handle next button click"""
    if self.current_index < len(self.data_list) - 1:
      self.current_index += 1
      self.update_display()
  
  
  def show(self):
    """Display the interface"""
    display(self.main_layout)




class LMXEPreview(Preview):
  def __init__(self, data_list, index=0):
    # data_list: [(image_path, lmxe_path), ...]
    super().__init__(data_list, index)
    
    self._init_main_layout()
    
    # Display initial content
    self.update_display()
  
  
  def _init_main_layout(self):
    self.path_label = widgets.Label(value="")
    self.measure_counter = widgets.Label(value="")
    
    button_box = widgets.HBox([self.prev_button, self.counter, self.next_button])
    top_box = widgets.VBox([self.path_label, self.measure_counter])
    
    left_side = widgets.VBox([self.image_output])
    right_side = widgets.VBox([self.symbolic])
    content_box = widgets.HBox([left_side, right_side])
    
    self.main_layout = widgets.VBox([
      button_box,
      top_box,
      content_box
    ])
  
  
  def update_display(self):
    """Update the displayed image and text"""
    if not self.data_list:
      return
    
    self.counter.value = f"({self.current_index + 1}/{len(self.data_list)})"  
    
    i_p, l_p = self.data_list[self.current_index]
    
    # Update path label
    self.path_label.value = f"Image: {i_p}\nLMXE: {l_p}"
    
    # Update image
    with self.image_output:
      clear_output(wait=True)
      display(IPImage(filename=i_p, width=600))
    
    lmxe = LMXEFile.load(l_p, include_metadata=False)
    self.measure_counter.value = f"Num Measures: {len(lmxe.measures)}"
    
    lmxe_str = [
      'measure\n' +
      '\n'.join([
        f'    part:{i+1} ' + ' '.join(p)
        for i, p in enumerate(split_tokens_by_key_token(m.split()[1:], 'part:', compare_fn=contains))
      ])
      for m in lmxe.measures
    ]
    
    self.symbolic.value = '\n\n'.join(lmxe_str)
    
    # Update button states
    self.prev_button.disabled = (self.current_index == 0)
    self.next_button.disabled = (self.current_index == len(self.data_list) - 1)
  
  
  def on_prev_clicked(self, b):
    """Handle previous button click"""
    if self.current_index > 0:
      self.current_index -= 1
      self.update_display()
  
  
  def on_next_clicked(self, b):
    """Handle next button click"""
    if self.current_index < len(self.data_list) - 1:
      self.current_index += 1
      self.update_display()
  
  
  def show(self):
    """Display the interface"""
    display(self.main_layout)



class StaffBboxPreview(Preview):
  def __init__(self, data_list, index=0):
    # data_list: [(image_path, bbox_path), ...]
    super().__init__(data_list, index)
    
    self._init_main_layout()
    
    # Display initial content
    self.update_display()
  
  
  def _init_main_layout(self):
    self.path_label = widgets.Label(value="")
    self.measure_counter = widgets.Label(value="")
    
    button_box = widgets.HBox([self.prev_button, self.counter, self.next_button])
    top_box = widgets.VBox([self.path_label, self.measure_counter])
    
    left_side = widgets.VBox([self.image_output])
    right_side = widgets.VBox([self.symbolic])
    content_box = widgets.HBox([left_side, right_side])
    
    self.main_layout = widgets.VBox([
      button_box,
      top_box,
      content_box
    ])
  
  
  def update_display(self):
    """Update the displayed image and text"""
    if not self.data_list:
      return
    
    colors = [
      (255, 0, 0),  # red
      (0, 0, 255),  # blue
      (0, 255, 0),  # green
    ]
    
    self.counter.value = f"({self.current_index + 1}/{len(self.data_list)})"  
    
    i_p, b_p = self.data_list[self.current_index]
    
    # Update path label
    self.path_label.value = f"Image: {i_p}"
    
    img = cv2.imread(i_p, cv2.IMREAD_UNCHANGED)
    bboxs = load_bboxs(
      b_p, 
      with_class=True, 
      confidence_threshold=0.7,
      merge_threshold=0.7,
    )
    for i, (cl, x1, y1, x2, y2) in enumerate(bboxs):
      color = hsl_to_rgb((i*137) % 360, 100, 50)  # unique color for each bbox
      cv2.rectangle(img, (x1, y1), (x2, y2), color=color, thickness=2)
    
    buffer = io.BytesIO()
    pil_img = Image.fromarray(img)
    pil_img.save(buffer, format='PNG')
    
    # Update image
    with self.image_output:
      clear_output(wait=True)
      display(IPImage(data=buffer.getvalue(), width=600))
    
    self.symbolic.value = '\n'.join([ ' '.join([ str(x) for x in b]) for b in bboxs])
    
    # Update button states
    self.prev_button.disabled = (self.current_index == 0)
    self.next_button.disabled = (self.current_index == len(self.data_list) - 1)
  
  
  def on_prev_clicked(self, b):
    """Handle previous button click"""
    if self.current_index > 0:
      self.current_index -= 1
      self.update_display()
  
  
  def on_next_clicked(self, b):
    """Handle next button click"""
    if self.current_index < len(self.data_list) - 1:
      self.current_index += 1
      self.update_display()
  
  
  def show(self):
    """Display the interface"""
    display(self.main_layout)


class ABCInferencePreview(Preview):
  def __init__(self, data_list, index=0):
    # data_list: [(image_path, gt_path, pred_path), ...]
    super().__init__(data_list, index)
    
    self._init_main_layout()
    
    # Display initial content
    self.update_display()
  
  
  def _init_main_layout(self):
    self.path_label = widgets.Label(value="")
    self.gt_path_label = widgets.Label(value="")
    self.omr_ned = widgets.Label(value="")
    
    button_box = widgets.HBox([self.prev_button, self.counter, self.next_button])
    top_box = widgets.VBox([self.path_label, self.gt_path_label, self.omr_ned])
    
    left_side = widgets.VBox([self.image_output, self.symbolic])
    self.image_pred = widgets.Output()
    self.symbolic_pred = widgets.Textarea(
      value='',
      layout=widgets.Layout(width='700px', height='800px'),
      disabled=True
    )
    right_side = widgets.VBox([self.image_pred, self.symbolic_pred])
    content_box = widgets.HBox([left_side, right_side])
    
    self.main_layout = widgets.VBox([
      button_box,
      top_box,
      content_box
    ])
  
  
  def update_display(self):
    """Update the displayed image and text"""
    if not self.data_list:
      return
    
    self.counter.value = f"({self.current_index + 1}/{len(self.data_list)})"  
    
    i_p, g_p, p_p, omr_ned = self.data_list[self.current_index]
    
    # Update path label
    self.path_label.value = f"Image: {i_p}"
    
    # Update GT path label
    self.gt_path_label.value = f"GT Path: {g_p}"
    
    # Update OMR-NED label
    self.omr_ned.value = f"OMR-NED: {omr_ned:.4f}"
    
    # Update image
    with self.image_output:
      clear_output(wait=True)
      display(IPImage(filename=i_p, width=600))
    
    sym = g_p.read_text()
    self.symbolic.value = sym
    
    try:
      pred_score = converter.parse(
        p_p.with_name(p_p.stem + '_with_time.abc'),
        forceSource=True,
        acceptSyntaxErrors=True
      )
      pred_score.write('musicxml', p_p.with_suffix('.musicxml'))
      musicxml = MusicXMLFile.load_musicxml(p_p.with_suffix('.musicxml'))
      musicxml.strip_musicxml()
      musicxml.remove_music21_defaults()
      musicxml.write(p_p.with_suffix('.musicxml'))
      
      mscx_path = p_p.with_suffix('.mscx')
      run_musescore_converter(
        p_p.with_suffix('.musicxml'),
        mscx_path,
        './single-system.mss',
        ('--force', ''),
      )
    
      # render mscx to png using MuseScore
      run_musescore_converter(
        mscx_path,
        p_p.with_suffix('.png'),
        ('--force', ''),
      )
    
      # select second image,
      # first image is empty image w/ empty VBox
      pred_img_paths = p_p.parent.glob(f"{p_p.stem}-*.png")
      pred_img_paths = sorted(pred_img_paths)
      pred_img_path = pred_img_paths[-1]
      rendered_image = cv2.imread(
        pred_img_path,
        cv2.IMREAD_UNCHANGED
      )
      
      rendered_image = make_background_white(rendered_image)
      rendered_image = crop_white_space(rendered_image, ratio=0.001)
      rendered_image = cv2.resize(rendered_image, (int(rendered_image.shape[1] * 256 / rendered_image.shape[0]), 256), interpolation=cv2.INTER_AREA)
      cv2.imwrite(p_p.with_suffix('.png'), rendered_image)
    
      for i_p in pred_img_paths:
        i_p.unlink() # clean up intermediate images
    
    except Exception as e:
      print(e)
      rendered_image = np.zeros((100, 100, 3), dtype=np.uint8)
      cv2.imwrite(p_p.with_suffix('.png'), rendered_image)
    
    with self.image_pred:
      clear_output(wait=True)
      display(IPImage(filename=p_p.with_suffix('.png'), width=600))
    
    pred = p_p.read_text()
    self.symbolic_pred.value = pred
    
    # Update button states
    self.prev_button.disabled = (self.current_index == 0)
    self.next_button.disabled = (self.current_index == len(self.data_list) - 1)
  
  
  def on_prev_clicked(self, b):
    """Handle previous button click"""
    if self.current_index > 0:
      self.current_index -= 1
      self.update_display()
  
  
  def on_next_clicked(self, b):
    """Handle next button click"""
    if self.current_index < len(self.data_list) - 1:
      self.current_index += 1
      self.update_display()
  
  
  def show(self):
    """Display the interface"""
    display(self.main_layout)