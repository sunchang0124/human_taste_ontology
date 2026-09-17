#!/usr/bin/env bash
# Downloads the ROBOT jar. Idempotent.
set -euo pipefail
mkdir -p bin
if [ ! -f bin/robot.jar ]; then
  curl -sL -o bin/robot.jar \
    https://github.com/ontodev/robot/releases/latest/download/robot.jar
fi
java -jar bin/robot.jar --version
