export PYTHONPATH=.:$PYTHONPATH
BASE_DIR=
MULTI_PROCESS=1
VERIFY=1
# L_PATH=/path/to/task_list.txt
# L="--list-path ${L_PATH}"
L=""
# 
SYNTHETIC_SW_PLMXE=1
SCANNED_SW_PLMXE=1
# 
SYNTHETIC_SW_RLMXE=1
SCANNED_SW_RLMXE=1
# 
SYNTHETIC_PW_RLMXE=1
SCANNED_PW_RLMXE=1
#
#
if [ $SYNTHETIC_SW_PLMXE -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: LMXE: CONVERTING TO PLMXE"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_lmxe_to_variant.py -d $BASE_DIR -t synthetic --level systemwise --lmxe-variant plmxe --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_PLMXE -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: LMXE: CONVERTING TO PLMXE"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_lmxe_to_variant.py -d $BASE_DIR -t scanned --level systemwise --lmxe-variant plmxe --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_SW_RLMXE -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: LMXE: CONVERTING TO RLMXE"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_lmxe_to_variant.py -d $BASE_DIR -t synthetic --level systemwise --lmxe-variant rlmxe --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_RLMXE -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: LMXE: CONVERTING TO RLMXE"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_lmxe_to_variant.py -d $BASE_DIR -t scanned --level systemwise --lmxe-variant rlmxe --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_PW_RLMXE -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: LMXE: CONVERTING TO RLMXE"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_lmxe_to_variant.py -d $BASE_DIR -t synthetic --level partwise --lmxe-variant rlmxe --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_RLMXE -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: LMXE: CONVERTING TO RLMXE"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_lmxe_to_variant.py -d $BASE_DIR -t scanned --level partwise --lmxe-variant rlmxe --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi