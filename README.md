# Jarvis Mac Assistant

A personalized macOS assistant to automate your startup sequence, provide timely notifications, and add a bit of flair to your daily routine. Inspired by J.A.R.V.I.S. from Iron Man.

**Created by Diego Anderson**, a high‑schooler with a deep passion for coding, automation, and ethical tech. Inspired by Iron Man’s J.A.R.V.I.S., this project reflects my drive to build systems that empower people while guarding their privacy.

## Features

### Network Info Feature
Optionally shows the user's current public IP address upon request—on‑demand and with explicit consent.

*   **Password Protected Startup:** Ensures only authorized access.
*   **Custom Startup Media:**
    *   Plays a configurable startup video (fullscreen with VLC, fallback to QuickTime).
    *   Plays a configurable bootup sound.
*   **Automated Application & Folder Launching:**
    *   Opens a list of user-defined applications.
    *   Opens a list of user-defined folders.
    *   Prompts for confirmation before opening general apps/folders.
    *   Separate, optional confirmation prompt for specific applications (e.g., Arc browser).
*   **Personalized Greetings & Information:**
    *   Spoken welcome message with the user's configured name.
    *   Displays the number of days left in the year.
*   **Hourly Check-in Notifications:**
    *   Sends a desktop notification every hour with a customizable message.
    *   Notifications can be paused by creating a `pause.flag` file in the script's directory.
*   **Configurable:** Most features are customizable via a `config.json` file, including user name, apps, folders, media paths, voice, and notification messages.
*   **Logging:** Provides detailed debug and informational logs.

## Requirements

*   macOS
*   Python 3.x
*   VLC Media Player (for optimal video playback). Make sure it's installed in `/Applications/VLC.app`. If it's elsewhere, you may need to adjust the path in `main.py`.

## Setup

1.  **Clone the repository (or download the files):**
    ```bash
    git clone https://github.com/diego7438/jarvis-mac-assistant.git
    cd jarvis-mac-assistant
    ```

2.  **Create your configuration file:**
    *   Copy the template:
        ```bash
        cp config.json.template config.json
        ```
    *   Edit `config.json` with your preferred settings:
        *   `user_name`: Your name or title for greetings.
        *   `apps`: A list of application names to open (e.g., `"Spotify"`, `"Visual Studio Code"`).
        *   `folders`: A list of absolute paths to folders you want to open.
        *   `sound`: Absolute path to your desired startup sound file (e.g., `.wav`, `.mp3`).
        *   `startup_video_path`: Absolute path to your desired startup video file.
        *   `voice`: (Optional) The name of a macOS voice to use for spoken messages (e.g., "Alex", "Daniel"). Leave as `null` for the default voice.
        *   `hourly_checkin_message`: The template for your hourly notification. Use `{user_name}` as a placeholder for your configured user name.

3.  **Ensure VLC is installed:**
    For the best experience with the startup video, install VLC from videolan.org and ensure it's in your `/Applications` folder.

## How to Run

Navigate to the project directory in your terminal and execute:

```bash
python3 main.py