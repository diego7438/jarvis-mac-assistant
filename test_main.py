import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import os
import sys
from datetime import datetime

# Assuming test_main.py is in the same directory as main.py
# If main.py is in a different location relative to this test file,
# sys.path might need adjustment.
import main as jarvis_main

class TestJarvisAssistant(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open, read_data='{"greeting": "Test"}')
    @patch('json.load')
    def test_load_config(self, mock_json_load, mock_file_open):
        original_config_file = jarvis_main.CONFIG_FILE
        jarvis_main.CONFIG_FILE = 'test_config.json'
        expected_config = {"greeting": "Test"}
        mock_json_load.return_value = expected_config

        config = jarvis_main.load_config()

        mock_file_open.assert_called_once_with('test_config.json', 'r')
        mock_json_load.assert_called_once_with(mock_file_open())
        self.assertEqual(config, expected_config)
        jarvis_main.CONFIG_FILE = original_config_file # Restore

    @patch('subprocess.run')
    def test_speak(self, mock_subprocess_run):
        message = "Hello Jarvis"
        jarvis_main.speak(message)
        mock_subprocess_run.assert_called_once_with(["say", message])

    @patch('subprocess.run')
    def test_send_notification(self, mock_subprocess_run):
        title = "Notification Title"
        message = "Notification Message"
        jarvis_main.send_notification(title, message)
        expected_script = f'display notification "{message}" with title "{title}"'
        mock_subprocess_run.assert_called_once_with(["osascript", "-e", expected_script])

    @patch('subprocess.run')
    def test_show_welcome_popup(self, mock_subprocess_run):
        jarvis_main.show_welcome_popup()
        expected_script = 'display dialog "Welcome home, sir." buttons {"Continue"} default button 1 with title "Jarvis"'
        mock_subprocess_run.assert_called_once_with(["osascript", "-e", expected_script])

    @patch('subprocess.run')
    def test_ask_for_password_correct(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "button returned:Continue\ntext returned:iron man"
        mock_subprocess_run.return_value = mock_result
        self.assertTrue(jarvis_main.ask_for_password())
        expected_script = 'display dialog "Please enter the passphrase to continue:" default answer "" with hidden answer buttons {"Continue"} default button 1 with title "Jarvis"'
        mock_subprocess_run.assert_called_once_with(["osascript", "-e", expected_script], capture_output=True, text=True)

    @patch('subprocess.run')
    def test_ask_for_password_incorrect(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "button returned:Continue\ntext returned:wrong"
        mock_subprocess_run.return_value = mock_result
        self.assertFalse(jarvis_main.ask_for_password())

    @patch('subprocess.run')
    def test_ask_for_password_cancel(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "button returned:Cancel"
        mock_subprocess_run.return_value = mock_result
        self.assertFalse(jarvis_main.ask_for_password())

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    def test_play_bootup_sound_exists(self, mock_subprocess_run, mock_os_path_exists):
        sound_path = "/path/to/sound.wav"
        jarvis_main.play_bootup_sound(sound_path)
        mock_os_path_exists.assert_called_once_with(sound_path)
        mock_subprocess_run.assert_called_once_with(["afplay", sound_path])

    @patch('os.path.exists', return_value=False)
    @patch('subprocess.run')
    def test_play_bootup_sound_not_exists(self, mock_subprocess_run, mock_os_path_exists):
        sound_path = "/path/to/nonexistent.wav"
        jarvis_main.play_bootup_sound(sound_path)
        mock_os_path_exists.assert_called_once_with(sound_path)
        mock_subprocess_run.assert_not_called()

    @patch('subprocess.Popen')
    @patch('subprocess.run') # For Arc confirmation dialog
    @patch('main.speak')    # To check if speak is called on Arc cancel
    def test_open_apps_and_folders_with_arc_confirm(self, mock_speak, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Arc", "Spotify", "Notion"],
            "folders": ["/Users/test/Desktop"]
        }
        mock_dialog_result = MagicMock()
        mock_dialog_result.stdout = "button returned:Continue"
        mock_subprocess_run_dialog.return_value = mock_dialog_result

        jarvis_main.open_apps_and_folders(config)

        # Check Arc dialog call
        expected_arc_dialog_script = 'display dialog "Open Arc?" buttons {"Continue", "Cancel"} default button "Continue" with title "Jarvis"'
        mock_subprocess_run_dialog.assert_called_once_with(
            ["osascript", "-e", expected_arc_dialog_script], capture_output=True, text=True
        )

        # Check Popen calls
        popen_calls = mock_subprocess_popen.call_args_list
        self.assertEqual(len(popen_calls), 4) # Spotify, Notion, Folder, Arc

        expected_calls_before_arc = [
            call(["open", "-a", "Spotify"]),
            call(["open", "-a", "Notion"]),
            call(["open", "/Users/test/Desktop"]),
        ]
        # Check that non-Arc apps and folders are opened
        for expected_call in expected_calls_before_arc:
            self.assertIn(expected_call, popen_calls)

        # Check that Arc is opened last
        self.assertEqual(popen_calls[-1], call(["open", "-a", "Arc"]))
        mock_speak.assert_not_called()

    @patch('subprocess.Popen')
    @patch('subprocess.run') # For Arc confirmation dialog
    @patch('main.speak')    # To check if speak is called on Arc cancel
    def test_open_apps_and_folders_with_arc_cancel(self, mock_speak, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Arc", "Spotify"],
            "folders": []
        }
        mock_dialog_result = MagicMock()
        mock_dialog_result.stdout = "button returned:Cancel"
        mock_subprocess_run_dialog.return_value = mock_dialog_result

        jarvis_main.open_apps_and_folders(config)

        # Check Arc dialog call
        expected_arc_dialog_script = 'display dialog "Open Arc?" buttons {"Continue", "Cancel"} default button "Continue" with title "Jarvis"'
        mock_subprocess_run_dialog.assert_called_once_with(
            ["osascript", "-e", expected_arc_dialog_script], capture_output=True, text=True
        )

        # Check Popen calls (only Spotify should be opened)
        mock_subprocess_popen.assert_called_once_with(["open", "-a", "Spotify"])
        mock_speak.assert_called_once_with("Okay, I will not open Arc.")

    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_open_apps_and_folders_no_arc(self, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Spotify", "Notion"],
            "folders": ["/Users/test/Documents"]
        }
        jarvis_main.open_apps_and_folders(config)

        expected_popen_calls = [
            call(["open", "-a", "Spotify"]),
            call(["open", "-a", "Notion"]),
            call(["open", "/Users/test/Documents"]),
        ]
        mock_subprocess_popen.assert_has_calls(expected_popen_calls, any_order=True) # Order of non-Arc apps/folders can vary
        self.assertEqual(mock_subprocess_popen.call_count, 3)
        mock_subprocess_run_dialog.assert_not_called() # Arc dialog should not appear

    @patch('os.path.exists', return_value=False) # PAUSE_FLAG does not exist
    @patch('main.send_notification')
    def test_hourly_checkin_no_pause(self, mock_send_notification, mock_os_path_exists):
        jarvis_main.hourly_checkin()
        mock_os_path_exists.assert_called_once_with(jarvis_main.PAUSE_FLAG)
        mock_send_notification.assert_called_once_with("Jarvis", "Hi Diego, it’s Jarvis checking in. Never stop grinding.")

    @patch('os.path.exists', return_value=True) # PAUSE_FLAG exists
    @patch('main.send_notification')
    def test_hourly_checkin_with_pause(self, mock_send_notification, mock_os_path_exists):
        jarvis_main.hourly_checkin()
        mock_os_path_exists.assert_called_once_with(jarvis_main.PAUSE_FLAG)
        mock_send_notification.assert_not_called()

    @patch('main.load_config')
    @patch('main.show_welcome_popup')
    @patch('main.ask_for_password')
    @patch('threading.Thread')
    @patch('main.open_apps_and_folders')
    @patch('main.speak')
    @patch('main.send_notification')
    @patch('schedule.every')
    @patch('time.sleep')
    @patch('sys.exit') # To prevent test runner from exiting if main calls it
    def test_main_flow_access_granted(self, mock_sys_exit, mock_time_sleep, mock_schedule_every,
                                      mock_send_notification_main, mock_speak_main, mock_open_apps,
                                      mock_thread_class, mock_ask_password, mock_show_welcome,
                                      mock_load_config):
        # --- Setup Mocks ---
        mock_config_data = {
            "sound": "boot.wav",
            "apps": ["TestApp"],
            "folders": ["/test/folder"],
            "greeting": "Welcome, Test User." # This specific greeting isn't used by main's speak
        }
        mock_load_config.return_value = mock_config_data
        mock_ask_password.return_value = True  # Access granted

        # Mock threading.Thread
        mock_thread_instance = MagicMock()
        mock_thread_class.return_value = mock_thread_instance

        # Mock schedule to prevent actual scheduling
        mock_job = MagicMock()
        mock_schedule_every.return_value.hour.return_value.at.return_value.do.return_value = mock_job

        # Make time.sleep raise an exception to break the while loop in main() after one pass
        mock_time_sleep.side_effect = InterruptedError("Break main loop for test")

        # --- Run main ---
        with self.assertRaises(InterruptedError): # Expect main to break due to time.sleep mock
            jarvis_main.main()

        # --- Assertions ---
        mock_load_config.assert_called_once()
        mock_show_welcome.assert_called_once()
        mock_ask_password.assert_called_once()

        # Thread for sound
        mock_thread_class.assert_called_once_with(target=jarvis_main.play_bootup_sound, args=(mock_config_data.get('sound'),))
        mock_thread_instance.start.assert_called_once()

        mock_open_apps.assert_called_once_with(mock_config_data)
        mock_thread_instance.join.assert_called_once() # Sound thread joined

        # Final speak call
        # Get the actual datetime object that would have been used
        today = datetime.now()
        days_left = (datetime(today.year, 12, 31) - today).days
        expected_speak_message = f"Welcome home, Diego Stark. There are {days_left} days left in the year. Let’s get it."
        mock_speak_main.assert_called_with(expected_speak_message)

        mock_send_notification_main.assert_called_once_with("Jarvis", "Notifications will appear here every hour.")
        mock_schedule_every.return_value.hour.return_value.at.return_value.do.assert_called_once_with(jarvis_main.hourly_checkin)
        mock_sys_exit.assert_not_called() # Should not exit if access granted

    @patch('main.load_config')
    @patch('main.show_welcome_popup')
    @patch('main.ask_for_password')
    @patch('main.speak')
    @patch('sys.exit')
    # Add other mocks for functions called before sys.exit to ensure they are not called if not expected
    @patch('threading.Thread')
    @patch('main.open_apps_and_folders')
    def test_main_flow_access_denied(self, mock_open_apps, mock_thread_class,
                                     mock_sys_exit, mock_speak_main, mock_ask_password,
                                     mock_show_welcome, mock_load_config):
        mock_load_config.return_value = {} # Minimal config
        mock_ask_password.return_value = False # Access denied

        # Call main
        jarvis_main.main()

        # Assertions
        mock_load_config.assert_called_once()
        mock_show_welcome.assert_called_once()
        mock_ask_password.assert_called_once()
        mock_speak_main.assert_called_once_with("Access denied. Terminating session.")
        mock_sys_exit.assert_called_once_with()

        # Ensure later parts of main are not called
        mock_thread_class.assert_not_called()
        mock_open_apps.assert_not_called()

if __name__ == '__main__':
    unittest.main()