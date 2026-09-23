export PYTHONPATH=.:$PYTHONPATH
BASE_DIR=
python3 ./omrdp/ossq/clean.py \
  -d $BASE_DIR \
  --path 'temp' \

  # --path 'lmxe/scanned/partwise' \
  # --path 'lmxe/synthtic/partwise' \
  # --path 'lmxe' \
  # --path 'musicxml' \
  # --path 'krn' \
  # --path 'abc' \
  # --path 'metadata' \
  # 
  # --path 'lmxe/unaligned' \
  # --path 'lmxe/synthetic/systemwise' \
  # --path 'lmxe/scanned/systemwise' \
  # --path 'lmxe/synthetic/partwise' \
  # --path 'lmxe/scanned/partwise' \
  #
  # --path 'musicxml/synthetic/systemwise' \
  # --path 'musicxml/scanned/systemwise' \
  # --path 'musicxml/synthetic/partwise' \
  # --path 'musicxml/scanned/partwise' \
  #
  # --path 'abc/synthetic/systemwise' \
  # --path 'abc/scanned/systemwise' \
  # --path 'abc/synthetic/partwise' \
  # --path 'abc/scanned/partwise' \
  #
  # --path 'images/synthetic/systemwise' \
  # --path 'images/scanned/systemwise' \
  # --path 'images/synthetic/partwise' \
  # --path 'images/scanned/partwise' \
  #
  # --path 'images/synthetic/original/ \
  # --path 'images/synthetic/original/*_yolo_bboxs.txt' \
  # --path 'images/synthetic/original/*_system_bboxs.txt' \
  # 
  # --path 'images/synthetic/cropped' \
  # --path 'images/synthetic/cropped/*_staff_heights.txt' \
  # 
  # --path 'images/synthetic/systemwise/' \
  # --path 'images/synthetic/systemwise/*_yolo_bboxs.txt' \
  # 
  # --path 'images/synthetic/partwise/' \
  # 
  # --path 'images/scanned/original/ \
  # --path 'images/scanned/original/*_yolo_bboxs.txt' \
  # --path 'images/scanned/original/*_system_bboxs.txt' \
  # 
  # --path 'images/scanned/cropped' \
  # --path 'images/scanned/cropped/*_staff_heights.txt' \
  # 
  # --path 'images/scanned/systemwise/' \
  # --path 'images/scanned/systemwise/*_yolo_bboxs.txt' \
  # 
  # --path 'images/scanned/partwise/' \
