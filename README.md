# NVDA Stock Ticker Service

Monitors NVDA stock price every minute during NASDAQ trading hours (9:30–16:00 ET, weekdays).
Prints current price and delta each minute. Prints an end-of-day summary at market close.

## Requirements

- systemd
- python

## Installation

Clone the repo and navigate to the directory then run the install script:

```bash
git clone https://github.com/AmpJee/nvda-ticker.git
cd nvda-ticker
./install.sh
```

## Usage

View live logs:

```bash
journalctl -u nvda-ticker -f
```

Check service status:

```bash
sudo systemctl status nvda-ticker
```

Stop / restart:

```bash
sudo systemctl stop nvda-ticker
sudo systemctl restart nvda-ticker
```

## Uninstall

```bash
sudo systemctl disable --now nvda-ticker
sudo rm /etc/systemd/system/nvda-ticker.service
sudo rm -rf /opt/nvda_ticker
sudo systemctl daemon-reload
```

## Sample Output

```
[2067-03-09 10:30:05 ET] NVDA: $0.32  (+0.14)
[2067-03-09 10:31:05 ET] NVDA: $0.10  (+0.22)
[2067-03-09 10:32:05 ET] NVDA: $0.88  (-0.76)
=== NVDA End of Day [2067-03-09] ===
  Open:   $0.50
  Close:  $0.88
  Low:    $0.10
  High:   $0.88
  Change: +$0.38 (+70.00%)
```

## How Restart Resilience Works

State is written to state.json after every price update using an atomic write , so a mid-write crash never corrupts the file. On restart, if the stored date matches today, open price and running min/max are restored keeping the EOD summary accurate no matter how many times the service restarts. If the service comes back after 16:00 ET with the summary still unprinted, it prints immediately rather than waiting for the next day.
