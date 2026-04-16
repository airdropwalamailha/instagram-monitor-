import os
import time
import json
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pushbullet import Pushbullet

# ─────────────────────────────────────────
# SETTINGS — GitHub Secrets se aate hain
# ─────────────────────────────────────────
INSTAGRAM_USERNAME = os.environ["IG_USERNAME"]
INSTAGRAM_PASSWORD = os.environ["IG_PASSWORD"]
PUSHBULLET_API_KEY = os.environ["PB_API_KEY"]

# Kitne minutes ke andar aai post "new" mani jaye
NEW_POST_MINUTES = 10

# Monitor karne wale accounts (apne add karo)
TARGET_ACCOUNTS = [
    "rf_short_tv",
    "shabnamlayek2003",
    "noorkhan_shorts",
    # ... baaki accounts yahan add karo
]

# ─────────────────────────────────────────
# PUSHBULLET NOTIFICATION
# ─────────────────────────────────────────
def send_notification(title, body):
    try:
        pb = Pushbullet(PUSHBULLET_API_KEY)
        pb.push_note(title, body)
        print(f"[NOTIFY] {title}: {body}")
    except Exception as e:
        print(f"[ERROR] Pushbullet: {e}")

# ─────────────────────────────────────────
# CHROME DRIVER SETUP
# ─────────────────────────────────────────
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    return driver

# ─────────────────────────────────────────
# INSTAGRAM LOGIN
# ─────────────────────────────────────────
def instagram_login(driver):
    print("[INFO] Instagram login ho raha hai...")
    driver.get("https://www.instagram.com/accounts/login/")
    wait = WebDriverWait(driver, 15)

    # Username field
    username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
    username_field.clear()
    username_field.send_keys(INSTAGRAM_USERNAME)

    # Password field
    password_field = driver.find_element(By.NAME, "password")
    password_field.clear()
    password_field.send_keys(INSTAGRAM_PASSWORD)

    # Login button
    login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_btn.click()

    time.sleep(5)

    # "Save Info" popup dismiss
    try:
        not_now = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now' or text()='Not now']"))
        )
        not_now.click()
        time.sleep(2)
    except:
        pass

    # Notifications popup dismiss
    try:
        not_now2 = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now' or text()='Not now']"))
        )
        not_now2.click()
        time.sleep(2)
    except:
        pass

    print("[INFO] Login successful!")

# ─────────────────────────────────────────
# LATEST POST CHECK
# ─────────────────────────────────────────
def check_latest_post(driver, username):
    try:
        driver.get(f"https://www.instagram.com/{username}/")
        wait = WebDriverWait(driver, 10)

        # Pehli post ka link lo
        first_post = wait.until(
            EC.presence_of_element_located((By.XPATH, "//article//a[contains(@href, '/p/')]"))
        )
        post_url = first_post.get_attribute("href")

        # Post open karo
        driver.get(post_url)
        time.sleep(2)

        # Time tag dhundo
        time_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//time[@datetime]"))
        )
        post_time_str = time_element.get_attribute("datetime")
        post_time = datetime.fromisoformat(post_time_str.replace("Z", "+00:00"))

        now = datetime.now(timezone.utc)
        diff_minutes = (now - post_time).total_seconds() / 60

        print(f"[CHECK] @{username} — last post {diff_minutes:.1f} min pehle")

        if diff_minutes <= NEW_POST_MINUTES:
            # Check karo video hai ya nahi
            is_video = False
            try:
                driver.find_element(By.XPATH, "//video")
                is_video = True
            except:
                pass

            content_type = "🎬 Video" if is_video else "🖼️ Post"
            return {
                "new": True,
                "url": post_url,
                "minutes_ago": round(diff_minutes, 1),
                "type": content_type
            }

        return {"new": False}

    except Exception as e:
        print(f"[ERROR] @{username}: {e}")
        return {"new": False, "error": str(e)}

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"Monitor start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total accounts: {len(TARGET_ACCOUNTS)}")
    print(f"{'='*50}\n")

    driver = get_driver()
    new_posts_found = 0

    try:
        instagram_login(driver)

        for username in TARGET_ACCOUNTS:
            result = check_latest_post(driver, username)

            if result.get("new"):
                new_posts_found += 1
                send_notification(
                    f"📱 Instagram: @{username}",
                    f"{result['type']} — {result['minutes_ago']} min pehle\n{result['url']}"
                )
                time.sleep(1)  # Pushbullet rate limit

            time.sleep(3)  # Accounts ke beech delay

    finally:
        driver.quit()

    print(f"\n[DONE] {new_posts_found} new posts mili. Script complete.")

if __name__ == "__main__":
    main()
