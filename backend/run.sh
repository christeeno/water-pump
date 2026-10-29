#!/bin/bash
if [ -d "backend" ]; then
    cd backend
fi
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
