# Standard library imports
import signal
import smtplib
from datetime import datetime, timedelta

# Third-party imports
import pytest
import requests

# Local imports
import stock_checker

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("PUSHOVER_TOKEN", "test_token")
    monkeypatch.setenv("PUSHOVER_USER", "test_user")
    monkeypatch.setenv("EMAIL_USER", "a@b.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "pw")
    monkeypatch.setenv("EMAIL_RECIPIENTS", "c@d.com,e@f.com")
    monkeypatch.setenv("LOG_FILE", "/tmp/stocksmart_test.log")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MAX_RETRIES", "3")
    monkeypatch.setenv("HEARTBEAT_HOURS", "24")
    yield

# --- Pushover tests ---
def test_send_push_success(monkeypatch):
    """Test successful push notification."""
    calls = {}
    def fake_post(url, data, timeout):
        calls['url'] = url
        calls['data'] = data
        calls['timeout'] = timeout
        
        class Resp:
            def raise_for_status(self):
                """Stub for response."""
                return
        
        return Resp()
    
    monkeypatch.setattr(requests, "post", fake_post)
    stock_checker.send_push("Test message", "Test title", "http://test.url")
    assert calls['url'] == "https://api.pushover.net/1/messages.json"
    assert calls['data']['message'] == "Test message"
    assert calls['data']['title'] == "Test title"
    assert calls['data']['url'] == "http://test.url"
    assert calls['data']['url_title'] == "View Product"


def test_send_push_missing_credentials(caplog, monkeypatch):
    """Test push notification with missing credentials."""
    monkeypatch.setenv("PUSHOVER_TOKEN", "")
    monkeypatch.setenv("PUSHOVER_USER", "")
    stock_checker.send_push("msg", "title", "http://test.url")
    assert "Pushover credentials missing" in caplog.text

# --- Email tests ---
class FakeSMTP:
    """Mock SMTP class for testing."""
    def __init__(self, _host, _port):
        self.tls = False
        self.login_info = None
        self.sent = None
        self.message = None
    
    def starttls(self):
        """Enable TLS."""
        self.tls = True
    
    def login(self, user, pwd):
        """Store login credentials."""
        self.login_info = (user, pwd)
    
    def sendmail(self, frm, to, msg):
        """Store sent message details."""
        self.sent = (frm, to)
        self.message = msg
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc, tb):
        """Context manager exit."""
        return


def test_send_email_success(monkeypatch):
    """Test successful email sending."""
    smtp = FakeSMTP(None, None)
    def fake_smtp(_host, _port):
        return smtp
    
    monkeypatch.setattr(smtplib, "SMTP", fake_smtp)
    test_url = "http://test.url"
    stock_checker.send_email("subj", "body", test_url)
    assert smtp.tls
    assert smtp.login_info == ("a@b.com", "pw")
    assert smtp.sent == ("a@b.com", ["c@d.com", "e@f.com"])
    assert test_url in smtp.message


def test_send_email_incomplete(caplog, monkeypatch):
    """Test email sending with incomplete settings."""
    monkeypatch.setenv("EMAIL_USER", "")
    stock_checker.send_email("s", "b", "http://test.url")
    assert "Email settings incomplete" in caplog.text

# --- Heartbeat tests ---
def test_heartbeat_notification(monkeypatch):
    """Test heartbeat notification functionality."""
    calls = []
    def mock_send_push(msg, title=None, url=None):
        calls.append(("push", msg, title, url))
    
    def mock_send_email(subj, body, url=None):
        calls.append(("email", subj, body, url))
    
    monkeypatch.setattr(stock_checker, "send_push", mock_send_push)
    monkeypatch.setattr(stock_checker, "send_email", mock_send_email)
    
    # Set last_heartbeat to 25 hours ago
    stock_checker.last_heartbeat = datetime.now() - timedelta(hours=25)
    stock_checker.send_heartbeat()
    
    # Verify heartbeat notifications
    heartbeat_push = next(c for c in calls if c[0] == "push" and "Service Heartbeat" == c[2])
    assert "running normally" in heartbeat_push[1]
    assert "Uptime:" in heartbeat_push[1]
    assert "Last check:" in heartbeat_push[1]
    
    heartbeat_email = next(c for c in calls if c[0] == "email" and "Heartbeat" in c[1])
    assert "running normally" in heartbeat_email[2]
    assert "Uptime:" in heartbeat_email[2]
    assert "Last check:" in heartbeat_email[2]

# --- Consecutive failure tests ---
def test_consecutive_failures(monkeypatch):
    """Test handling of consecutive failures."""
    calls = []
    def mock_send_push(msg, title=None, url=None):
        calls.append(("push", msg, title, url))
    
    def mock_send_email(subj, body, url=None):
        calls.append(("email", subj, body, url))
    
    monkeypatch.setattr(stock_checker, "send_push", mock_send_push)
    monkeypatch.setattr(stock_checker, "send_email", mock_send_email)
    
    # Mock Chrome driver
    class FakeDriver:
        """Mock Chrome driver for testing."""
        def __init__(self):
            """Initialize with empty page source."""
            self.page_source = ""
        
        def get(self, _url):
            """Mock get method."""
            return
        
        def add_cookie(self, _cookie):
            """Mock add_cookie method."""
            return
        
        def quit(self):
            """Mock quit method."""
            return
    
    def fake_chrome(*_args, **_kwargs):
        """Create mock Chrome driver."""
        return FakeDriver()
    
    monkeypatch.setattr(stock_checker.webdriver, "Chrome", fake_chrome)
    
    # Run check_stock multiple times to trigger failure notifications
    for _ in range(4):  # One more than MAX_RETRIES
        stock_checker.check_stock()
    
    # Verify failure notifications
    failure_push = next(c for c in calls if c[0] == "push" and "Checker Error" in str(c[2]))
    assert "3 times in a row" in failure_push[1]
    
    failure_email = next(c for c in calls if c[0] == "email" and "Error" in str(c[1]))
    assert "3 times in a row" in failure_email[2]

# --- Shutdown notification tests ---
def test_graceful_shutdown(monkeypatch):
    """Test graceful shutdown handling."""
    calls = []
    def mock_send_push(msg, title=None, url=None):
        calls.append(("push", msg, title, url))
    
    def mock_send_email(subj, body, url=None):
        calls.append(("email", subj, body, url))
    
    monkeypatch.setattr(stock_checker, "send_push", mock_send_push)
    monkeypatch.setattr(stock_checker, "send_email", mock_send_email)
    
    # Simulate SIGTERM
    stock_checker.handle_shutdown(signal.SIGTERM, None)
    
    # Verify shutdown notifications
    shutdown_push = next(c for c in calls if c[0] == "push" and "Service Stopping" in str(c[2]))
    assert "shutting down" in shutdown_push[1].lower() or "stopping" in shutdown_push[1].lower()
    
    shutdown_email = next(c for c in calls if c[0] == "email" and "Stopping" in str(c[1]))
    assert "shut down" in shutdown_email[2].lower() or "stopping" in shutdown_email[2].lower()
    
    # Verify running flag is set to False
    assert not stock_checker.running

# --- Startup notifications test ---
def test_main_startup_notifications(monkeypatch):
    """Test startup notification handling."""
    calls = []
    def mock_send_push(msg, title=None, url=None):
        calls.append(("push", msg, title, url))
    
    def mock_send_email(subj, body, url=None):
        calls.append(("email", subj, body, url))
    
    # Mock check_stock to return True immediately
    monkeypatch.setattr(stock_checker, "send_push", mock_send_push)
    monkeypatch.setattr(stock_checker, "send_email", mock_send_email)
    monkeypatch.setattr(stock_checker, "check_stock", lambda: True)
    
    stock_checker.main()
    
    # Verify startup notifications
    startup_push = next(c for c in calls if c[0] == "push" and "started" in c[1].lower())
    assert startup_push[3] == stock_checker.PRODUCT_URL
    
    startup_email = next(c for c in calls if c[0] == "email" and "started" in c[1].lower())
    assert startup_email[3] == stock_checker.PRODUCT_URL
    
    # Verify stop notifications
    stop_push = next(c for c in calls if c[0] == "push" and "stopped" in c[1].lower())
    assert "no longer active" in stop_push[1].lower()
    
    stop_email = next(c for c in calls if c[0] == "email" and "stopped" in c[1].lower())
    assert "no longer active" in stop_email[2].lower()
    
    # Verify total number of notifications (2 start + 2 stop = 4)
    assert len(calls) == 4
