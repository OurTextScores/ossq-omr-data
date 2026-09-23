import difflib
import xml.etree.ElementTree as ET


def compare_parts(expected: ET.Element, given: ET.Element, summary:bool=False):
  measures_e = expected.findall("measure")
  measures_g = given.findall("measure")
  assert len(measures_e) == len(measures_g)
  for i in range(len(measures_e)):
    compare_measures(measures_e[i], measures_g[i], summary=summary)


def compare_measures(expected: ET.Element, given: ET.Element, summary:bool=False):
  measure_number = expected.get("number")

  if len(expected) != len(given):
    # print("Non-matching measure contents!")
    compare_elements(measure_number, expected, given, summary=summary)
    return

  # everything
  for e, g in zip(expected, given):
    compare_elements(measure_number, e, g, summary=summary)


def compare_elements(measure_number: str, expected: ET.Element, given: ET.Element, summary:bool=False):
  e = ET.canonicalize(
    ET.tostring(expected),
    strip_text=True
  )

  g = ET.canonicalize(
    ET.tostring(given),
    strip_text=True
  )
  
  if e != g:
    if summary:
      ET.indent(expected)
      e = ET.tostring(expected, encoding='unicode')
      ET.indent(given)
      g = ET.tostring(given, encoding='unicode')

      diff = difflib.unified_diff(
        e.splitlines(), 
        g.splitlines(), 
        lineterm=''
      )
      
      is_pitch = any( '<pitch>' in line for line in diff )
      
      if is_pitch:
        print()
        print("MEASURE: ", measure_number)
        print("DIFF:")
        diff = difflib.unified_diff(
          e.splitlines(), 
          g.splitlines(), 
          lineterm=''
        ) 
        for line in diff:
          print(line)
    
    else:
      print()
      print("MEASURE: ", measure_number)
      print("EXPECTED:", e)
      print("GIVEN:   ", g)