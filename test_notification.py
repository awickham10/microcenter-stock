#!/usr/bin/env python3
# Standard library imports
import os

# Third-party imports
from dotenv import load_dotenv

# Local imports
from stock_checker import send_push, send_email

# Set log file to local path before importing stock_checker
os.environ["LOG_FILE"] = "stocksmart_test.log"

def main():
    """Test the notification functionality."""
    # Load environment variables
    load_dotenv("config.env")
    
    # Send test notifications
    print("Sending test notifications...")
    
    # Pushover notification
    send_push(
        "This is a test notification from Microcenter Stock Checker!\n\n"
        "If you received this, your Pushover notifications are working correctly.",
        "Test Notification",
        "https://www.microcenter.com"
    )
    
    # Email notification
    send_email(
        "🔔 Microcenter Stock Checker Test Notification",
        "This is a test notification from Microcenter Stock Checker!\n\n"
        "If you received this email, your email notifications are working correctly.\n\n"
        "When a product becomes available, you'll receive a notification like this one.",
        "https://www.microcenter.com"
    )
    
    print("Test notifications sent! Please check your devices for the notifications.")

if __name__ == "__main__":
    main() 
