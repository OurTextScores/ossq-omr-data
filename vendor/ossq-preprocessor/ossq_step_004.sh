export PYTHONPATH=.:$PYTHONPATH
BASE_DIR=
MULTI_PROCESS=1
VERIFY=1
# L_PATH=/path/to/task_list.txt
# L="--list-path ${L_PATH}"
L=""
#
# 
SYNTHETIC_SW_KRN_CONVERT=1
SCANNED_SW_KRN_CONVERT=1
# 
SYNTHETIC_SW_KRN_CONVERT_EKRN=1
SCANNED_SW_KRN_CONVERT_EKRN=1
#
SYNTHETIC_PW_KRN_CONVERT=1
SCANNED_PW_KRN_CONVERT=1
#
SYNTHETIC_PW_KRN_ALIGN=1
SCANNED_PW_KRN_ALIGN=1
#
echo ""
#
#
echo ""
if [ $SYNTHETIC_SW_KRN_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: KRN: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_musicxml_to_krn.py -d $BASE_DIR -t synthetic -v $VERIFY --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_KRN_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: KRN: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_musicxml_to_krn.py -d $BASE_DIR -t scanned -v $VERIFY --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SYNTHETIC_SW_KRN_CONVERT_EKRN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: KRN: CONVERTING TO EKRN"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_krn_to_ekrn.py -d $BASE_DIR -t synthetic -v $VERIFY --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_KRN_CONVERT_EKRN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: KRN: CONVERTING TO EKRN"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_krn_to_ekrn.py -d $BASE_DIR -t scanned -v $VERIFY --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_PW_KRN_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: KRN: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/split_krn_partwise.py -d $BASE_DIR -v $VERIFY -t synthetic --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_KRN_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: KRN: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/split_krn_partwise.py -d $BASE_DIR -v $VERIFY -t scanned --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
# 
if [ $SYNTHETIC_PW_KRN_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: KRN: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_parts_krn.py -d $BASE_DIR -v $VERIFY -t synthetic $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_KRN_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: KRN: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_parts_krn.py -d $BASE_DIR -v $VERIFY -t scanned $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#