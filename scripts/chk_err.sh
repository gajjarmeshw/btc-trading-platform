#!/bin/bash
echo "=== SYSTEMD STATUS ==="
sudo systemctl status btc-bot --no-pager

echo -e "\n=== JOURNALCTL (Last 20 lines) ==="
journalctl -u btc-bot -n 20 --no-pager

echo -e "\n=== STDERR LOG (data/service_error.log) ==="
if [ -f data/service_error.log ]; then
    tail -n 20 data/service_error.log
else
    echo "No service_error.log found."
fi

echo -e "\n=== APP LOG (trading.log) ==="
tail -n 20 trading.log
