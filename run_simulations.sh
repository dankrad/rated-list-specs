#!/bin/bash

python3 -m venv venv
./venv/bin/activate
cd simulator
pip3 install -r requirements.txt

for i in $(seq 1 10);
do
    python3 . $i
done
