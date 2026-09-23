export PYTHONPATH=.:$PYTHONPATH
BASE_DIR=
MULTI_PROCESS=1
VERIFY=1
# L_PATH=/path/to/task_list.txt
# L="--list-path ${L_PATH}"
L=""
#
# 
SYNTHETIC_SW_ABC_CONVERT=1
SCANNED_SW_ABC_CONVERT=1
#
SYNTHETIC_SW_ABC_CLEAN=1
SCANNED_SW_ABC_CLEAN=1
#
SYNTHETIC_SW_ABC_CONVERT_EABC=1
SCANNED_SW_ABC_CONVERT_EABC=1
#
SYNTHETIC_PW_ABC_CONVERT=1
SCANNED_PW_ABC_CONVERT=1
#
SYNTHETIC_PW_ABC_CLEAN=1
SCANNED_PW_ABC_CLEAN=1
#
SYNTHETIC_PW_ABC_ALIGN=1
SCANNED_PW_ABC_ALIGN=1
#
SYNTHETIC_PW_ABC_CONVERT_EABC=1
SCANNED_PW_ABC_CONVERT_EABC=1
#
echo ""
#
#
echo ""
if [ $SYNTHETIC_SW_ABC_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: ABC: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_musicxml_to_abc.py -d $BASE_DIR -t synthetic -v $VERIFY --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_ABC_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: ABC: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_musicxml_to_abc.py -d $BASE_DIR -t scanned -v $VERIFY --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_SW_ABC_CLEAN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: ABC: CLEANING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/clean_abc.py -d $BASE_DIR -t synthetic --level systemwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_ABC_CLEAN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: ABC: CLEANING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/clean_abc.py -d $BASE_DIR -t scanned --level systemwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_SW_ABC_CONVERT_EABC -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: SW: ABC: CONVERTING TO EABC"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_abc_to_eabc.py -d $BASE_DIR -t synthetic --level systemwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_SW_ABC_CONVERT_EABC -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: SW: ABC: CONVERTING TO EABC"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_abc_to_eabc.py -d $BASE_DIR -t scanned --level systemwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_PW_ABC_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: ABC: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/split_abc_partwise.py -d $BASE_DIR -v $VERIFY -t synthetic --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_ABC_CONVERT -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: ABC: CONVERTING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/split_abc_partwise.py -d $BASE_DIR -v $VERIFY -t scanned --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
# 
if [ $SYNTHETIC_PW_ABC_CLEAN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: ABC: CLEANING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/clean_abc.py -d $BASE_DIR -t synthetic --level partwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_ABC_CLEAN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: ABC: CLEANING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/clean_abc.py -d $BASE_DIR -t scanned --level partwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_PW_ABC_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: ABC: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_parts_abc.py -d $BASE_DIR -v $VERIFY -t synthetic $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_ABC_ALIGN -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: ABC: ALIGNING"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/align_parts_abc.py -d $BASE_DIR -v $VERIFY -t scanned $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
#
if [ $SYNTHETIC_PW_ABC_CONVERT_EABC -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SYNTHETIC: PW: ABC: CONVERTING TO EABC"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_abc_to_eabc.py -d $BASE_DIR -t synthetic --level partwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#
if [ $SCANNED_PW_ABC_CONVERT_EABC -eq 1 ]; then
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "SCANNED: PW: ABC: CONVERTING TO EABC"
  echo "-------------------------------------------"
  python3 ./omrdp/ossq/convert_abc_to_eabc.py -d $BASE_DIR -t scanned --level partwise --multi-process $MULTI_PROCESS $L
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo ""
fi
#