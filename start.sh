#!/bin/bash
export PYTHONDONTWRITEBYTECODE=1
source ~/code/python/bard/.venv/bin/activate
python3 manage.py scheduler &
python3 manage.py serve -r
