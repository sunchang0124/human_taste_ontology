#!/usr/bin/env bash
# Downloads the ROBOT jar. Idempotent.
#
# Pinned to an exact release: `latest` made the build depend on whatever
# ontodev happened to have released that day, so two checkouts of the same
# commit could produce different ontologies.
set -euo pipefail

ROBOT_VERSION="1.9.10"

mkdir -p bin
if [ ! -f bin/robot.jar ]; then
  curl -fsSL -o bin/robot.jar \
    "https://github.com/ontodev/robot/releases/download/v${ROBOT_VERSION}/robot.jar"
fi

installed="$(java -jar bin/robot.jar --version)"
echo "$installed"
case "$installed" in
  *"$ROBOT_VERSION"*) ;;
  *) echo "error: expected ROBOT $ROBOT_VERSION, found: $installed" >&2
     echo "       delete bin/robot.jar and rerun to fetch the pinned release." >&2
     exit 1 ;;
esac
