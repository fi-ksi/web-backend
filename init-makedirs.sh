#/bin/bash
# This script makes filesystem structure necessarry for ksi-backend
# to work. It is intended to be run at (and only at) initialization on
# a new server. However, if you run this script on running server,
# it just does nothing.

# Do not forget to checkout repository 'seminar' into data/seminar (write access required).
# Do not forget to checkout repository 'module_lib' into data/module_lib (read access in enough).

cd "$(dirname "$(realpath "$0")")" || { echo "ERR: Cannot cd to script dir"; exit 1; }

echo -n "[*] Making data directories..."
mkdir -p data/code_executions
mkdir -p data/content/achievements data/content/articles
mkdir -p data/images
mkdir -p data/modules
mkdir -p data/seminar
mkdir -p data/submissions
mkdir -p data/task-content
echo " done"
