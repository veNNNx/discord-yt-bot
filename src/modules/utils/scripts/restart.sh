#!/bin/bash

echo "Restarting bot..."

APP_DIR="/usr/src/app"

pkill -f "python $APP_DIR/main.py"

nohup python "$APP_DIR/main.py" > "$APP_DIR/bot.log" 2>&1 &