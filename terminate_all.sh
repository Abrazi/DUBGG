#!/bin/bash

# terminate_all.sh - Clean up backend and frontend processes for DUBGG

echo "Stopping DUBGG project processes..."

# 1. Kill by Ports (standard for FastAPI and Vite)
echo "Cleaning up ports 8000 (Backend) and 5173 (Frontend)..."
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null

# 2. Kill by Process Names (redundancy)
echo "Hunting for python and vite processes..."
pkill -f "python api_server.py"
pkill -f "python app_server.py"
pkill -f "vite"
pkill -f "node.*vite"

# 3. Kill any leftover Modbus server processes if child processes were spawned
# (though they should be daemon threads, pkill is safer)
pkill -f "generator_sim.py"

echo "Cleanup complete. You can now start fresh."
