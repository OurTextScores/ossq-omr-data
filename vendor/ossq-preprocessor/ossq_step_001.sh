export PYTHONPATH=.:$PYTHONPATH
BASE_DIR=
MULTI_PROCESS=1
REPRODUCE=1
VERIFY=0
# L_PATH=/path/to/task_list.txt
# L="--list-path ${L_PATH}"
L=""
# 
CONVERT_MUSESCORE_TO_MUSICXML=1
CLEAN_MUSICXML=1
# 
CONVERT_MUSICXML_TO_LMXE=1
#
SYNTHETIC_SW_CONVERT_PDF=1
SYNTHETIC_SW_CROPPING=1
SYNTHETIC_SW_RESIZING=1
SYNTHETIC_PW_CROPPING=1
SYNTHETIC_SW_CROPPING_CONFIDENCE=0.45
SYNTHETIC_PW_CROPPING_CONFIDENCE=0.7
#
SCANNED_SW_CONVERT_PDF=1
SCANNED_SW_CROPPING=1
SCANNED_SW_RESIZING=1
SCANNED_PW_CROPPING=1
SCANNED_SW_CROPPING_CONFIDENCE=0.30
SCANNED_PW_CROPPING_CONFIDENCE=0.7
#
if [ $CONVERT_MUSESCORE_TO_MUSICXML -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "MUSICXML: MUSESCORE TO MUSICXML"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_musescore_to_musicxml.py -d $BASE_DIR --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
if [ $CLEAN_MUSICXML -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "MUSICXML: CLEANING MUSICXML"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/clean_musicxml.py -d $BASE_DIR -v $VERIFY --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
if [ $CONVERT_MUSICXML_TO_LMXE -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "LMXE: SYSTEMWISE"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_musicxml_to_lmxe.py -d $BASE_DIR -v $VERIFY --remove-stem-direction 1 --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
T=synthetic
if [ $SYNTHETIC_SW_CONVERT_PDF -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: CONVERTING PDF"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_musescore_to_pdf.py -d $BASE_DIR -t $T $L
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_pdf_to_images.py -d $BASE_DIR -t $T $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo""
fi
if [ $SYNTHETIC_SW_CROPPING -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: CROPPING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_detect_systems.py -d $BASE_DIR -t $T -n 32 --device 'cuda:0' --reproduce $REPRODUCE $L
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_crop_systems.py -d $BASE_DIR -t $T -v $VERIFY --confidence-threshold $SYNTHETIC_SW_CROPPING_CONFIDENCE --merge-threshold 0.7 --reproduce $REPRODUCE $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
if [ $SYNTHETIC_SW_RESIZING -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: RESIZING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_detect_staff_heights.py -d $BASE_DIR -t $T -n 64 --device 'cuda:0' -v $VERIFY --reproduce $REPRODUCE $L
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_resize_systems.py -d $BASE_DIR -t $T --target_height 18 --reproduce $REPRODUCE $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
if [ $SYNTHETIC_PW_CROPPING -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: CROPPING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_detect_staves.py -d $BASE_DIR -t $T -n 64 --device 'cuda:0' --reproduce $REPRODUCE $L
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_crop_staves.py -d $BASE_DIR -t $T --confidence-threshold $SYNTHETIC_PW_CROPPING_CONFIDENCE --merge-threshold 0.7 --reproduce $REPRODUCE $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
# 
T=scanned
if [ $SCANNED_SW_CONVERT_PDF -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: CONVERTING PDF"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_pdf_to_images.py -d $BASE_DIR -t $T $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
if [ $SCANNED_SW_CROPPING -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: CROPPING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_detect_systems.py -d $BASE_DIR -t $T -n 32 --device 'cuda:1' --reproduce $REPRODUCE $L
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_crop_systems.py -d $BASE_DIR -t $T --confidence-threshold $SCANNED_SW_CROPPING_CONFIDENCE --merge-threshold 0.7 -v $VERIFY --reproduce $REPRODUCE $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
if [ $SCANNED_SW_RESIZING -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: RESIZING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_detect_staff_heights.py -d $BASE_DIR -t $T -n 64 --device 'cuda:1' -v $VERIFY --reproduce $REPRODUCE $L
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_resize_systems.py -d $BASE_DIR -t $T --target_height 18 --reproduce $REPRODUCE $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
if [ $SCANNED_PW_CROPPING -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: CROPPING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_detect_staves.py -d $BASE_DIR -t $T -n 64 --device 'cuda:1' --reproduce $REPRODUCE $L
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/yolo_crop_staves.py -d $BASE_DIR -t $T --confidence-threshold $SCANNED_PW_CROPPING_CONFIDENCE --merge-threshold 0.7 --reproduce $REPRODUCE $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
