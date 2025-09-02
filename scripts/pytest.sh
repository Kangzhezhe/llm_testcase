#!/bin/bash
pytest --import-mode=importlib -n 16 "$@"
