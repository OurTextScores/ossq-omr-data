import argparse
from typing import Dict

from fractions import Fraction


KEY_TOKENS = [
  "key:fifths:-7", "key:fifths:-6", "key:fifths:-5", "key:fifths:-4",
  "key:fifths:-3", "key:fifths:-2", "key:fifths:-1",
  "key:fifths:0",
  "key:fifths:1", "key:fifths:2", "key:fifths:3", "key:fifths:4",
  "key:fifths:5", "key:fifths:6", "key:fifths:7",
]

BEATS_TOKENS = [
  "beats:1", "beats:2", "beats:3", "beats:4", "beats:5", "beats:6",
  "beats:7", "beats:8", "beats:9", "beats:10", "beats:11", "beats:12",
  "beats:13", "beats:14", "beats:15", "beats:16", "beats:17",
  "beats:3+4", 
]

BEAT_TYPE_TOKENS = [
  "beat-type:2",
  "beat-type:4",
  "beat-type:8",
  "beat-type:16",
  "beat-type:32",
]

TIME_SIGNATURE_TOKENS = [
  "time",
  *BEATS_TOKENS,
  *BEAT_TYPE_TOKENS
]

CLEF_TOKENS = [
  "clef:G1", "clef:G2", "clef:G3", "clef:G4", "clef:G5",
  "clef:C1", "clef:C2", "clef:C3", "clef:C4", "clef:C5",
  "clef:F1", "clef:F2", "clef:F3", "clef:F4", "clef:F5"
]

NOTE_TYPE_TOKENS = [
  # ORDER MATTERS! (is used)
  # (from shortest to longest duration, doubles with each)
  "1024th", "512th", "256th", "128th", "64th",
  "32nd", "16th", "eighth", "quarter", "half", "whole",
  "breve", "long", "maxima"
]

NOTE_TYPE_TO_QUARTER_MULTIPLE: Dict[str, Fraction] = {
  "1024th":  Fraction(1, 256),
  "512th":   Fraction(1, 128),
  "256th":   Fraction(1, 64),
  "128th":   Fraction(1, 32),
  "64th":    Fraction(1, 16),
  "32nd":    Fraction(1, 8),
  "16th":    Fraction(1, 4),
  "eighth":  Fraction(1, 2),
  "quarter": Fraction(1, 1), # one
  "half":    Fraction(2, 1),
  "whole":   Fraction(4, 1),
  "breve":   Fraction(8, 1),
  "long":    Fraction(16, 1),
  "maxima":  Fraction(32, 1),
}

assert set(NOTE_TYPE_TOKENS) == set(NOTE_TYPE_TO_QUARTER_MULTIPLE.keys())

PITCH_TOKENS = [
  # ORDER MATTERS! (is used)
  # (from lowest to highest pitch)
  "C0", "D0", "E0", "F0", "G0", "A0", "B0",
  "C1", "D1", "E1", "F1", "G1", "A1", "B1",
  "C2", "D2", "E2", "F2", "G2", "A2", "B2",
  "C3", "D3", "E3", "F3", "G3", "A3", "B3",
  "C4", "D4", "E4", "F4", "G4", "A4", "B4",
  "C5", "D5", "E5", "F5", "G5", "A5", "B5",
  "C6", "D6", "E6", "F6", "G6", "A6", "B6",
  "C7", "D7", "E7", "F7", "G7", "A7", "B7",
  "C8", "D8", "E8", "F8", "G8", "A8", "B8",
  "C9", "D9", "E9", "F9", "G9", "A9", "B9"
]

VOICE_TOKENS = [
  "voice:1", "voice:2", "voice:3", "voice:4",
  "voice:5", "voice:6", "voice:7", "voice:8",
  "voice:9", "voice:10", "voice:11", "voice:12", # organ 3-staff music
]

TIME_MODIFICATION_TOKENS = [
  '3in2', '6in4', '2in1', '2in3', '5in4', '7in8', '7in6',
  '9in8', '4in3', '7in4', '4in6', '13in8', '22in16', '10in4',
  '12in8', '9in4', '10in8', '18in4', '16in8', '15in8', '5in3',
  '11in8', '11in12', '5in2', '8in2', '4in2', '7in1', '35in16',
  '9in2', 
  # added for new grandstaff-lmx
  '15in12', '17in16', '15in10', '14in8', '28in16',
  # added for string quartet scores
  '8in10', '24in4', '12in5', '12in4', '33in8', '48in16',  
  '3in4', '5in6', '6in5', '7in16', '8in6', '8in12', '9in6', '11in6', '18in8', '19in16', 
]

ACCIDENTAL_TOKENS = [
  "sharp",
  "flat",
  "natural",
  "double-sharp",
  "flat-flat",
  "natural-sharp",
  "natural-flat"
]

STEM_TOKENS = [
  "stem:up", "stem:down", "stem:none"
]

STAFF_TOKENS = [
  "staff:1", "staff:2",
  "staff:3" # organ 3-staff music
]

BEAM_TOKENS = [
  "beam:begin",
  "beam:end",
  "beam:continue",
  "beam:forward-hook",
  "beam:backward-hook"
]

TREMOLO_MARKS_TOKENS = [
  "tremolo:1",
  "tremolo:2",
  "tremolo:3",
  "tremolo:4"
]

TREMOLO_TYPE_TOKENS = [
  "tremolo:single",
  "tremolo:start",
  "tremolo:stop",
  "tremolo:unmeasured"
]

TREMOLO_TOKENS = [
  *TREMOLO_TYPE_TOKENS,
  *TREMOLO_MARKS_TOKENS
]

EXTENDED_FLAVOR_TOKENS = [
  "slur:start",
  "slur:stop",
  "fermata",
  "arpeggiate",
  "staccato",
  "accent",
  "strong-accent",
  "tenuto",
  "trill-mark",
  *TREMOLO_TOKENS
]

NOTE_PREFIX_TOKENS = [
  "print-object:no",
  "grace", "grace:slash",
  "chord",
  *PITCH_TOKENS, "rest", "forward", "backup", # note kind
  *VOICE_TOKENS
]

NOTE_SUFFIX_TOKENS = [
  *TIME_MODIFICATION_TOKENS,
  "dot",
  *ACCIDENTAL_TOKENS,
  *STEM_TOKENS,
  *STAFF_TOKENS,
  *BEAM_TOKENS,
  "tied:start", "tied:stop",
  "tuplet:start", "tuplet:stop",

  *EXTENDED_FLAVOR_TOKENS
]

NOTE_ROOT_TOKENS = [
  *NOTE_TYPE_TOKENS,
  "rest:measure",
]

# added as LMXE specs
# for multi-part music (e.g. string quartet)
PART_TOKENS = [
  "part:1", "part:2", "part:3", "part:4",
  "part:5", "part:6", "part:7", "part:8",
  "part:9", "part:10", "part:11", "part:12",
]

# added as LMXE specs
SCORE_TYPE_TOKENS = [
  "single", "multi", "grandstaff", "mixed"
]

# added as LMXE specs
SPECIAL_TOKENS = [
  "<new-system>", "<new-page>"
]

# TOKENS IGNORED IN REDUCED LMXE
REDUCED_IGNORE_TOKENS = [
  *BEATS_TOKENS,
  *BEAT_TYPE_TOKENS
]

ALL_TOKENS = [
  "measure",
  
  # attributes tokens
  *KEY_TOKENS,
  *TIME_SIGNATURE_TOKENS,
  *CLEF_TOKENS,
  
  # note tokens
  *NOTE_PREFIX_TOKENS,
  *NOTE_ROOT_TOKENS, # ROOT of a note
  *NOTE_SUFFIX_TOKENS,
  
  # added as LMXE specs
  *PART_TOKENS,
  *SCORE_TYPE_TOKENS,
  *SPECIAL_TOKENS,
]

def print_vocabulary(file=None):
  print(
    "\n".join(ALL_TOKENS),
    file=file
  )


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    prog='Linearized MusicXML Extended vocabulary',
    description='Prints the vocabulary of the Linearized MusicXML Extended.',
  )
  
  parser.add_argument(
    '--out-path', '-o',
    dest='outpath',
    type=str,
    default='vocabulary.txt',
    help='Path to the output file where the vocabulary will be written.'
  )
  
  args = parser.parse_args()
  
  print("Writing vocabulary to", args.outpath)
  
  with open(args.outpath, "w") as f:
    print_vocabulary(file=f)