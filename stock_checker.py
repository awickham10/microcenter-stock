#!/usr/bin/env python3
# Standard library imports
import logging
import os
import signal
import smtplib
import sys
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Third-party imports
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- Load configuration ---
load_dotenv("config.env")

PRODUCT_URL = os.getenv("PRODUCT_URL")
STORE_COOKIE_NAME = os.getenv("STORE_COOKIE_NAME")
STORE_COOKIE_VALUE = os.getenv("STORE_COOKIE_VALUE")
POLL_INTERVAL = os.getenv("POLL_INTERVAL", "60")  # Changed to string
MAX_RETRIES = os.getenv("MAX_RETRIES", "3")  # Changed to string
HEARTBEAT_HOURS = os.getenv("HEARTBEAT_HOURS", "24")  # Changed to string

# Convert to int after getting string values
POLL_INTERVAL = int(POLL_INTERVAL)
MAX_RETRIES = int(MAX_RETRIES)
HEARTBEAT_HOURS = int(HEARTBEAT_HOURS)

# Email
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENTS = [e.strip() for e in os.getenv("EMAIL_RECIPIENTS", "").split(",") if e.strip()]

# Pushover
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")

# Logging
LOG_FILE = os.getenv("LOG_FILE", "stocksmart.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Global state
running = True
consecutive_failures = 0
last_heartbeat = None

# --- Configure logging ---
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Signal handling ---
def handle_shutdown(_signum, _frame):
    """Handle graceful shutdown on SIGINT/SIGTERM."""
    global running  # pylint: disable=global-statement
    logging.info("Received signal %s, initiating graceful shutdown...", _signum)
    send_push(
        "Microcenter Stock Checker service is shutting down gracefully.\n"
        "Monitoring will stop after current check completes.",
        "Service Stopping",
        PRODUCT_URL
    )
    send_email(
        "Microcenter Stock Checker Service Stopping",
        "The Microcenter Stock Checker service is being shut down gracefully.\n"
        "Monitoring will stop after the current check completes.",
        PRODUCT_URL
    )
    running = False

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# --- Notification functions ---
def send_push(message: str, title: str = "Stock Alert", url: str = None):
    """Send a push notification via Pushover."""
    # Re-read environment variables each time
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")
    
    if not token or not user:
        logging.warning("Pushover credentials missing, skipping push")
        return

    payload = {
        "token": token,
        "user": user,
        "message": message,
        "title": title
    }
    if url:
        payload["url"] = url
        payload["url_title"] = "View Product"
    
    try:
        r = requests.post(
            "https://api.pushover.net/1/messages.json",
            data=payload,
            timeout=5
        )
        r.raise_for_status()
        logging.info("Pushover notification sent")
    except requests.RequestException as e:
        logging.error("Pushover error: %s", str(e))


def send_email(subject: str, body: str, url: str = None):
    """Send an email notification."""
    # Re-read environment variables each time
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_recipients = [
        e.strip() for e in os.getenv("EMAIL_RECIPIENTS", "").split(",")
        if e.strip()
    ]
    
    if not all([email_user, email_password, email_recipients]):
        logging.warning("Email settings incomplete, skipping email")
        return

    # Add URL to body if provided
    if url:
        body = f"{body}\n\nProduct URL: {url}"

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = ", ".join(email_recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_user, email_password)
            server.sendmail(email_user, email_recipients, msg.as_string())
            logging.info("Email notification sent")
    except (smtplib.SMTPException, OSError) as e:
        logging.error("Email error: %s", str(e))

# --- Stock checking ---
def set_store_cookie(driver):
    """Set the store cookie for location-specific stock checking."""
    driver.get("https://www.microcenter.com")
    time.sleep(1)
    driver.add_cookie({
        'name': STORE_COOKIE_NAME,
        'value': STORE_COOKIE_VALUE,
        'domain': '.microcenter.com',
        'path': '/',
        'secure': True,
        'httpOnly': False
    })
    driver.get(PRODUCT_URL)
    time.sleep(1)

def send_heartbeat():
    """Send a heartbeat notification to confirm service is still running."""
    global last_heartbeat  # pylint: disable=global-statement
    
    uptime = datetime.now() - last_heartbeat if last_heartbeat else timedelta(0)
    message = (
        f"Microcenter Stock Checker service is running normally.\n"
        f"Uptime: {uptime.days} days, {uptime.seconds//3600} hours\n"
        f"Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    send_push(message, "Service Heartbeat", PRODUCT_URL)
    send_email("Microcenter Stock Checker Service Heartbeat", message, PRODUCT_URL)
    last_heartbeat = datetime.now()

def check_stock():
    """Check if the product is in stock and handle notifications."""
    global consecutive_failures  # pylint: disable=global-statement
    
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    try:
        set_store_cookie(driver)
        page = driver.page_source
        
        if "'inStock':'True'" in page:
            consecutive_failures = 0
            logging.info("Status: In Stock!")
            send_push(
                "Product is in stock! Click to view the product page.",
                "In Stock",
                PRODUCT_URL
            )
            send_email(
                "Product In Stock",
                "Your product is now available! Click the link below to view the product page.",
                PRODUCT_URL
            )
            return True
        
        if "'inStock':'False'" in page:
            consecutive_failures = 0
            logging.info("Status: Out of Stock")
            return False
            
        consecutive_failures += 1
        logging.warning("Status: Unknown (Failure #%d)", consecutive_failures)
        if consecutive_failures >= MAX_RETRIES:
            error_msg = (
                f"Stock check returned unknown status {consecutive_failures} times in a row.\n"
                "Click to verify manually."
            )
            send_push(error_msg, "Checker Error", PRODUCT_URL)
            send_email(
                "Stock Checker Error",
                f"Unknown stock status detected {consecutive_failures} times in a row.\n"
                "Please verify manually using the link below.",
                PRODUCT_URL
            )
            
    except (WebDriverException, TimeoutError) as e:
        consecutive_failures += 1
        logging.error("Checker exception: %s (Failure #%d)", str(e), consecutive_failures)
        if consecutive_failures >= MAX_RETRIES:
            error_msg = (
                f"Checker failed {consecutive_failures} times in a row: {e}\n"
                "Click to check manually."
            )
            send_push(error_msg, "Checker Exception", PRODUCT_URL)
            send_email(
                "Stock Checker Exception",
                f"The stock checker encountered {consecutive_failures} consecutive errors:\n{e}\n\n"
                "Please check manually using the link below.",
                PRODUCT_URL
            )
    finally:
        driver.quit()
    
    return False

def main():
    """Main program loop."""
    global last_heartbeat  # pylint: disable=global-statement
    
    logging.info("Starting Microcenter Stock Checker loop")
    start_time = datetime.now()
    last_heartbeat = start_time
    
    # Test notifications on startup
    send_push(
        "Microcenter Stock Checker service has started successfully.\n"
        "Click to view the monitored product.",
        "Service Started",
        PRODUCT_URL
    )
    send_email(
        "Microcenter Stock Checker Service Started",
        "The Microcenter Stock Checker service has started successfully.\n"
        "Monitoring the following product:",
        PRODUCT_URL
    )
    
    try:
        while running:
            if check_stock():
                break
                
            # Send heartbeat if it's time
            if datetime.now() - last_heartbeat > timedelta(hours=HEARTBEAT_HOURS):
                send_heartbeat()
                
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, stopping...")
    finally:
        logging.info("Microcenter Stock Checker stopped")
        send_push(
            "Microcenter Stock Checker service has stopped.\n"
            "Monitoring is no longer active.",
            "Service Stopped",
            PRODUCT_URL
        )
        send_email(
            "Microcenter Stock Checker Service Stopped",
            "The Microcenter Stock Checker service has stopped.\n"
            "Monitoring is no longer active.",
            PRODUCT_URL
        )

if __name__ == "__main__":
    main()
