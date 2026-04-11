#!/bin/bash

PYTHON=${PYTHON:-}
VENV_NAME=_swinydlvenv

error_exit(){
    echo "$1" 1>&2
    exit 1
}
error_clean_exit(){
    echo Try again later! Removing the virtual environment dir...
    [ -e $VENV_NAME ] && rm -r $VENV_NAME
    error_exit "$1" 1>&2
}

cd "`dirname \"$0\"`"  # go to the script directory

if [ -z "$PYTHON" ]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
    then
      PYTHON="$candidate"
      break
    fi
  done
fi

[ -n "$PYTHON" ] || error_exit "Python 3.11 or newer is required"
command -v "$PYTHON" >/dev/null 2>&1 || error_exit "Python 3.11+ is required but '$PYTHON' was not found"
"$PYTHON" - <<'PY' || error_exit "Python 3.11 or newer is required"
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
# Check if virtual environment had been created
if [ ! -d "$VENV_NAME" ]; then
  echo Creating python virtual environment in "$VENV_NAME/"...
  "$PYTHON" -m venv $VENV_NAME || error_exit "Failed to create virtual environment"
  source $VENV_NAME/bin/activate || error_exit "Failed to source virtual environment"
  echo Upgrading pip...
  python -m pip install --upgrade pip
  echo Installing swinydl in editable mode...
  python -m pip install -e . || error_clean_exit "Something went wrong while installing swinydl"
fi

source $VENV_NAME/bin/activate || error_exit "Failed to source virtual environment (try to delete '$VENV_NAME/' and re-run)"

python -m swinydl.main "$@"
