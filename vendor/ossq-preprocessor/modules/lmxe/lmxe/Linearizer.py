import io
from typing import Union, Iterator, Optional, List, TextIO, Dict
from fractions import Fraction
import xml.etree.ElementTree as ET

from .utils import *
from .vocabulary import *


IGNORED_MEASURE_ELEMENTS = set([
  # https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/measure-partwise/
  "direction", "harmony", "figured-bass", "sound", "listening", "print", 
  "grouping", "link", "bookmark", "barline"
])

IGNORED_ATTRIBUTES_ELEMENTS = set([
  # https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/attributes/
  "footnote", "level", "part-symbol", "instruments", "staff-details",
  "directive", "measure-style"
])

# NOTE: Use assert only for very major things. For everything else,
# use self._error, so that the code works fine with slightly unexpected input

class Measure:
  def __init__(self, *, tokens:list[str], is_new_system:bool, is_new_page:bool, number:Optional[str]=None, signatures:dict[str,tuple[int,int]|int|str]={}):
    self.tokens:list[str] = tokens
    self.is_new_system:bool = is_new_system
    self.is_new_page:bool = is_new_page
    self.number:str = number
    # only tracks signature changes at the beginning of the measure
    # if signatures changes mid measure, it is not recorded here
    # they will be recorded in the tokens list instead
    self.signatures:dict[str,list[int,int]|int|str|bool] = {
      'time': signatures.get('time', [4,4]),
      'key': signatures.get('key', 0),
      'clef': signatures.get('clef', {'1': 'G2'}),
    }
    self.signature_injected = {
      'time': False,
      'key': False,
      'clef': False
    }
  
  def __str__(self):
    return ' '.join(self.tokens)


class PartLinearizer:
  def __init__(
    self, 
    *,
    is_grandstaff:bool=False,
    errout:Optional[TextIO]=None, # usually comes from parent LMXELinearizer
    fail_on_unknown_tokens=True
  ):
    self.is_grandstaff = is_grandstaff

    self._errout = errout or io.StringIO()
    self.fail_on_unknown_tokens = fail_on_unknown_tokens
    
    self.reset_outputs()
    self.reset_states()
  

  def __str__(self):
    return ' '.join([ str(m) for m in self.measures ])
  
  
  def reset_outputs(self):
    self.measures:list[Measure] = []
    self.output_tokens:list[str] = []
  
  
  def reset_states(self):
    # within-part state
    self._part_id: Optional[str] = None # current part ID
    self._measure_number: Optional[str] = None # current measure number
    self._divisions: Optional[int] = None # time units per one quarter note
    self._beats_per_measure: Optional[int] = None # time signature top
    self._beat_type: Optional[int] = None # time signature bottom
    self._measure_duration: Optional[int] = None # time-units per measure
    self._staves: Optional[int] = None # number of staves
    self._clefs: Dict[int, str] = {} # clef tokens for staves
    self._key_signature_fifths: Optional[int] = None # key signature

    # within-measure state
    self._stem_orientation: Optional[str] = None # "up", "down", None
    self._staff: Optional[str] = None # "1", "2", None
    self._onset: int = 0 # in duration units
    self._voice: Optional[str] = None # "1", "2", ... "8", None
    self._previous_note_duration: Optional[int] = None # for chord checks
    self._previous_note_pitch: Optional[str] = None # for chord checks
    self._is_new_system = False
    self._is_new_page = False
  
  
  def _error(self, *values):
    header = f"[ERROR][P:{self._part_id} M:{self._measure_number}]:"
    print(header, *values, file=self._errout)


  def _emit(self, token:str, prepend:bool=False):
    """Emits a token into the output sequence"""
    if self.fail_on_unknown_tokens:
      assert token in ALL_TOKENS, f"Token '{token}' not in the vocabulary"
    else:
      if token not in ALL_TOKENS:
        self._error(f"Token '{token}' not in the vocabulary")
        return

    if prepend:
      self.output_tokens = [token] + self.output_tokens
    else:
      self.output_tokens.append(token)
  

  def _init_current_measure(self) -> Measure:
    return Measure(
      tokens=[],
      is_new_system=self._is_new_system,
      is_new_page=self._is_new_page,
      number=self._measure_number,
      signatures={
        'time': [self._beats_per_measure, self._beat_type] if self._beats_per_measure and self._beat_type else [4,4],
        'key': self._key_signature_fifths,
        'clef': { str(k): v.split(':')[-1] for k, v in self._clefs.items() }
      }
    )
  

  def _update_current_measure_signatures(self, current_measure:Measure) -> Measure:
    has_sig_change, sigs = self._detect_signature_change_start_of_measure(get_tokens=True)

    has_time = has_sig_change['time']
    has_key = has_sig_change['key']
    has_clef = has_sig_change['clef']
    
    # wheter signatures are injectioned or not is
    # inverse of "has_sig_change" values
    # if there is a signature change, 
    # it means there was no injection
    # ignore first measures
    if self._is_new_system and self._measure_number not in {"0", "1"}:
      current_measure.signature_injected = {
        'time': not has_time,
        'key': not has_key,
        'clef': not has_clef,
      }

    # if no changes,
    if not any([has_time, has_key, has_clef]):
      return current_measure

    # if any changes,
    if has_time:
      current_measure.signatures['time'] = sigs['time']
    if has_key:
      current_measure.signatures['key'] = sigs['key']
    if has_clef:
      current_measure.signatures['clef'] = sigs['clef']
    
    return current_measure


  def _update_measures(self, current_measure:Measure):
    current_measure.tokens = self.output_tokens[:]
    # check for signature changes at the beginning of current measure
    
    self.measures.append(current_measure)


  def process_part(self, part: ET.Element):
    # reset within-part state
    self._part_id = None
    self._measure_number = None
    self._divisions = None
    self._beats_per_measure = None
    self._beat_type = None
    self._measure_duration = None
    self._staves = None
    self._clefs = {}
    self._key_signature_fifths = None
    
    assert part.tag == "part"
    self._part_id = part.attrib.get("id")
    for measure in part:
      if measure.tag is ET.Comment:
        continue # ignore comments
      
      assert measure.tag == "measure"
      
      self.process_measure(measure)
  

  def process_measure(self, measure: ET.Element):
    assert measure.tag == "measure"

    # reset within-measure state
    self._stem_orientation = None
    self._staff = None
    self._onset = 0
    self._voice = None
    self._previous_note_duration = None
    self._previous_note_pitch = None

    self._is_new_system = False
    self._is_new_page = False
    self._measure_number = measure.attrib.get("number")

    # empty previous output tokens
    self.output_tokens = []

    # process print options
    print_opt = measure.find('print')
    if print_opt is not None:
      if print_opt.attrib.get('new-system') == 'yes':
        self._is_new_system = True
      elif print_opt.attrib.get('new-page') == 'yes':
        self._is_new_page = True
        self._is_new_system = True # new-page implies new-system
    
    # init current measure with last known signatures
    cur_measure = self._init_current_measure()

    for element in measure:
      if element.tag in IGNORED_MEASURE_ELEMENTS:
        continue
      elif element.tag == "note":
        self.process_note(element, measure)
      elif element.tag == "attributes":
        self.process_attributes(element)
      elif element.tag == "backup":
        self.process_backup(element, measure)
      elif element.tag == "forward":
        self.process_forward(element)
      
      else:
        self._error("Unexpected <measure> element:", element, element.attrib)
    
    # finalize signature information for the measure
    cur_measure = self._update_current_measure_signatures(cur_measure)

    if (self._is_new_system and self._measure_number not in {"0", "1"}):
      self._inject_signatures(cur_measure)
    
    
    if not self.output_tokens and self.is_grandstaff:
      rests_for_measure = [
        "rest", "voice:1", "rest:measure", "staff:1",
        "backup", "whole",
        "rest", "voice:2", "rest:measure", "staff:2",
      ]
      self.output_tokens += rests_for_measure

    # append current measure to self.measures
    self._update_measures(cur_measure)


  def process_note(self, note: ET.Element, measure: ET.Element):
    assert note.tag == "note"

    # [print-object:no]
    if note.attrib.get("print-object") == "no":
      self._emit("print-object:no")

    # [grace]
    grace_element = note.find("grace")
    is_grace_note = grace_element is not None
    if is_grace_note:
      self._emit("grace")
      if grace_element.attrib.get("slash") == "yes":
        self._emit("grace:slash")
    
    # [chord]
    chord_element = note.find("chord")
    is_chord = chord_element is not None
    if is_chord:
      self._emit("chord")

    # [rest] or [pitch]
    rest_element = note.find("rest")
    is_measure_rest = False
    pitch_token: Optional[str] = None
    if rest_element is not None:
      self._emit("rest")
      is_measure_rest = rest_element.attrib.get("measure") == "yes" or len(measure.findall('note')) == 1
    else:
      pitch_element = note.find("pitch")
      pitch_token = pitch_element.find("step").text + pitch_element.find("octave").text
      assert pitch_token in PITCH_TOKENS, "Invalid pitch: " + pitch_token
      self._emit(pitch_token)
    
    # [voice]
    voice_element = note.find("voice")
    if voice_element is not None:
      if self._voice != voice_element.text:
        self._emit("voice:" + voice_element.text)
        self._voice = voice_element.text
    
    # [type] or [rest:measure] - the ROOT of the [note] sequence
    type_element = note.find("type")
    if type_element is not None:
      assert type_element.text in NOTE_TYPE_TOKENS
      self._emit(type_element.text)
    elif is_measure_rest:
      self._emit("rest:measure")
    else:
      self._error("Note does not have <type>:", ET.tostring(note))
    
    # [time-modification] (tuplets rhythm-wise)
    if note.find("time-modification") is not None:
      actual = note.find("time-modification/actual-notes").text
      normal = note.find("time-modification/normal-notes").text
      token = actual + "in" + normal
      self._emit(token)

    # [dot]
    for dot_element in note.findall("dot"):
      self._emit("dot")

    # [accidental]
    accidental_element = note.find("accidental")
    if accidental_element is not None:
      accidental = accidental_element.text
      if accidental not in ACCIDENTAL_TOKENS:
        self._error("Unsupported accidental type:", accidental)
      self._emit(accidental)

    # [stem]
    # stem orientation is reset with each voice start
    # and then only changes are recorded
    # DOUBLE STEMS: are encoded as two notes in two voices,
    # this is what MuseScore produces and is reasonable
    # (even though MusicXML allows for "double" as a value here)
    stem_element = note.find("stem")
    if stem_element is not None:
      if stem_element.text not in ["up", "down", "none"]:
        self._error(
          f"Unknown stem type '{stem_element.text}'.",
          ET.tostring(note)
        )
      else:
        if self._stem_orientation != stem_element.text:
          self._emit("stem:" + stem_element.text)
          self._stem_orientation = stem_element.text
    
    # [staff]
    # like stems, staves are indicated at the beginning
    # of a measure, voice, and during a change of staff
    staff_element = note.find("staff")
    if staff_element is not None:
      if staff_element.text not in ["1", "2", "3"]:
        self._error("Only staves 1,2,3 are supported.")
      else:
        if self.is_grandstaff:
          assert self._staves >= 2 
        
        if self._staff != staff_element.text:
          self._emit("staff:" + staff_element.text)
          self._staff = staff_element.text
    else:
      if self._staff is None:
        self._emit("staff:1")
        self._staff = '1' # pseudo staff

    # [beam]
    for beam in note.findall("beam"):
      assert beam.text in ["begin", "end", "continue", "forward hook", "backward hook"]
      if beam.text != "continue":
        if beam.text == "forward hook":
          self._emit("beam:forward-hook")
        elif beam.text == "backward hook":
          self._emit("beam:backward-hook")
        else:
          self._emit("beam:" + beam.text)

    # [tied]
    for tied_element in note.findall("notations/tied"):
      tied_type = tied_element.attrib.get("type")
      assert tied_type in ["start", "stop"]
      self._emit("tied:" + tied_type)

    # [tuplet]
    for tuplet_element in note.findall("notations/tuplet"):
      tuplet_type = tuplet_element.attrib.get("type")
      assert tuplet_type in ["start", "stop"]
      self._emit("tuplet:" + tuplet_type)
    
    # extended notations and ornaments
    self._process_extended_notations(note)
    
    # extract duration
    duration_element = note.find("duration")
    duration: Optional[int] = None
    if duration_element is None and not is_grace_note:
      self._error("Note lacks duration:", ET.tostring(note))
    elif duration_element is not None:
      duration = int(duration_element.text)
      assert duration > 0

    # check assumptions about the linearization process
    self._verify_note_duration(duration, note, measure, is_measure_rest, is_grace_note)
    self._verify_chords(duration, pitch_token, is_chord, note, measure)

    # perform on-exit state changes
    self._previous_note_duration = duration
    self._previous_note_pitch = pitch_token
    if duration is not None and not is_chord:
      self._onset += duration
  

  def _process_extended_notations(self, note: ET.Element):
    # save some compute time
    notations = note.find("notations")
    if notations is None:
      return

    # [slur]
    for slur_element in notations.findall("slur"):
      slur_type = slur_element.attrib.get("type")
      if slur_type == "continue":
        pass # ignore
      else:
        assert slur_type in ["start", "stop"]
        self._emit("slur:" + slur_type)

    # [fermata]
    fermata_element = notations.find("fermata")
    if fermata_element is not None:
      self._emit("fermata")

    # [arpeggiate]
    arpeggiate_element = notations.find("arpeggiate")
    if arpeggiate_element is not None:
      self._emit("arpeggiate")
    
    # [staccato]
    staccato_element = notations.find("articulations/staccato")
    if staccato_element is not None:
      self._emit("staccato")

    # [accent]
    accent_element = notations.find("articulations/accent")
    if accent_element is not None:
      self._emit("accent")

    # [strong-accent]
    strong_accent_element = notations.find("articulations/strong-accent")
    if strong_accent_element is not None:
      self._emit("strong-accent")

    # [tenuto]
    tenuto_element = notations.find("articulations/tenuto")
    if tenuto_element is not None:
      self._emit("tenuto")
    
    # [tremolo]
    tremolo_element = notations.find("ornaments/tremolo")
    if tremolo_element is not None:
      tremolo_type = tremolo_element.attrib.get("type", "single")
      tremolo_marks = tremolo_element.text
      assert tremolo_type in ["single", "start", "stop", "unmeasured"]
      assert tremolo_marks in ["1", "2", "3", "4"]
      self._emit("tremolo:" + tremolo_type)
      self._emit("tremolo:" + tremolo_marks)

    # [trill-mark]
    trill_mark_element = notations.find("ornaments/trill-mark")
    if trill_mark_element is not None:
      self._emit("trill-mark")
  

  def _verify_note_duration(
    self, duration: Optional[int], note: ET.Element, measure: ET.Element,
    is_measure_rest: bool, is_grace_note: bool
  ):
    if duration is None:
      return

    # verify for measure rests
    if is_measure_rest:
      if duration != self._measure_duration:
        self._error(
          "Measure rest does not have expected duration.",
          "Divisions:", + self._divisions,
          "Measure duration:", self._measure_duration,
          ET.tostring(note)
        )
      return
    
    # verify for regular notes
    expected_duration, expected_duration_float = self._expected_note_duration(note)
    
    if expected_duration != duration:
      self._error(
        "Note does not have expected duration.",
        "Expected:", expected_duration_float,
        "Actual:", duration,
        ET.tostring(note)
      )
  

  def _expected_note_duration(self, note: ET.Element) -> int:
    type_element = note.find("type")
    
    if type_element is None:
      note_type = "whole"
    else:
      note_type = type_element.text

    # simple conversion
    expected_duration: Fraction = NOTE_TYPE_TO_QUARTER_MULTIPLE[note_type] * self._divisions

    # handle duration dots
    dot_duration = expected_duration / 2
    for _ in note.findall("dot"):
      expected_duration += dot_duration
      dot_duration /= 2
    
    # handle time modification
    if note.find("time-modification") is not None:
      actual = int(note.find("time-modification/actual-notes").text)
      normal = int(note.find("time-modification/normal-notes").text)
      expected_duration *= Fraction(normal, actual)
    
    # The denominaotor now SHOULD be 1, if the file is valid MusicXML.
    # BUT! The reality strucks and you find out that MuseScore caps
    # divisions at 480 and won't go higher. Which causes non-integer
    # results here. And they don't even covnert to int, they round instead!
    # So there must have been some obscure reason for their decision.
    # Either they play 4D Chess, or some random contributor on the internet
    # put round() there because he felt like so. Either way, we have to
    # round as well to get the same results.
    return round(expected_duration), float(expected_duration) # keep the floats for error handling
    # assert expected_duration.denominator == 1
    # return expected_duration.numerator
  

  def _verify_chords(
    self, duration: Optional[int], pitch_token: Optional[str],
    is_chord: bool, note: ET.Element, measure: ET.Element
  ):
    if not is_chord:
      return
    
    # verify duration
    if duration != self._previous_note_duration:
      self._error(
        "Chord notes have varying duration.",
        ET.tostring(note)
      )
    
    # verify pitch order
    previous_order = PITCH_TOKENS.index(self._previous_note_pitch) if self._previous_note_pitch is not None else -1
    current_order = PITCH_TOKENS.index(pitch_token)
    if previous_order > current_order:
      self._error(
        "Chord notes must have ascending pitches.",
        ET.tostring(note)
      )


  def process_attributes(self, attributes: ET.Element):
    # the order of elements is well defined
    # https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/attributes/
    assert attributes.tag == "attributes"

    # divisions
    divisions_element = attributes.find("divisions")
    if divisions_element is not None:
      self.process_divisions(divisions_element)
    
    # key signature (process even if missing due to re-prints)
    key_element = attributes.find("key")
    self.process_key_signature(key_element)

    # time signature
    time_element = attributes.find("time")
    if time_element is not None:
      self.process_time_signature(time_element)
    
    # staves
    staves_element = attributes.find("staves")
    if staves_element is not None and self.is_grandstaff:
      self._staves = int(staves_element.text)
    elif staves_element is None and not self.is_grandstaff:
      self._staves = 1 # pseudo staves for non grandstaff

    # clef (process even if missing due to re-prints)
    clef_elements = attributes.findall("clef")
    self.process_clefs(clef_elements)

    # check that all elements have been processed
    for element in attributes:
      if element.tag in ["divisions", "key", "time", "staves", "clef"]:
        pass # has been processed already
      elif element.tag in IGNORED_ATTRIBUTES_ELEMENTS:
        pass # ignored
      else:
        self._error("Unexpected <attributes> element:", element, element.attrib)


  def process_divisions(self, divisions: ET.Element):
    assert divisions.tag == "divisions"

    self._divisions = int(divisions.text)
    assert self._divisions > 0, "<divisions> should be a positive number"


  def process_time_signature(self, time: ET.Element):
    assert time.tag == "time"

    assert self._divisions is not None, "Time signature should follow <divisions>"
    
    beats_element = time.find("beats")
    assert beats_element is not None, "<beats> must be present in <time> element"
    beat_type_element = time.find("beat-type")
    assert beat_type_element is not None, "<beat-type> must be present in <time> element"
    
    is_normal_beat = True if '+' not in beats_element.text else False
    
    self._beats_per_measure = (
      int(beats_element.text) 
      if is_normal_beat 
      else sum(map(int, beats_element.text.split('+')))
    )
    assert self._beats_per_measure > 0
    self._beat_type = int(beat_type_element.text)
    assert self._beat_type > 0

    # emit tokens
    self._emit("time")
    self._emit( "beats:" + (str(self._beats_per_measure) if is_normal_beat else beats_element.text) )
    self._emit("beat-type:" + str(self._beat_type))

    # compute measure duration
    beat_type_fraction = Fraction(1, self._beat_type)
    quarters_per_beat_type = beat_type_fraction / Fraction(1, 4)
    quarters_per_measure = quarters_per_beat_type * self._beats_per_measure
    time_units_per_measure = quarters_per_measure * self._divisions
    assert time_units_per_measure.denominator == 1, "Measure duration calculation failed"
    self._measure_duration = time_units_per_measure.numerator


  def process_key_signature(self, key: Optional[ET.Element]):
    if key is not None:
      self._key_signature_fifths = int(key.find("fifths").text)
      self._emit("key:fifths:" + str(self._key_signature_fifths))
  

  def _detect_signature_change_start_of_measure(self, get_tokens:bool=False)->dict[str,bool]:
    """Detects whether there are signature changes at the start of the measure"""
    has_signature = {
      'time': False,
      'key': False,
      'clef': False
    }
    
    signatures = {
      'time': None,
      'key': None,
      'clef': None
    }

    # find first note in current measure
    first_note_index = find_nth_token_index(
      self.output_tokens, 
      1,
      token_set=NOTE_PREFIX_TOKENS,
    ) 
    attr_tokens = self.output_tokens[:first_note_index]

    if len(set(attr_tokens)&{'time'}) > 0:
      has_signature['time'] = True
      if get_tokens:
        time_index = attr_tokens.index('time')
        beats = attr_tokens[time_index + 1].split(':')[-1]
        if '+' in beats:
          beats = sum(map(int, beats.split('+')))
        beat_type = attr_tokens[time_index + 2].split(':')[-1]
        signatures['time'] = [int(beats), int(beat_type)]
    
    if len(set(attr_tokens)&set(KEY_TOKENS)) > 0:
      has_signature['key'] = True
      if get_tokens:
        key_token = next(
          t for t in attr_tokens 
          if t.startswith('key:fifths:')
        )
        fifths = int(key_token.split(':')[-1])
        signatures['key'] = fifths
    
    if len(set(attr_tokens)&set(CLEF_TOKENS)) > 0:
      has_signature['clef'] = True
      if get_tokens:
        clefs_dict = {}
        for i in range(len(attr_tokens) - 1):
          t = attr_tokens[i]
          t_next = attr_tokens[i+1]
          if 'clef:' in t and 'staff:' in t_next:
            staff_number = t_next.split(':')[-1]
            clefs_dict[staff_number] = t.split(':')[-1]
        signatures['clef'] = clefs_dict

    return has_signature, signatures
  

  def _inject_signatures(self, current_measure:Measure):
    """
    Injects the last known signatures into the start of the first measure of a new system.
    For the consistency, regardless of whether there was a signature change or not.
    1. key signature
    2. (time signature) - if only time signature changed
    3. clefs - including staff numbers
    """

    first_note_index = find_nth_token_index(
      self.output_tokens, 
      1, 
      token_set=NOTE_PREFIX_TOKENS
    ) # find first note in current measure
    attr_tokens = self.output_tokens[:first_note_index]
    
    inject_time = False
    if 'time' in set(attr_tokens):
      inject_time = True
    
    inject_tokens = []

    # append key signature
    key_fifths = str(current_measure.signatures['key'])
    inject_tokens.append( f"key:fifths:{key_fifths}" )

    # append time signature if needed
    if inject_time:
      beats, beat_type = current_measure.signatures['time']
      inject_tokens.append("time")
      inject_tokens.append( f"beats:{beats}" )
      inject_tokens.append( f"beat-type:{beat_type}" )
    
    # append clefs
    clefs_dict = current_measure.signatures['clef']
    for staff_number in sorted(clefs_dict.keys(), key=lambda x: int(x)):
      clef_token = "clef:" + clefs_dict[staff_number]
      inject_tokens.append(clef_token)
      inject_tokens.append( "staff:" + str(staff_number) )
    
    self.output_tokens = inject_tokens + self.output_tokens[first_note_index:]
  
  
  def process_clefs(self, clefs: List[ET.Element]):
    # get all the currently defined clefs (staff -> clef token)
    # (those are always printed)
    clefs_to_print = {}
    for clef in clefs:
      staff_number = int(clef.attrib.get("number", "1"))
      clef_token = (
        "clef:" + clef.find("sign").text.upper()
          + clef.find("line").text
      )
      
      if 'percussion' in clef_token:
        self._error(f"'percussion' clef is not available. Skipping.")
        continue
        
      clefs_to_print[staff_number] = clef_token

      # remember the clef for future printing
      self._clefs[staff_number] = clef_token

    # now we can print all the clefs to be printed, IN THE PROPER ORDER
    for staff_number in sorted(clefs_to_print.keys()):
      self._emit(clefs_to_print[staff_number])
      if self._staves is not None: # emit staff number only if we're multistaff
        self._emit("staff:" + str(staff_number))
  

  def process_backup(self, backup: ET.Element, measure: ET.Element):
    assert backup.tag == "backup"

    # get the duration
    backup_duration = int(backup.find("duration").text)
    assert backup_duration > 0

    # build up to match the duration
    for note_type in self._duration_to_note_types(backup_duration):
      self._emit("backup")
      self._emit(note_type)
    
    # backup resets these values
    self._voice = None
    self._onset -= backup_duration
    self._staff = None
    self._stem_orientation = None


  def process_forward(self, forward: ET.Element):
    assert forward.tag == "forward"

    # get the duration
    forward_duration = int(forward.find("duration").text)
    assert forward_duration > 0

    # build up to match the duration
    for note_type in self._duration_to_note_types(forward_duration):
      self._emit("forward")
      self._emit(note_type)

    # update within-measure onset
    self._onset += forward_duration
  
  
  def _duration_to_note_types(self, duration: int) -> Iterator[str]:
    assert self._divisions is not None, "<backup/forward> should follow <divisions>"
    assert NOTE_TYPE_TOKENS[-1] == "maxima"
    
    remainder = duration
    step = self._divisions * 32 # 32 quarters in one maxima
    
    for note_type in reversed(NOTE_TYPE_TOKENS):
      if remainder <= 0:
        break
      if step <= remainder:
        yield note_type
        remainder -= step
      step //= 2
    
    # Happens in very few, very weird cases
    if remainder != 0:
      self._error(
        # possible solution: make the forward a tuplet note
        "Duration could not be split up to note types for " + \
        "forward/backup. This is most likely a tuplet forward.",
        "Duration:", duration,
        "Divisions:", self._divisions
      ) 



class LMXELinearizer:
  def __init__(
    self, 
    *,
    score_type:str='multi', 
    errout:Optional[TextIO]=None, 
    fail_on_unknown_tokens=True
  ): 
    assert score_type in SCORE_TYPE_TOKENS, f"Invalid score type: {score_type}"

    self.score_type = score_type
    
    self.errout = errout
    self.fail_on_unknown_tokens = fail_on_unknown_tokens

    self.lmx_parts = None
    self.lmx_score = None
  
  
  def process_parts(self, parts:dict[str,list[ET.Element]]):
    lmx_parts = {
      key: [] 
      for key in parts.keys()
    }
    
    for key, part_list in parts.items():
      linearizer = PartLinearizer(
        is_grandstaff=(key=='grandstaff'),
        errout=self.errout, 
        fail_on_unknown_tokens=self.fail_on_unknown_tokens, 
      )

      for part_idx, part in part_list:
        linearizer.reset_outputs()
        linearizer.reset_states()
        linearizer.process_part(part)
        part_measures:list[Measure] = linearizer.measures
        lmx_parts[key].append( (part_idx, part_measures) )
    
    self.lmx_parts = lmx_parts
  
  
  def get_lmx_score(self):
    assert self.lmx_parts is not None, "XML parts not processed yet"

    part_score_types = []
    total_parts = []
    for score_type, part_list in self.lmx_parts.items():
      total_parts += part_list
      part_score_types += [ score_type for _ in part_list ]
    total_parts = sorted(zip(total_parts, part_score_types), key=lambda x: x[0][0]) # sort by part_idx

    num_parts = len(total_parts)

    # total_parts: list[tuple[part_idx, list[measure]]]
    total_parts, part_score_types = zip(*total_parts)
  
    assert len(part_score_types) == len(total_parts), "Parts count mismatch"

    pages_by_parts = [ [] for _ in range(len(total_parts)) ]
    for p_idx, part in total_parts:
      cur_page = []
      cur_system = []
      # part is list[Measure]
      for m in part:
        if m.is_new_page:
          cur_page.append(cur_system)
          pages_by_parts[p_idx].append(cur_page)
          cur_page = []
          cur_system = []
        elif m.is_new_system:
          cur_page.append(cur_system)
          cur_system = []
        
        cur_system.append(m)
      
      else:
        if len(cur_system) > 0:
          cur_page.append(cur_system)
        if len(cur_page) > 0:
          pages_by_parts[p_idx].append(cur_page)

    assert all( [ 
      len(pages_by_parts[0]) == len(pages) 
      for pages in pages_by_parts[1:] 
    ] ), 'number of pages between parts do not match'

    assert all([
      all([
        len(pages[0]) == len(part) 
        for part in pages[1:]
      ])
      for pages in zip(*pages_by_parts)
    ]), 'number of systems in a pages between parts do not match'

    assert all([
      all([
        all([
          len(systems[0]) == len(system)
          for system in systems[1:]
        ])
        for systems in zip(*pages)
      ])
      for pages in zip(*pages_by_parts)
    ]), 'number of measures in systems between parts do not match'

    lmx_score = []
    # zip(*pages_by_parts): (page, system, measure, part)
    for p_idx, page in enumerate(zip(*pages_by_parts)):  
      lmx_page = []
      
      for _, system in enumerate(zip(*page)):
        lmx_system = []

        measure_nos = [ m.number for m in system[0] ]
        # track only first measure of a system
        signature_injected = [
          p_system[0].signature_injected
          for p_system in system
        ]
        
        signatures = []
        for _, measure in enumerate(zip(*system)):
          assert len(measure) == len(total_parts) == len(part_score_types), 'Number of parts mismatch'
          
          measure_signatures = []
          lmx_measure = ['measure']
          for p_i, part in enumerate(measure):
            measure_signatures.append(part.signatures)
            
            part_token = f'part:{p_i+1}'
            lmx_measure += [ part_token, part_score_types[p_i] ]
            lmx_measure += part.tokens
          
          signatures.append(measure_signatures)
          lmx_system.append( ' '.join(lmx_measure) )
        
        lmx_page.append((
          num_parts,
          measure_nos,
          signature_injected,
          signatures,
          lmx_system
        ))
      
      lmx_score.append(lmx_page)
    
    self.lmx_score = lmx_score
    
    return lmx_score



class LEGCY_LINEARLIZERS:
  pass


class Linearizer:
  def __init__(self, errout: Optional[TextIO] = None, fail_on_unknown_tokens=True):
    self._errout = errout or io.StringIO()
    """Print errors and warnings here"""

    self.output_tokens: List[str] = []
    """The output linearized sequence, split up into tokens"""

    self.fail_on_unknown_tokens = fail_on_unknown_tokens
      
    # within-part state
    self._part_id: Optional[str] = None # current part ID
    self._measure_number: Optional[str] = None # current measure number
    self._divisions: Optional[int] = None # time units per one quarter note
    self._beats_per_measure: Optional[int] = None # time signature top
    self._beat_type: Optional[int] = None # time signature bottom
    self._measure_duration: Optional[int] = None # time-units per measure
    self._staves: Optional[int] = None # number of staves
    self._clefs: Dict[int, str] = {} # clef tokens for staves
    self._key_signature_fifths: Optional[int] = None # key signature

    # within-measure state
    self._stem_orientation: Optional[str] = None # "up", "down", None
    self._staff: Optional[str] = None # "1", "2", None
    self._onset: int = 0 # in duration units
    self._voice: Optional[str] = None # "1", "2", ... "8", None
    self._previous_note_duration: Optional[int] = None # for chord checks
    self._previous_note_pitch: Optional[str] = None # for chord checks


  def _error(self, *values):
    header = f"[ERROR][P:{self._part_id} M:{self._measure_number}]:"
    print(header, *values, file=self._errout)

  
  def _emit(self, token: str):
    """Emits a token into the output sequence"""
    if self.fail_on_unknown_tokens:
      assert token in ALL_TOKENS, f"Token '{token}' not in the vocabulary"
    else:
      if token not in ALL_TOKENS:
        self._error(f"Token '{token}' not in the vocabulary")
        return
    
    self.output_tokens.append(token)
  

  def process_part(self, part: ET.Element):
    # reset within-part state
    self._part_id = None
    self._measure_number = None
    self._divisions = None
    self._beats_per_measure = None
    self._beat_type = None
    self._measure_duration = None
    self._staves = None
    self._clefs = {}
    self._key_signature_fifths = None
    
    assert part.tag == "part"
    self._part_id = part.attrib.get("id")
    for measure in part:
      if measure.tag is ET.Comment:
        continue # ignore comments

      assert measure.tag == "measure"
      
      self.process_measure(measure)
      
  def process_measure(self, measure: ET.Element):
    assert measure.tag == "measure"

    # reset within-measure state
    self._stem_orientation = None
    self._staff = None
    self._onset = 0
    self._voice = None
    self._previous_note_duration = None
    self._previous_note_pitch = None

    self._measure_number = measure.attrib.get("number")
    
    # start a new measure
    self._emit("measure")

    for element in measure:
      if element.tag in IGNORED_MEASURE_ELEMENTS:
        continue
      elif element.tag == "note":
        self.process_note(element, measure)
      elif element.tag == "attributes":
        self.process_attributes(element)
      elif element.tag == "backup":
        self.process_backup(element, measure)
      elif element.tag == "forward":
        self.process_forward(element)
      else:
        self._error("Unexpected <measure> element:", element, element.attrib)
      
      
  def process_note(self, note: ET.Element, measure: ET.Element):
    assert note.tag == "note"

    # [print-object:no]
    if note.attrib.get("print-object") == "no":
      self._emit("print-object:no")

    # [grace]
    grace_element = note.find("grace")
    is_grace_note = grace_element is not None
    if is_grace_note:
      self._emit("grace")
      if grace_element.attrib.get("slash") == "yes":
        self._emit("grace:slash")
    
    # [chord]
    chord_element = note.find("chord")
    is_chord = chord_element is not None
    if is_chord:
      self._emit("chord")

    # [rest] or [pitch]
    rest_element = note.find("rest")
    is_measure_rest = False
    pitch_token: Optional[str] = None
    if rest_element is not None:
      self._emit("rest")
      is_measure_rest = rest_element.attrib.get("measure") == "yes" or len(measure.findall('note')) == 1
    else:
      pitch_element = note.find("pitch")
      pitch_token = pitch_element.find("step").text + pitch_element.find("octave").text
      assert pitch_token in PITCH_TOKENS, "Invalid pitch: " + pitch_token
      self._emit(pitch_token)
    
    # [voice]
    voice_element = note.find("voice")
    if voice_element is not None:
      if self._voice != voice_element.text:
        self._emit("voice:" + voice_element.text)
        self._voice = voice_element.text
    
    # [type] or [rest:measure] - the ROOT of the [note] sequence
    type_element = note.find("type")
    if type_element is not None:
      assert type_element.text in NOTE_TYPE_TOKENS
      self._emit(type_element.text)
    elif is_measure_rest:
      self._emit("rest:measure")
    else:
      self._error("Note does not have <type>:", ET.tostring(note))
    
    # [time-modification] (tuplets rhythm-wise)
    if note.find("time-modification") is not None:
      actual = note.find("time-modification/actual-notes").text
      normal = note.find("time-modification/normal-notes").text
      token = actual + "in" + normal
      self._emit(token)

    # [dot]
    for dot_element in note.findall("dot"):
      self._emit("dot")

    # [accidental]
    accidental_element = note.find("accidental")
    if accidental_element is not None:
      accidental = accidental_element.text
      if accidental not in ACCIDENTAL_TOKENS:
        self._error("Unsupported accidental type:", accidental)
      self._emit(accidental)

    # [stem]
    # stem orientation is reset with each voice start
    # and then only changes are recorded
    # DOUBLE STEMS: are encoded as two notes in two voices,
    # this is what MuseScore produces and is reasonable
    # (even though MusicXML allows for "double" as a value here)
    stem_element = note.find("stem")
    if stem_element is not None:
      if stem_element.text not in ["up", "down", "none"]:
        self._error(
          f"Unknown stem type '{stem_element.text}'.",
          ET.tostring(note)
        )
      else:
        if self._stem_orientation != stem_element.text:
          self._emit("stem:" + stem_element.text)
          self._stem_orientation = stem_element.text
    
    # [staff]
    # like stems, staves are indicated at the beginning
    # of a measure, voice, and during a change of staff
    staff_element = note.find("staff")
    if staff_element is not None:
      if staff_element.text not in ["1", "2", "3"]:
        self._error("Only staves 1,2,3 are supported.")
      else:
        assert self._staves >= 2
        if self._staff != staff_element.text:
          self._emit("staff:" + staff_element.text)
          self._staff = staff_element.text

    # [beam]
    for beam in note.findall("beam"):
      assert beam.text in ["begin", "end", "continue", "forward hook", "backward hook"]
      if beam.text != "continue":
        if beam.text == "forward hook":
          self._emit("beam:forward-hook")
        elif beam.text == "backward hook":
          self._emit("beam:backward-hook")
        else:
          self._emit("beam:" + beam.text)

    # [tied]
    for tied_element in note.findall("notations/tied"):
      tied_type = tied_element.attrib.get("type")
      assert tied_type in ["start", "stop"]
      self._emit("tied:" + tied_type)

    # [tuplet]
    for tuplet_element in note.findall("notations/tuplet"):
      tuplet_type = tuplet_element.attrib.get("type")
      assert tuplet_type in ["start", "stop"]
      self._emit("tuplet:" + tuplet_type)
    
    # extended notations and ornaments
    self._process_extended_notations(note)
    
    # extract duration
    duration_element = note.find("duration")
    duration: Optional[int] = None
    if duration_element is None and not is_grace_note:
      self._error("Note lacks duration:", ET.tostring(note))
    elif duration_element is not None:
      duration = int(duration_element.text)
      assert duration > 0

    # check assumptions about the linearization process
    self._verify_note_duration(duration, note, measure, is_measure_rest, is_grace_note)
    self._verify_chords(duration, pitch_token, is_chord, note, measure)

    # perform on-exit state changes
    self._previous_note_duration = duration
    self._previous_note_pitch = pitch_token
    if duration is not None and not is_chord:
      self._onset += duration
  

  def _process_extended_notations(self, note: ET.Element):
    # save some compute time
    notations = note.find("notations")
    if notations is None:
      return

    # [slur]
    for slur_element in notations.findall("slur"):
      slur_type = slur_element.attrib.get("type")
      if slur_type == "continue":
        pass # ignore
      else:
        assert slur_type in ["start", "stop"]
        self._emit("slur:" + slur_type)

    # [fermata]
    fermata_element = notations.find("fermata")
    if fermata_element is not None:
      self._emit("fermata")

    # [arpeggiate]
    arpeggiate_element = notations.find("arpeggiate")
    if arpeggiate_element is not None:
      self._emit("arpeggiate")
    
    # [staccato]
    staccato_element = notations.find("articulations/staccato")
    if staccato_element is not None:
      self._emit("staccato")

    # [accent]
    accent_element = notations.find("articulations/accent")
    if accent_element is not None:
      self._emit("accent")

    # [strong-accent]
    strong_accent_element = notations.find("articulations/strong-accent")
    if strong_accent_element is not None:
      self._emit("strong-accent")

    # [tenuto]
    tenuto_element = notations.find("articulations/tenuto")
    if tenuto_element is not None:
      self._emit("tenuto")
    
    # [tremolo]
    tremolo_element = notations.find("ornaments/tremolo")
    if tremolo_element is not None:
      tremolo_type = tremolo_element.attrib.get("type", "single")
      tremolo_marks = tremolo_element.text
      assert tremolo_type in ["single", "start", "stop", "unmeasured"]
      assert tremolo_marks in ["1", "2", "3", "4"]
      self._emit("tremolo:" + tremolo_type)
      self._emit("tremolo:" + tremolo_marks)

    # [trill-mark]
    trill_mark_element = notations.find("ornaments/trill-mark")
    if trill_mark_element is not None:
      self._emit("trill-mark")
  

  def _verify_note_duration(
    self, duration: Optional[int], note: ET.Element, measure: ET.Element,
    is_measure_rest: bool, is_grace_note: bool
  ):
    if duration is None:
      return

    # verify for measure rests
    if is_measure_rest:
      if duration != self._measure_duration:
        self._error(
          "Measure rest does not have expected duration.",
          "Divisions:", + self._divisions,
          "Measure duration:", self._measure_duration,
          ET.tostring(note)
        )
      return
    
    # verify for regular notes
    expected_duration, expected_duration_float = self._expected_note_duration(note)
    
    if expected_duration != duration:
      self._error(
        "Note does not have expected duration.",
        "Expected:", expected_duration_float,
        "Actual:", duration,
        ET.tostring(note)
      )
  

  def _expected_note_duration(self, note: ET.Element) -> int:
    type_element = note.find("type")
    
    if type_element is None:
      note_type = "whole"
    else:
      note_type = type_element.text

    # simple conversion
    expected_duration: Fraction = NOTE_TYPE_TO_QUARTER_MULTIPLE[note_type] * self._divisions

    # handle duration dots
    dot_duration = expected_duration / 2
    for _ in note.findall("dot"):
      expected_duration += dot_duration
      dot_duration /= 2
    
    # handle time modification
    if note.find("time-modification") is not None:
      actual = int(note.find("time-modification/actual-notes").text)
      normal = int(note.find("time-modification/normal-notes").text)
      expected_duration *= Fraction(normal, actual)
    
    # The denominaotor now SHOULD be 1, if the file is valid MusicXML.
    # BUT! The reality strucks and you find out that MuseScore caps
    # divisions at 480 and won't go higher. Which causes non-integer
    # results here. And they don't even covnert to int, they round instead!
    # So there must have been some obscure reason for their decision.
    # Either they play 4D Chess, or some random contributor on the internet
    # put round() there because he felt like so. Either way, we have to
    # round as well to get the same results.
    return round(expected_duration), float(expected_duration) # keep the floats for error handling
    # assert expected_duration.denominator == 1
    # return expected_duration.numerator
  

  def _verify_chords(
    self, duration: Optional[int], pitch_token: Optional[str],
    is_chord: bool, note: ET.Element, measure: ET.Element
  ):
    if not is_chord:
      return
    
    # verify duration
    if duration != self._previous_note_duration:
      self._error(
        "Chord notes have varying duration.",
        ET.tostring(note)
      )
    
    # verify pitch order
    previous_order = PITCH_TOKENS.index(self._previous_note_pitch) if self._previous_note_pitch is not None else -1
    current_order = PITCH_TOKENS.index(pitch_token)
    if previous_order > current_order:
      self._error(
        "Chord notes must have ascending pitches.",
        ET.tostring(note)
      )


  def process_attributes(self, attributes: ET.Element):
    # the order of elements is well defined
    # https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/attributes/
    assert attributes.tag == "attributes"

    # divisions
    divisions_element = attributes.find("divisions")
    if divisions_element is not None:
      self.process_divisions(divisions_element)
    
    # key signature (process even if missing due to re-prints)
    key_element = attributes.find("key")
    self.process_key_signature(key_element)

    # time signature
    time_element = attributes.find("time")
    if time_element is not None:
      self.process_time_signature(time_element)
    
    # staves
    staves_element = attributes.find("staves")
    if staves_element is not None:
      self._staves = int(staves_element.text)

    # clef (process even if missing due to re-prints)
    clef_elements = attributes.findall("clef")
    self.process_clefs(clef_elements)

    # check that all elements have been processed
    for element in attributes:
      if element.tag in ["divisions", "key", "time", "staves", "clef"]:
        pass # has been processed already
      elif element.tag in IGNORED_ATTRIBUTES_ELEMENTS:
        pass # ignored
      else:
        self._error("Unexpected <attributes> element:", element, element.attrib)


  def process_divisions(self, divisions: ET.Element):
    assert divisions.tag == "divisions"

    self._divisions = int(divisions.text)
    assert self._divisions > 0, "<divisions> should be a positive number"


  def process_time_signature(self, time: ET.Element):
    assert time.tag == "time"

    assert self._divisions is not None, "Time signature should follow <divisions>"
    
    beats_element = time.find("beats")
    assert beats_element is not None, "<beats> must be present in <time> element"
    beat_type_element = time.find("beat-type")
    assert beat_type_element is not None, "<beat-type> must be present in <time> element"
    
    is_normal_beat = True if '+' not in beats_element.text else False
    
    self._beats_per_measure = (
      int(beats_element.text) 
      if is_normal_beat 
      else sum(map(int, beats_element.text.split('+')))
    )
    assert self._beats_per_measure > 0
    self._beat_type = int(beat_type_element.text)
    assert self._beat_type > 0

    # emit tokens
    self._emit("time")
    self._emit( "beats:" + (str(self._beats_per_measure) if is_normal_beat else beats_element.text) )
    self._emit("beat-type:" + str(self._beat_type))

    # compute measure duration
    beat_type_fraction = Fraction(1, self._beat_type)
    quarters_per_beat_type = beat_type_fraction / Fraction(1, 4)
    quarters_per_measure = quarters_per_beat_type * self._beats_per_measure
    time_units_per_measure = quarters_per_measure * self._divisions
    assert time_units_per_measure.denominator == 1, "Measure duration calculation failed"
    self._measure_duration = time_units_per_measure.numerator


  def process_key_signature(self, key: Optional[ET.Element]):
    if key is not None:
      self._key_signature_fifths = int(key.find("fifths").text)
      self._emit("key:fifths:" + str(self._key_signature_fifths))

  
  def process_clefs(self, clefs: List[ET.Element]):
    # get all the currently defined clefs (staff -> clef token)
    # (those are always printed)
    clefs_to_print = {}
    for clef in clefs:
      staff_number = int(clef.attrib.get("number", "1"))
      clef_token = (
        "clef:" + clef.find("sign").text.upper()
          + clef.find("line").text
      )
      
      if 'percussion' in clef_token:
        self._error(f"'percussion' clef is not available. Skipping.")
        continue
        
      clefs_to_print[staff_number] = clef_token

      # remember the clef for future printing
      self._clefs[staff_number] = clef_token

    # now we can print all the clefs to be printed, IN THE PROPER ORDER
    for staff_number in sorted(clefs_to_print.keys()):
      self._emit(clefs_to_print[staff_number])
      if self._staves is not None: # emit staff number only if we're multistaff
        self._emit("staff:" + str(staff_number))
  

  def process_backup(self, backup: ET.Element, measure: ET.Element):
    assert backup.tag == "backup"

    # get the duration
    backup_duration = int(backup.find("duration").text)
    assert backup_duration > 0

    # build up to match the duration
    for note_type in self._duration_to_note_types(backup_duration):
      self._emit("backup")
      self._emit(note_type)
    
    # backup resets these values
    self._voice = None
    self._onset -= backup_duration
    self._staff = None
    self._stem_orientation = None


  def process_forward(self, forward: ET.Element):
    assert forward.tag == "forward"

    # get the duration
    forward_duration = int(forward.find("duration").text)
    assert forward_duration > 0

    # build up to match the duration
    for note_type in self._duration_to_note_types(forward_duration):
      self._emit("forward")
      self._emit(note_type)

    # update within-measure onset
    self._onset += forward_duration
  
  
  def _duration_to_note_types(self, duration: int) -> Iterator[str]:
    assert self._divisions is not None, "<backup/forward> should follow <divisions>"
    assert NOTE_TYPE_TOKENS[-1] == "maxima"
    
    remainder = duration
    step = self._divisions * 32 # 32 quarters in one maxima
    
    for note_type in reversed(NOTE_TYPE_TOKENS):
      if remainder <= 0:
        break
      if step <= remainder:
        yield note_type
        remainder -= step
      step //= 2
    
    # Happens in very few, very weird cases
    if remainder != 0:
      self._error(
        # possible solution: make the forward a tuplet note
        "Duration could not be split up to note types for " + \
        "forward/backup. This is most likely a tuplet forward.",
        "Duration:", duration,
        "Divisions:", self._divisions
      )



class SQPartLinearizer(Linearizer):
  def __init__(self, errout:Optional[TextIO]=None, fail_on_unknown_tokens=False):
    super().__init__(errout, fail_on_unknown_tokens)
    self._init_output_attr_tokens = lambda: {
      key: None
      for key in ['key', 'time', 'clef']
    }
    self.output_attr_tokens: dict = self._init_output_attr_tokens()
    self.measures: list[list[str]] = []
  
  
  def _flatten_output_attr_tokens(self, attr_tokens: dict) -> list[str]:
    flat_tokens = []
    
    if attr_tokens['key'] is not None:
      flat_tokens.append(attr_tokens['key'])
    
    if attr_tokens['time'] is not None:
      flat_tokens.extend(attr_tokens['time'])
    
    if attr_tokens['clef'] is not None:
      flat_tokens.extend(attr_tokens['clef'])
    
    return flat_tokens
  
  
  def _emit(self, token:str, emit_type:str="token"):
    """Emits a token into the output sequence"""
    if emit_type == 'measure':
      self.measures.append((
        self._flatten_output_attr_tokens(self.output_attr_tokens),
        self.output_tokens
      ))
      self.output_attr_tokens = self._init_output_attr_tokens()
      self.output_tokens = []
    
    if self.fail_on_unknown_tokens:
      assert token in ALL_TOKENS, f"Token '{token}' not in the vocabulary"
    else:
      if token not in ALL_TOKENS:
        self._error(f"Token '{token}' not in the vocabulary")
        return
    
    if emit_type == 'token':
      self.output_tokens.append(token)
    elif emit_type == 'attr':
      if 'time' == token:
        self.output_attr_tokens['time'] = [token]
      elif token.startswith('beats:') or token.startswith('beat-type:'):
        self.output_attr_tokens['time'].append(token)
      elif token.startswith('clef:'):
        if self.output_attr_tokens['clef'] is None:
          self.output_attr_tokens['clef'] = []
        self.output_attr_tokens['clef'].append(token)
      else:
        self.output_attr_tokens[token.split(':')[0]] = token
    
    else:
      raise ValueError(f"Unknown emit type: {emit_type}")


  def process_part(self, part:ET.Element):
    # reset within-part state
    self._part_id = None
    self._measure_number = None
    self._divisions = None
    self._beats_per_measure = None
    self._beat_type = None
    self._measure_duration = None
    self._staves = None
    self._clefs = {}
    self._key_signature_fifths = None
    
    # check whether part is <part> element
    assert part.tag == "part"
    
    self._part_id = part.attrib.get("id")
    
    for measure in part:
      # ignore comments
      if measure.tag is ET.Comment:
        continue
      
      assert measure.tag == "measure"
      
      is_new_system = False
      
      # process print options
      if (print_opt:=measure.find('print')) is not None:
        if print_opt.attrib.get('new-system') == 'yes':
          self._emit("<new-system>")
          self._emit(None, emit_type='measure')
          is_new_system = True
        elif print_opt.attrib.get('new-page') == 'yes':
          self._emit("<new-page>")
          self._emit(None, emit_type='measure')
          is_new_system = True

      # fileter print-object:no elements
      for el in reversed(measure):
        if el.tag == 'note' and el.get('print-object') == 'no':
          measure.remove(el)
      
      self.process_measure(measure, is_new_system)
  
  
  def process_measure(self, measure:ET.Element, is_new_system:bool):
    assert measure.tag == "measure"

    # reset within-measure state
    self._stem_orientation = None
    self._staff = None
    self._onset = 0
    self._voice = None
    self._previous_note_duration = None
    self._previous_note_pitch = None

    self._measure_number = measure.attrib.get("number")
    
    # start a new measure
    # self._emit("measure")

    for element in measure:
      if element.tag in IGNORED_MEASURE_ELEMENTS:
        continue
      elif element.tag == "note":
        self.process_note(element, measure)
      elif element.tag == "attributes":
        self.process_attributes(element)
        
      # Do not process backup/forward in multi-part linearization
      
      else:
        self._error("Unexpected <measure> element:", element, element.attrib)
    
    if is_new_system and self._measure_number != "1":
      self._inject_attributes()
    
    self._emit(None, emit_type='measure')
  
  
  def process_time_signature(self, time: ET.Element):
    super().process_time_signature(time)
    # store the last three tokens (time, beats, beat-type)
    # for later use in multi-part linearization
    part_time_tokens = self.output_tokens[-3:]
    for t in part_time_tokens:
      self._emit(t, 'attr')
    
    # remove the last three tokens (time, beats, beat-type)
    self.output_tokens = self.output_tokens[:-3]  
  
  
  def process_key_signature(self, key: Optional[ET.Element]):
    if key is not None:
      self._key_signature_fifths = int(key.find("fifths").text)
      self._emit(
        "key:fifths:" + str(self._key_signature_fifths),
        'attr'
      )
  
  
  def process_clefs(self, clefs: List[ET.Element]):
    super().process_clefs(clefs)
    # store the clefs for later use in multi-part linearization
    # (they are printed in the same order as they are defined)
    num_clef_tokens = len(self._clefs.keys()) * (2 if self._staves is not None else 1)
    clef_tokens = self.output_tokens[-num_clef_tokens:]
    
    for t in clef_tokens:
      self._emit(t, 'attr')

    self.output_tokens = self.output_tokens[:-num_clef_tokens]
  
  
  def _inject_attributes(self):
    """Injects the last known attributes into the first measure of a new system"""
    if self.output_attr_tokens['key'] is None and self._key_signature_fifths is not None:
      self._emit(
        "key:fifths:" + str(self._key_signature_fifths),
        'attr'
      )
    
    if self.output_attr_tokens['clef'] is None:
      for staff_number in sorted(self._clefs.keys()):
        self._emit(self._clefs[staff_number], 'attr')
        if self._staves is not None:
          self._emit("staff:" + str(staff_number), 'attr')


class SQLinearizer():
  def __init__(self, errout:Optional[TextIO]=None, fail_on_unknown_tokens=False):
    self.linearizers = [
      SQPartLinearizer(errout, fail_on_unknown_tokens)
      for _ in range(4)
    ]

  
  def process_multi_parts(self, part_list: list[ET.Element]):
    lmx_parts = []
    
    for part, linearizer in zip(part_list, self.linearizers):
      linearizer.process_part(part)
      lmx_parts.append(linearizer.measures)
    
    return lmx_parts