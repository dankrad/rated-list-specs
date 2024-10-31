#!/bin/bash

cd simulator

for i in $(seq 1 1000); do
  python3 . $i
done
