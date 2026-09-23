from pathlib import Path
from typing import Union
from collections import defaultdict
from fractions import Fraction

import xml.etree.ElementTree as ET
import zipfile


# (type_name, duration_in_quarter_notes) — ordered longest to shortest
_NOTE_TYPE_DURATIONS: list[tuple[str, Fraction]] = [
  ('long',    Fraction(16, 1)),
  ('breve',   Fraction(8,  1)),
  ('whole',   Fraction(4,  1)),
  ('half',    Fraction(2,  1)),
  ('quarter', Fraction(1,  1)),
  ('eighth',  Fraction(1,  2)),
  ('16th',    Fraction(1,  4)),
  ('32nd',    Fraction(1,  8)),
  ('64th',    Fraction(1,  16)),
  ('128th',   Fraction(1,  32)),
  ('256th',   Fraction(1,  64)),
  ('512th',   Fraction(1,  128)),
  ('1024th',  Fraction(1,  256)),
]


def _duration_to_type(duration_quarters: Fraction) -> tuple[str | None, int]:
  """Map a duration (in quarter notes) to a MusicXML note type and dot count.

  Supports up to 2 augmentation dots.
  Returns (type_str, num_dots), or (None, 0) if no standard type matches.
  """
  for note_type, base_dur in _NOTE_TYPE_DURATIONS:
    for dots in range(3):  # 0, 1, 2 dots
      # dot_multiplier: 1, 3/2, 7/4 for dots = 0, 1, 2
      dot_multiplier = Fraction(2 ** (dots + 1) - 1, 2 ** dots)
      if duration_quarters == base_dur * dot_multiplier:
        return note_type, dots
  return None, 0


class MxlFile:
  """Loads and lets you manipulate a MusicXML file"""

  def __init__(self, tree: ET.ElementTree):
    self.tree = tree

    # all MuseScore exported MusicXML files should be partwise organized
    # https://www.w3.org/2021/06/musicxml40/tutorial/structure-of-musicxml-files/
    assert tree.getroot().tag == "score-partwise"
  
  
  @staticmethod
  def load_mxl(path: str) -> "MxlFile":
    """Loads MusicXML from the compressed MXL file"""
    with zipfile.ZipFile(path, "r") as archive:
      for record in archive.infolist():
        if record.filename.startswith("META-INF"):
          continue
        if record.filename.endswith(".xml"):
          inner_file_name = record.filename
          break
      with archive.open(inner_file_name) as file:
        tree = ET.parse(file)
        return MxlFile(tree)
  
  
  def resolve_piano_part_id(self) -> str:
    """Resolves the ID of the piano part, e.g. 'P2'"""
    part_list = self.tree.getroot().find("part-list")
    
    for part in part_list.findall("score-part"):
      if part.find("score-instrument/instrument-name").text in [
        "Piano", "Grand Piano", "Acoustic Grand Piano",
        "Harpsichord", "Pianoforte", "Piano (2)"
      ]:
        return part.attrib["id"]
      if part.find("part-name").text in [
        "Pianoforte"
      ]:
        return part.attrib["id"]
    
    raise Exception(
      "No piano part found:\n" \
        + str(ET.tostring(part_list), "utf-8")
    )
  
  
  def get_piano_part(self) -> ET.Element:
    """Returns the <part> element of the piano, containing measures."""
    part_id = self.resolve_piano_part_id()

    parts = [
      part for part in self.tree.findall("part")
      if part.attrib["id"] == part_id
    ]
    assert len(parts) == 1
    part = parts[0]

    return part
  
  
  def resolve_string_part_ids(self) -> list[str]:
    """Resolves the list of IDs of the strings parts, e.g. [P1, P2, P3, P4]"""
    part_list = self.tree.getroot().find("part-list")
    
    string_part_ids = []
    
    for part in part_list.findall("score-part"):
      if (
        part.find("score-instrument/instrument-name").text in { "Violin", "Viola", "Cello", "Violoncello" } or
        part.find("part-name").text in { "Violin 1", "Violin 2", "Viola", "Cello", "Violoncello" }
      ):
        string_part_ids.append(part.attrib["id"])
    
    assert len(string_part_ids) > 0, "No string parts found."
    
    if len(string_part_ids) > 4:
      print("Warning: More than 4 string parts found. Using the first 4.")
      string_part_ids = string_part_ids[:4]
    
    return string_part_ids
  
  
  def get_string_quartet_parts(self) -> list[ET.Element]:
    """Returns the <part> elements of the string quartet, containing measures."""
    string_part_ids = self.resolve_string_part_ids()
    
    parts = [
      part for part in self.tree.findall("part")
      if part.attrib["id"] in string_part_ids
    ]
    
    assert len(parts) == 4
    return parts



class MusicXMLFile:
  """Represents a MusicXML file and provides methods for manipulation."""

  def __init__(self, tree:ET.ElementTree):
    self.tree = tree
    self.parts = defaultdict(list)
    self.type = ''

    # all MuseScore exported MusicXML files should be partwise organized
    # https://www.w3.org/2021/06/musicxml40/tutorial/structure-of-musicxml-files/
    assert tree.getroot().tag == "score-partwise"
  
  
  @staticmethod
  def load_mxl(path:Union[str|Path])->"MusicXMLFile":
    """Loads MusicXML from the compressed MXL file"""
    if isinstance(path, str):
      path = Path(path)

    assert path.suffix == ".mxl", "Only compressed MusicXML file expected"
    assert path.exists(), "File not found"

    with zipfile.ZipFile(path, "r") as archive:
      for record in archive.infolist():
        if record.filename.startswith("META-INF"):
          continue
        if record.filename.endswith(".xml"):
          inner_file_name = record.filename
          break
      with archive.open(inner_file_name) as f:
        tree = ET.parse(f)
        return MusicXMLFile(tree)

  
  @staticmethod
  def load_musicxml(path:Union[str|Path]) -> 'MusicXMLFile':
    if isinstance(path, str):
      path = Path(path)

    assert path.suffix == ".musicxml" or path.suffix == '.xml', "Only (un-compressed) MusicXML file expected"
    assert path.exists(), "MusicXML file not found"

    with open(path, 'r', encoding='utf-8') as f:
      xml_str = f.read()
    
    xml_tree = ET.ElementTree(ET.fromstring(xml_str))
    
    return MusicXMLFile(xml_tree)
  
  
  def __str__(self):
    ET.indent(self.tree)
    return ET.tostring(self.tree.getroot(), encoding='unicode', xml_declaration=True)
  
  
  def write(self, path:str|Path):
    ET.indent(self.tree)
    self.tree.write(path, encoding='unicode', xml_declaration=True)
  
  
  def get_parts(self) -> dict[str,list[ET.Element]]:
    part_ids = self.resolve_part_ids()
    parts = defaultdict(list)
    
    for part_idx, part in enumerate(self.tree.findall("part")):
      part_id = part.attrib["id"]
      
      if part_id in part_ids['grandstaff']:
        parts['grandstaff'].append((part_idx, part))
        continue
      
      parts['multi'].append((part_idx, part))
    
    self.parts = dict(parts)
    
    return self.parts
  
  
  def resolve_part_ids(self) -> dict:
    part_list = self.tree.getroot().find('part-list')
    part_ids = defaultdict(list)
    
    for part in part_list.findall("score-part"):
      part_id = part.attrib['id']
      
      if self._is_piano_part(part):
        part_ids['grandstaff'].append(part_id)
        continue

      part_ids['multi'].append(part_id)
    
    return part_ids
  
  
  def _is_piano_part(self, part:ET.Element) -> bool:
    inst_name = part.find('score-instrument/instrument-name')
    inst_name = inst_name.text if inst_name is not None else ""
    if inst_name in [
      "Piano", "Grand Piano", "Acoustic Grand Piano",
      "Harpsichord", "Pianoforte", "Piano (2)"
    ]:
      return True
    
    part_name = part.find('part-name')
    part_name = part_name.text if part_name is not None else ""
    if part_name in [
      "Piano", "Pianoforte", "Piano (2)"
    ]:
      return True
    
    return False
  
  
  def _is_string_part(self, part:ET.Element) -> bool:
    inst_name = part.find('score-instrument/instrument-name')
    inst_name = inst_name.text if inst_name is not None else ""
    if inst_name in { "Violin", "Viola", "Cello", "Violoncello" }:
      return True
    
    part_name = part.find('part-name')
    part_name = part_name.text if part_name is not None else ""
    if part_name in { "Violin 1", "Violin 2", "Viola", "Cello", "Violoncello" }:
      return True
  
    return False


  def strip_musicxml(self):
    """
    remove all following elements from the MusicXML
      - <print new-system="yes"/>
      - <print new-page="yes"/>
    which cause issues during comparing MusicXML files
    """
    root = self.tree.getroot()
    
    for measure in root.findall('.//measure'):
      print_els = measure.findall('.//print[@new-system="yes"]')
      for el in print_els:
        measure.remove(el)
      
      print_els = measure.findall('.//print[@new-page="yes"]')
      for el in print_els:
        measure.remove(el)
    
    self.tree = ET.ElementTree(root)
  
  
  def remove_music21_defaults(self):
    """
    remove all following elements from music21
      - movement_title
      - identification
      - defaults
    which cause issues during comparing MusicXML files
    """
    root = self.tree.getroot()
    
    movement_title = root.findall('movement-title')
    for el in movement_title:
      root.remove(el)
    
    identification = root.findall('identification')
    for el in identification:
      root.remove(el)
    
    defaults = root.findall('defaults')
    for el in defaults:
      root.remove(el)
    
    self.tree = ET.ElementTree(root)


  def resolve_measure_rests(self):
    """Replace <rest measure="yes"/> with fully typed rests.

    converter21's xml2abc silently drops whole-measure rests, producing empty
    ABC output. This method converts each such rest to a normal rest with a
    <type> element (and <dot/> elements as needed) so converter21 emits the
    correct ABC tokens.
    """
    root = self.tree.getroot()

    for part in root.findall('.//part'):
      divisions = Fraction(1)

      for measure in part.findall('.//measure'):
        attrs_el = measure.find('attributes')
        if attrs_el is not None:
          div_el = attrs_el.find('divisions')
          if div_el is not None:
            divisions = Fraction(int(div_el.text))

        for note in measure.findall('note'):
          rest_el = note.find('rest')
          if rest_el is None or rest_el.get('measure') != 'yes':
            continue

          dur_el = note.find('duration')
          if dur_el is None:
            continue

          duration_in_quarters = Fraction(int(dur_el.text)) / divisions
          note_type, num_dots = _duration_to_type(duration_in_quarters)

          del rest_el.attrib['measure']

          if note_type is None:
            continue

          children = list(note)
          dur_idx = children.index(dur_el)

          type_el = ET.Element('type')
          type_el.text = note_type
          note.insert(dur_idx + 1, type_el)

          for i in range(num_dots):
            note.insert(dur_idx + 2 + i, ET.Element('dot'))

    self.tree = ET.ElementTree(root)


  def remove_dangling_invisible_elements(self):
    """
    Remove groups of invisible elements 
    that exist only to position <direction> elements or for audio playback.
    These sequences consist of 
      1. <backup>|<forward>
      2. invisible <note>|<rest> elements (print-object="no"),
      3. <direction>

    Algorithm: 
      - scan each measure backward from its end.
        before any trailing <barline>.
      - Collect a contiguous "tail" of invisible elements
        i.e. any <backup>, <forward>, <direction>, or <note print-object="no">. 
      - Stop at the first real (visible) note or structural element. 
        If the tail contains at least one <backup>, 
        remove everything from the first <backup> to the end,
        leaving any <direction> elements that precede the backup intact.
    """
    root = self.tree.getroot()

    for part in root.findall('.//part'):
      for measure in part.findall('.//measure'):
        children = list(measure)

        # Effective end: skip trailing <barline> elements (they must stay)
        end_idx = len(children)
        while end_idx > 0 and children[end_idx - 1].tag == 'barline':
          end_idx -= 1

        # Scan backward to find the start of the invisible tail
        tail_start = end_idx
        for idx in range(end_idx - 1, -1, -1):
          elem = children[idx]
          if elem.tag in ('backup', 'forward', 'direction'):
            tail_start = idx
          elif elem.tag == 'note' and elem.get('print-object') == 'no':
            tail_start = idx
          else:
            break  # real note or structural element — stop

        if tail_start >= end_idx:
          continue  # nothing invisible at the end

        # Find the first <backup> within the tail
        first_backup = None
        for idx in range(tail_start, end_idx):
          if children[idx].tag == 'backup':
            first_backup = idx
            break

        if first_backup is None:
          continue  # tail has no backup, nothing to remove

        # Remove from first_backup to end_idx (reverse order preserves indices)
        for idx in range(end_idx - 1, first_backup - 1, -1):
          measure.remove(children[idx])

    self.tree = ET.ElementTree(root)
  
  
  def remove_zero_alters(self):
    root = self.tree.getroot()
    
    for measure in root.findall('.//measure'):
      parent_map = {
        child: parent 
        for parent in measure.findall('.//pitch') 
          for child in parent.iter()
      }
    
    for alter in measure.findall('.//alter'):
      try:
        if float(alter.text) == 0:
          parent_map[alter].remove(alter)
      except (TypeError, ValueError, KeyError):
        pass
  
  
  def strip_slur_numbers(self):
    root = self.tree.getroot()
    
    for slur in root.findall('.//slur'):
      if 'number' in slur.attrib:
        del slur.attrib['number']