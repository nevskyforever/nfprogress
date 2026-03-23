#!/bin/bash
./build-mac-arm.sh &
./build-mac-intel.sh &
wait
echo "Обе сборки завершены!"