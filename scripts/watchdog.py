import time
import subprocess
import requests
import logging

# Simple Watchdog
# Checks if the Bot Container is healthy (using Docker inspect)
# If not, restarts it.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONTAINER_NAME = "org_bot"

def check_health():
    try:
        # Check if container is running
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logging.error(f"Failed to inspect container: {result.stderr}")
            return False

        is_running = result.stdout.strip() == "true"
        return is_running
    except Exception as e:
        logging.error(f"Healthcheck exception: {e}")
        return False

def restart_bot():
    logging.warning("⚠️ Bot is unhealthy! Restarting...")
    subprocess.run(["docker", "restart", CONTAINER_NAME])

def main():
    logging.info("🐶 Watchdog started.")
    while True:
        if not check_health():
            restart_bot()
        else:
            logging.debug("Bot is healthy.")

        time.sleep(60)

if __name__ == "__main__":
    main()
