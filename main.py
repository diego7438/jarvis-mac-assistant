import os
import subprocess
import schedule
import time
import json
from datetime import datetime
import sys
import threading
import logging
import socket # For network check
import requests # For fetching public IP

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = 'config.json'
PAUSE_FLAG = 'pause.flag'

def speak(message, voice=None):
    logging.debug(f"Attempting to speak: '{message}'")
    cmd = ["say"]
    if voice:
        cmd.extend(["-v", voice])
    cmd.append(message)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"speak command error: {result.stderr}")
    else:
        logging.debug(f"speak command success (returncode 0).")

def send_notification(title, message):
    logging.debug(f"Attempting to send notification: Title='{title}', Message='{message}'")
    result = subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ], capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"send_notification osascript error: {result.stderr}")
    else:
        logging.debug(f"send_notification osascript success.")

def show_initial_prompt():
    logging.debug("Showing initial prompt dialog.")
    # Display the dialog (this is blocking)
    subprocess.run([
        "osascript", "-e",
        'display dialog "Ready to proceed?" buttons {"Continue"} default button 1 with title "Jarvis"'
    ])

def ask_for_password():
    logging.debug("Asking for password...")
    result = subprocess.run([
        "osascript", "-e",
        'display dialog "Please enter the passphrase to continue:" default answer "" with hidden answer buttons {"Continue"} default button 1 with title "Jarvis"'
    ], capture_output=True, text=True)

    if result.returncode != 0:
        logging.error(f"ask_for_password osascript error: {result.stderr}")
        return False

    logging.debug(f"ask_for_password stdout: {result.stdout}")
    if "button returned:Continue" in result.stdout:
        answer_line = [line for line in result.stdout.splitlines() if "text returned:" in line]
        if answer_line:
            password = answer_line[0].split("text returned:")[-1].strip()
            logging.debug(f"Password entered: '{password}'")
            return password == "iron man"
    logging.debug("Password check failed or dialog cancelled.")
    return False

def play_bootup_sound(sound_path):
    if sound_path and os.path.exists(sound_path):
        subprocess.run(["afplay", sound_path])

def play_video_fullscreen(video_path, voice_for_errors=None):
    if not video_path or not os.path.exists(video_path):
        logging.warning(f"Video path not provided or video not found: {video_path}")
        return

    logging.debug(f"Attempting to play video: {video_path}")
    try:
        vlc_executable_path = "/Applications/VLC.app/Contents/MacOS/VLC"
        # Try with VLC for better fullscreen and play-and-exit behavior
        logging.debug("Trying to play with VLC...")
        subprocess.run([vlc_executable_path, "--fullscreen", "--play-and-exit", video_path], check=True)
        logging.debug(f"VLC playback finished (using {vlc_executable_path}).")
    except FileNotFoundError:
        logging.warning("VLC not found. Falling back to QuickTime Player.")
        speak("VLC media player not found. Opening with QuickTime. Please close QuickTime to continue.", voice=voice_for_errors)
        # -W waits for the application to quit. Fullscreen might need manual activation.
        subprocess.run(["open", "-W", "-a", "QuickTime Player", video_path])
        logging.debug("QuickTime Player closed by user.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error playing video with VLC: {e}")
        speak(f"Error playing video: {os.path.basename(video_path)}.", voice=voice_for_errors)

def open_apps_and_folders(config, sound_thread_to_start=None):
    apps_to_open = config.get('apps', [])
    arc_app = None
    if "Arc" in apps_to_open:
        apps_to_open.remove("Arc")
        arc_app = "Arc"

    # Ask to open general apps and folders
    general_folders = config.get('folders', [])
    if apps_to_open or general_folders: # Check if there are any general apps or folders
        logging.debug("Prompting to open general apps and folders...")
        prompt_message = "Open configured applications and folders (excluding Arc)?"
        buttons = '{"Open Apps", "Continue"}' # "Continue" implies continuing without opening these
        default_button = '"Open Apps"'

        dialog_script = f'display dialog "{prompt_message}" buttons {buttons} default button {default_button} with title "Jarvis"'
        result = subprocess.run(["osascript", "-e", dialog_script], capture_output=True, text=True)

        if result.returncode == 0 and "button returned:Open Apps" in result.stdout:
            logging.info("User chose to open general apps and folders.")
            if sound_thread_to_start and not sound_thread_to_start.is_alive():
                logging.debug("Starting sound thread after 'Open Apps' confirmation.")
                sound_thread_to_start.start()
            # Open non-Arc apps
            for app in apps_to_open:
                logging.debug(f"Opening app: {app}")
                subprocess.Popen(["open", "-a", app])
            # Open folders
            for folder in general_folders:
                logging.debug(f"Opening folder: {folder}")
                subprocess.Popen(["open", folder])
        else:
            logging.info("User chose to skip or cancelled opening general apps and folders.")
            # Start sound thread even if user skips opening general apps, but after their choice.
            if sound_thread_to_start and not sound_thread_to_start.is_alive():
                logging.debug("Starting sound thread after skipping/cancelling general apps.")
                sound_thread_to_start.start()
            speak("Okay, skipping general applications and folders.", voice=config.get('voice'))
            if result.returncode != 0:
                logging.error(f"Dialog error for general apps/folders: {result.stderr}")
    elif sound_thread_to_start and not sound_thread_to_start.is_alive(): # If no general apps/folders to ask about
        logging.debug("No general apps/folders to prompt for. Starting sound thread.")
        sound_thread_to_start.start()

    # Open Arc last if it was specified and confirmed
    if arc_app:
        logging.debug(f"Prompting to open Arc...")
        arc_result = subprocess.run([
            "osascript", "-e",
            f'display dialog "Open {arc_app}?" buttons {{"Continue", "Cancel"}} default button "Continue" with title "Jarvis"'
        ], capture_output=True, text=True)

        if arc_result.returncode != 0: # Corrected variable name here
            logging.error(f"Arc dialog osascript error: {arc_result.stderr}")
            # Decide how to handle this - perhaps assume cancel or try to speak an error
            speak(f"There was an error trying to ask about opening {arc_app}.", voice=config.get('voice'))
            return # Exit function if dialog failed

        logging.debug(f"Arc dialog stdout: {arc_result.stdout}")
        if "button returned:Continue" in arc_result.stdout:
            logging.debug(f"Opening Arc...")
            subprocess.Popen(["open", "-a", arc_app])
        else:
            logging.debug(f"User chose not to open Arc.")
            speak(f"Okay, I will not open {arc_app}.", voice=config.get('voice'))
        time.sleep(1) # Pause after Arc interaction


def hourly_checkin(config): # Pass config to access message and user_name
    if not os.path.exists(PAUSE_FLAG):
        user_name = config.get('user_name', 'sir') # Get user_name for the message
        default_message = f"Hi {user_name}, it’s Jarvis checking in. Never stop grinding."
        message_template = config.get('hourly_checkin_message', default_message)
        message = message_template.replace("{user_name}", user_name)
        send_notification("Jarvis", message)
    else:
        logging.info("Hourly check-in skipped due to PAUSE_FLAG.")

def load_config(config_path=CONFIG_FILE):
    with open(config_path, 'r') as f:
        return json.load(f)

def check_internet_connection(host="8.8.8.8", port=53, timeout=3):
    logging.debug(f"Checking internet connection to {host}:{port} with timeout {timeout}s.")
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        logging.info("Internet connection check: Succeeded.")
        return True
    except socket.error as ex:
        logging.warning(f"Internet connection check: Failed. Error: {ex}")
        return False

def main():
    logging.info("Main function started.")
    config = load_config()
    
    voice_to_use = config.get('voice')
    # Step 1: Show initial prompt
    show_initial_prompt()
    logging.info("Initial prompt dialog acknowledged.")
    time.sleep(1) # Pause after initial prompt
    
    # Step 2: Ask for password
    if not ask_for_password():
        speak("Incorrect passphrase. Unauthorized access attempt detected. Counter-measures initiated. We are coming for you.", voice=voice_to_use)
        time.sleep(3) # Dramatic pause
        sys.exit()
    logging.info("Password correct.")
    time.sleep(1) # Pause after password success

    # New: Network Connectivity Check (after successful password)
    logging.info("Performing network connectivity check...")
    if check_internet_connection():
        speak("Network status: Connected and secure.", voice=voice_to_use)
    else:
        speak("Network status: Warning, unable to verify a secure internet connection. Proceeding with caution.", voice=voice_to_use)
    time.sleep(1) # Pause after network check message


    # Step 3: Play startup video if configured
    video_path = config.get('startup_video_path')
    if video_path and os.path.exists(video_path):
        play_video_fullscreen(video_path, voice_to_use)
        time.sleep(1) # Pause after video playback

    # Step 4: Start Iron Man sound in a background thread
    logging.debug("Starting sound thread.")
    sound_thread = threading.Thread(target=play_bootup_sound, args=(config.get('sound'),))
    # Sound thread will be started within open_apps_and_folders

    # Step 4: Launch apps and folders at the same time
    logging.debug("Opening apps and folders...")
    open_apps_and_folders(config, sound_thread_to_start=sound_thread)
    logging.info("Finished opening apps and folders.")
    # A small pause is already added within open_apps_and_folders after Arc interaction if applicable

    # Step 6: Wait for sound to finish
    logging.debug("Waiting for sound thread to join...")
    sound_thread.join()
    logging.debug("Sound thread joined.")

    # Step 6: Final motivational greeting
    today = datetime.now()
    days_left = (datetime(today.year, 12, 31) - today).days
    user_name = config.get('user_name', 'sir') # Get user_name from config, default to 'sir'
    logging.debug(f"Speaking final greeting...")
    time.sleep(1) # Pause before final greeting
    speak(f"Welcome home {user_name}. There are {days_left} days left in the year. Another day, another opportunity.", voice=voice_to_use)
    
    # Offer to show user's public IP
    logging.debug("Asking user if they want to see their public IP.")
    ip_dialog_script = 'display dialog "Would you like to see your current public IP?" buttons {"Yes", "No"} default button "No" with title "Jarvis"'
    ip_result = subprocess.run(["osascript", "-e", ip_dialog_script], capture_output=True, text=True)

    if ip_result.returncode != 0:
        logging.error(f"IP address dialog osascript error: {ip_result.stderr}")
    elif "button returned:Yes" in ip_result.stdout:
        logging.info("User chose to see public IP.")
        try:
            ip_address = requests.get('https://api.ipify.org', timeout=10).text
            logging.debug(f"Fetched public IP: {ip_address}")
            send_notification("Your IP Address", ip_address)
            speak(f"Your public IP address is {ip_address}", voice=voice_to_use)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching IP address: {e}")
            speak("Sorry, I couldn't fetch your public IP address at the moment.", voice=voice_to_use)
    elif "button returned:No" in ip_result.stdout:
        logging.info("User chose not to see public IP.")
        speak("Okay, I will not show your IP address.", voice=voice_to_use)
    else:
        logging.info("User cancelled IP address dialog or unknown button.")

    # Step 8: Hourly notifications begin
    logging.info(f"Sending initial notification and scheduling hourly check-ins...")
    send_notification("Jarvis", "Notifications will appear here every hour.")
    schedule.every().hour.at(":00").do(hourly_checkin, config=config) # Pass config to hourly_checkin
    while True:
        schedule.run_pending()
        time.sleep(1)
    

if __name__ == "__main__":
    main()