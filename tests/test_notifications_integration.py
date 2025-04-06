import stock_checker

def test_real_send_push():
    """
    Sends a real Pushover notification.
    You should receive a push titled 'Integration Test' with the message.
    """
    stock_checker.send_push(
        "Integration test: Microcenter Stock Checker is working! 🚀",
        "Integration Test",
        "https://www.microcenter.com"
    )


def test_real_send_email():
    """
    Sends a real email notification.
    You should receive an email titled 'Integration Test Email'.
    """
    stock_checker.send_email(
        "Integration Test Email",
        "If you receive this, email integration works!"
    )
