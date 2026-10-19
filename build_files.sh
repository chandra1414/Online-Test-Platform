#!/bin/bash
echo "===> Installing project dependencies..."
if command -v uv &> /dev/null; then
    uv pip install -r requirements.txt --system
else
    python3 -m pip install -r requirements.txt --break-system-packages 2>/dev/null || python3 -m pip install -r requirements.txt
fi

echo "===> Collecting static files..."
python3 manage.py collectstatic --noinput --clear || python manage.py collectstatic --noinput --clear
echo "===> Build completed successfully!"
