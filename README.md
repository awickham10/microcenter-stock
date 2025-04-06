# Microcenter Stock Checker

A reliable stock monitoring system for Microcenter products with push and email notifications.

## Features

- Real-time stock monitoring for Microcenter products
- Push notifications via Pushover
- Email notifications (Gmail SMTP)
- Configurable polling interval
- Store-specific monitoring
- Graceful shutdown handling
- Service health monitoring with heartbeat notifications
- Comprehensive test suite
- Systemd service support

## Requirements

- Python 3.10+
- Chrome/Chromium (for web scraping)
- Pushover account (optional, for push notifications)
- Gmail account (optional, for email notifications)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/awickham10/microcenter-stock.git
cd microcenter-stock
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example config and edit with your settings:
```bash
cp config.env.example config.env
# Edit config.env with your settings
```

## Configuration

Edit `config.env` with your settings:

```env
# Microcenter settings
PRODUCT_URL=https://www.microcenter.com/product/your-product-url
STORE_COOKIE_NAME=storeSelected
STORE_COOKIE_VALUE=051  # Your store ID

# Email settings
EMAIL_USER=your@email.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com

# Pushover settings
PUSHOVER_TOKEN=your-pushover-token
PUSHOVER_USER=your-pushover-user

# Polling interval in seconds
POLL_INTERVAL=5

# Logging
LOG_FILE=/var/log/microcenter.log
LOG_LEVEL=INFO
```

## Running the Service

### Manual Run

```bash
python stock_checker.py
```

### Install as System Service

```bash
# Copy service file
sudo cp microcenter-stock.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/microcenter
sudo chown $USER:$USER /var/log/microcenter

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable microcenter-stock
sudo systemctl start microcenter-stock
```

### Check Service Status

```bash
sudo systemctl status microcenter-stock
```

## Testing

Run the test suite:

```bash
python -m pytest -v
```

## Notifications

The system sends notifications for:
- Service startup/shutdown
- Product availability
- Service health (daily heartbeat)
- Error conditions
- Consecutive failures

## Development

### Project Structure

```
microcenter-stock/
├── README.md               # Project documentation
├── requirements.txt        # Python dependencies
├── config.env             # Configuration file
├── stock_checker.py       # Main script
├── microcenter-stock.service     # Systemd service file
├── pytest.ini            # Test configuration
└── tests/                # Test directory
    ├── __init__.py
    ├── test_stock_checker.py
    └── test_notifications_integration.py
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_stock_checker.py
```

## Security

### Email Configuration
For Gmail, use an App Password instead of your account password:
1. Go to your Google Account settings
2. Navigate to Security > 2-Step Verification > App passwords
3. Create a new app password for this application
4. Use this password in your `config.env`

### Credential Safety
- Never commit your `config.env` file to version control
- Keep your Pushover tokens private
- Store logs in a directory with appropriate permissions
- Use environment variables in production environments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments

This project was inspired by [StockSmart](https://github.com/ayoTyler/StockSmart) by Tyler (@ayoTyler). His original implementation provided valuable insights into Microcenter stock monitoring. If you find his work helpful, consider [buying him a coffee](https://buymeacoffee.com/ayotyler)!

If you find this fork useful in your projects, you can also [buy me a coffee](https://buymeacoffee.com/awickham10) - though I'd encourage supporting the original author first! 😊
