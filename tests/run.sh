#!/usr/bin/env bash

for file1 in test_main.py test_utils.py test_task.py test_luiti_ext.py
do
  echo "[test] $file1"
  python tests/$file1
done