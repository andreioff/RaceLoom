#!/bin/bash
SCRIPT_PATH=$(dirname $(realpath -s $0))

if $($SCRIPT_PATH/katch.sh run $SCRIPT_PATH/tutorial.nkpl > /dev/null); then
  rm -r $SCRIPT_PATH/results/*
  echo "OK!"
else
  echo $res
  echo "==================="
  echo "Failed with errors!"
fi
