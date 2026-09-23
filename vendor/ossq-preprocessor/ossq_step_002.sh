export PYTHONPATH=.:$PYTHONPATH
BASE_DIR=
MULTI_PROCESS=1
VERIFY=1
# L_PATH=/path/to/task_list.txt
# L="--list-path ${L_PATH}"
L=""
# 
SYNTHETIC_SW_LMXE_ALIGN=1
SCANNED_SW_LMXE_ALIGN=1
# 
SYNTHETIC_PW_LMXE_CONVERT=1
SCANNED_PW_LMXE_CONVERT=1
#
SYNTHETIC_PW_LMXE_ALIGN=1
SCANNED_PW_LMXE_ALIGN=1
#
echo ""
#
if [ $SYNTHETIC_SW_LMXE_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: LMXE: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_systems_lmxe.py -d $BASE_DIR -t synthetic $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_LMXE_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: LMXE: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_systems_lmxe.py -d $BASE_DIR -t scanned $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SYNTHETIC_PW_LMXE_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: LMXE: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/split_lmxe_partwise.py -d $BASE_DIR -v $VERIFY -t synthetic --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_LMXE_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: LMXE: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/split_lmxe_partwise.py -d $BASE_DIR -v $VERIFY -t scanned --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
# 
if [ $SYNTHETIC_PW_LMXE_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: LMXE: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_parts_lmxe.py -d $BASE_DIR -v $VERIFY -t synthetic $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_LMXE_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: LMXE: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_parts_lmxe.py -d $BASE_DIR -v $VERIFY -t scanned $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi