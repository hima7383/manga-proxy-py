from playwright.__main__ import main as playwright_install
import os

if __name__ == "__main__":
    # Force install in user-writable location
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    playwright_install(["install", "chromium"])
    playwright_install(["install-deps"])