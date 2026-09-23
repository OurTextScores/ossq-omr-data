import xml.etree.ElementTree as ET

from .MxlFile import MusicXMLFile


def inject_measure_numbers(part:ET.Element, measure_numbers:list[str]) -> ET.Element:
  """Inject measure numbers into the <measure> elements of a part"""
  measures = part.findall('.//measure')
  for i, measure in enumerate(measures):
    if i < len(measure_numbers):
      measure.set('number', measure_numbers[i])
  
  return part


def part_to_score(
  part: ET.Element,
  part_id="P2",
  part_name="Piano",
  musicxml_version="3.1"
) -> ET.ElementTree:
  """Embeds a <part> element within a MusicXML <score-partwise> file"""
  
  root = ET.Element("score-partwise")
  root.attrib["version"] = musicxml_version
  
  part_list_element = ET.Element("part-list")
  score_part_element = ET.Element("score-part")
  score_part_element.attrib["id"] = part_id
  part_name_element = ET.Element("part-name")
  part_name_element.text = part_name
  score_part_element.append(part_name_element)
  part_list_element.append(score_part_element)
  
  root.append(part_list_element)
  
  part.attrib["id"] = part_id
  root.append(part)
  
  return ET.ElementTree(root)


def get_part_groups(parts:list[tuple[str,ET.Element]]) -> list[tuple[str,list[ET.Element]]]:
  """Groups parts by their type (e.g., 'instrument', 'voice')"""
  part_groups = []
  cur_group = ()
  prev_type = None

  for part_type, part in parts:
    part_id = part.attrib['id']
    part_name = f'Part {part_id[1:]}'
    
    if part_type == 'grandstaff':
      part_name = f'Piano {part_id}'
    
    if prev_type is None:
      cur_group = (part_type, [(part_id, part_name)])

    elif prev_type == part_type:
      cur_group[1].append((part_id, part_name))

    elif prev_type != part_type:
      part_groups.append(cur_group)
      cur_group = (part_type, [(part_id, part_name)])

    prev_type = part_type
  
  else:
    if cur_group:
      part_groups.append(cur_group)
  
  return part_groups


def parts_to_score(
  parts:list[tuple[str,ET.Element]],
  measure_numbers:list[str]|None=None,
  musicxml_version:str="3.1"
)->ET.ElementTree:
  """Embeds multiple <part> elements within a MusicXML <score-partwise> file"""

  part_groups = get_part_groups(parts)
  
  root = ET.Element("score-partwise")
  root.attrib["version"] = musicxml_version
  
  part_list_el = ET.Element("part-list")

  g_idx = 1
  for group_score_type, group in part_groups:
    if group_score_type != 'grandstaff' and len(group) > 1:
      part_group_st_el = ET.Element("part-group")
      part_group_st_el.attrib['type'] = 'start'
      part_group_st_el.attrib['number'] = str(g_idx)

      group_symbol_el = ET.Element("group-symbol")
      group_symbol_el.text = 'bracket'
      part_group_st_el.append(group_symbol_el)

      part_list_el.append(part_group_st_el)

    for part_id, part_name in group:
      score_part_el = ET.Element("score-part")
      score_part_el.attrib["id"] = part_id
      part_name_el = ET.Element("part-name")
      part_name_el.text = part_name
      score_part_el.append(part_name_el)
      part_list_el.append(score_part_el)

    if group_score_type != 'grandstaff' and len(group) > 1:
      part_group_ed_el = ET.Element("part-group")
      part_group_ed_el.attrib['type'] = 'stop'
      part_group_ed_el.attrib['number'] = str(g_idx)
      part_list_el.append(part_group_ed_el)
      g_idx += 1
  
  root.append(part_list_el)
  
  for _, p in parts:
    if measure_numbers:
      p = inject_measure_numbers(p, measure_numbers)
    root.append(p)
  
  return ET.ElementTree(root)


def string_quartet_parts_to_score(
  parts:list[ET.Element],
  part_ids:list[str]=['P1', 'P2', 'P3', 'P4'],
  part_names:list[str]=['Violin 1', 'Violin 2', 'Viola', 'Violoncello'],
  musicxml_version="3.1"
) -> ET.ElementTree:
  
  assert len(parts) == 4, "There must be exactly 4 parts for a string quartet."
  
  root = ET.Element("score-partwise")
  root.attrib["version"] = musicxml_version
  
  part_list_element = ET.Element("part-list")
  
  # initialize the part-group element
  part_group_start = ET.Element("part-group")
  part_group_start.set("type", 'start')
  part_group_start.set("number", '1')
  
  group_symbol_element = ET.Element("group-symbol")
  group_symbol_element.text = 'bracket'
  
  part_group_start.append(group_symbol_element)
  part_list_element.append(part_group_start)
  
  # add the score-part elements
  for p_id, p_name in zip(part_ids, part_names):
    score_part_element = ET.Element("score-part")
    score_part_element.set("id", p_id)
    part_name_element = ET.Element("part-name")
    part_name_element.text = p_name
    score_part_element.append(part_name_element)
    part_list_element.append(score_part_element)
  
  part_group_end = ET.Element("part-group")
  part_group_end.set("type", 'end')
  part_group_end.set("number", '1')
  
  part_list_element.append(part_group_end)
  
  # add score-part element to the root
  root.append(part_list_element)
  
  # add parts to the root
  for p_id, p in zip(part_ids, parts):
    p.attrib["id"] = p_id
    root.append(p)
  
  return ET.ElementTree(root)