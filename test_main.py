import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import os
import sys
from datetime import datetime
import socket # For mocking network check

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
    def test_show_initial_prompt(self, mock_subprocess_run): # Renamed function
        jarvis_main.show_initial_prompt()
        expected_script = 'display dialog "Ready to proceed?" buttons {"Continue"} default button 1 with title "Jarvis"'
        mock_subprocess_run.assert_called_once_with(["osascript", "-e", expected_script])

    @patch('subprocess.run')
    def test_ask_for_password_correct(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "button returned:Continue\ntext returned:iron man"
        mock_subprocess_run.return_value = mock_result
        self.assertTrue(jarvis_main.ask_for_password())
        expected_script = 'display dialog "Please enter the passphrase to continue:" default answer "" with hidden answer buttons {"Continue"} default button 1 with title "Jarvis"' # Script is the same
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
    @patch('main.speak')
    @patch('threading.Thread') # Mock the sound thread
    def test_open_apps_and_folders_with_arc_confirm(self, mock_thread_class, mock_speak, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Arc", "Spotify", "Notion"],
            "folders": ["/Users/test/Desktop"],
            "voice": "Alex"
        }
        # Mock for the general apps/folders dialog
        mock_general_dialog_result = MagicMock(stdout="button returned:Open Apps", returncode=0)
        # Mock for the Arc dialog
        mock_arc_dialog_result = MagicMock(stdout="button returned:Continue", returncode=0)
        mock_subprocess_run_dialog.side_effect = [mock_general_dialog_result, mock_arc_dialog_result]

        mock_sound_thread = MagicMock()
        mock_thread_class.return_value = mock_sound_thread

        jarvis_main.open_apps_and_folders(config, sound_thread_to_start=mock_sound_thread)

        # Check Arc dialog call
        expected_arc_dialog_script = 'display dialog "Open Arc?" buttons {"Continue", "Cancel"} default button "Continue" with title "Jarvis"'
        # Check general apps dialog call first
        expected_general_dialog_script = 'display dialog "Open configured applications and folders (excluding Arc)?" buttons {"Open Apps", "Continue"} default button "Open Apps" with title "Jarvis"'

        self.assertEqual(mock_subprocess_run_dialog.call_count, 2)
        mock_subprocess_run_dialog.assert_any_call(
            ["osascript", "-e", expected_general_dialog_script], capture_output=True, text=True
        )
        mock_subprocess_run_dialog.assert_any_call(
            ["osascript", "-e", expected_arc_dialog_script], capture_output=True, text=True
        )

        # Check Popen calls
        # Order of Spotify, Notion, Folder can vary, Arc is last
        expected_popen_calls = [
            call(["open", "-a", "Spotify"]),
            call(["open", "-a", "Notion"]),
            call(["open", "/Users/test/Desktop"]),
            call(["open", "-a", "Arc"])
        ]
        mock_subprocess_popen.assert_has_calls(expected_popen_calls, any_order=False) # Arc must be last of these
        self.assertEqual(mock_subprocess_popen.call_count, 4)

        mock_speak.assert_not_called()
        mock_sound_thread.start.assert_called_once()

    @patch('subprocess.Popen')
    @patch('subprocess.run') # For Arc confirmation dialog
    @patch('main.speak')
    @patch('threading.Thread')
    def test_open_apps_and_folders_with_arc_cancel(self, mock_thread_class, mock_speak, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Arc", "Spotify"],
            "folders": [],
            "voice": "Alex"
        }
        # Mock for the general apps/folders dialog
        mock_general_dialog_result = MagicMock(stdout="button returned:Open Apps", returncode=0)
        # Mock for the Arc dialog
        mock_arc_dialog_result = MagicMock(stdout="button returned:Cancel", returncode=0)
        mock_subprocess_run_dialog.side_effect = [mock_general_dialog_result, mock_arc_dialog_result]

        mock_sound_thread = MagicMock()
        mock_thread_class.return_value = mock_sound_thread

        jarvis_main.open_apps_and_folders(config, sound_thread_to_start=mock_sound_thread)

        # Check Arc dialog call
        expected_arc_dialog_script = 'display dialog "Open Arc?" buttons {"Continue", "Cancel"} default button "Continue" with title "Jarvis"'
        mock_subprocess_run_dialog.assert_any_call(
            ["osascript", "-e", expected_arc_dialog_script], capture_output=True, text=True
        )

        # Check Popen calls (only Spotify should be opened)
        mock_subprocess_popen.assert_called_once_with(["open", "-a", "Spotify"])
        mock_speak.assert_called_once_with("Okay, I will not open Arc.", voice="Alex")
        mock_sound_thread.start.assert_called_once()

    @patch('subprocess.Popen')
    @patch('subprocess.run')
    @patch('threading.Thread')
    def test_open_apps_and_folders_no_arc(self, mock_thread_class, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Spotify", "Notion"],
            "folders": ["/Users/test/Documents"],
            "voice": "Alex"
        }
        # Mock for the general apps/folders dialog
        mock_general_dialog_result = MagicMock(stdout="button returned:Open Apps", returncode=0)
        mock_subprocess_run_dialog.return_value = mock_general_dialog_result

        mock_sound_thread = MagicMock()
        mock_thread_class.return_value = mock_sound_thread

        jarvis_main.open_apps_and_folders(config, sound_thread_to_start=mock_sound_thread)

        expected_popen_calls = [
            call(["open", "-a", "Spotify"]),
            call(["open", "-a", "Notion"]),
            call(["open", "/Users/test/Documents"]),
        ]
        mock_subprocess_popen.assert_has_calls(expected_popen_calls, any_order=True) # Order of non-Arc apps/folders can vary
        self.assertEqual(mock_subprocess_popen.call_count, 3)
        # General dialog should be called, Arc dialog should not
        expected_general_dialog_script = 'display dialog "Open configured applications and folders (excluding Arc)?" buttons {"Open Apps", "Continue"} default button "Open Apps" with title "Jarvis"'
        mock_subprocess_run_dialog.assert_called_once_with(
            ["osascript", "-e", expected_general_dialog_script], capture_output=True, text=True
        )
        mock_sound_thread.start.assert_called_once()

    @patch('os.path.exists', return_value=False) # PAUSE_FLAG does not exist
    @patch('main.send_notification')
    def test_hourly_checkin_no_pause(self, mock_send_notification, mock_os_path_exists):
        config = {"user_name": "TestUser", "hourly_checkin_message": "Hi {user_name}, check in!"}
        jarvis_main.hourly_checkin(config)
        mock_os_path_exists.assert_called_once_with(jarvis_main.PAUSE_FLAG)
        mock_send_notification.assert_called_once_with("Jarvis", "Hi TestUser, check in!")

    @patch('os.path.exists', return_value=True) # PAUSE_FLAG exists
    @patch('main.send_notification')
    def test_hourly_checkin_with_pause(self, mock_send_notification, mock_os_path_exists):
        config = {"user_name": "TestUser"} # Config still needed
        jarvis_main.hourly_checkin(config)
        mock_os_path_exists.assert_called_once_with(jarvis_main.PAUSE_FLAG)
        mock_send_notification.assert_not_called()

    @patch('socket.socket')
    def test_check_internet_connection_success(self, mock_socket_constructor):
        mock_socket_instance = MagicMock()
        mock_socket_constructor.return_value = mock_socket_instance
        self.assertTrue(jarvis_main.check_internet_connection())
        mock_socket_instance.connect.assert_called_once_with(("8.8.8.8", 53))

    @patch('socket.socket')
    def test_check_internet_connection_failure(self, mock_socket_constructor):
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = socket.error("Connection failed")
        mock_socket_constructor.return_value = mock_socket_instance
        self.assertFalse(jarvis_main.check_internet_connection())
        mock_socket_instance.connect.assert_called_once_with(("8.8.8.8", 53))


    @patch('main.load_config')
    @patch('main.show_initial_prompt') # Updated function name
    @patch('main.ask_for_password')
    @patch('main.check_internet_connection') # New mock
    @patch('main.play_video_fullscreen')
    @patch('threading.Thread')
    @patch('main.open_apps_and_folders')
    @patch('main.speak')
    @patch('main.send_notification')
    @patch('requests.get') # For IP address
    @patch('schedule.every')
    @patch('time.sleep')
    @patch('sys.exit') # To prevent test runner from exiting if main calls it
    @patch('subprocess.run') # For IP dialog
    def test_main_flow_access_granted(self, mock_subprocess_run_ip_dialog, mock_sys_exit, mock_time_sleep, mock_schedule_every,
                                      mock_requests_get, mock_send_notification_main, mock_speak_main, mock_open_apps,
                                      mock_thread_class, mock_play_video, mock_check_internet, mock_ask_password, mock_show_initial_prompt,
                                      mock_load_config):
        # --- Setup Mocks ---
        mock_config_data = {
            "sound": "boot.wav",
            "apps": ["TestApp"],
            "folders": ["/test/folder"],
            "user_name": "Test User",
            "voice": "Daniel",
            "startup_video_path": "/path/to/video.mp4",
            "hourly_checkin_message": "Hourly check for {user_name}"
        }
        mock_load_config.return_value = mock_config_data
        mock_ask_password.return_value = True  # Access granted
        mock_check_internet.return_value = True # Internet connected

        # Mock threading.Thread
        mock_thread_instance = MagicMock()
        # Make sure join doesn't block indefinitely if start isn't perfectly mocked or called
        mock_thread_instance.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread_instance

        # Mock schedule to prevent actual scheduling
        mock_job = MagicMock()
        mock_schedule_every.return_value.hour.return_value.at.return_value.do.return_value = mock_job

        # Make time.sleep raise an exception to break the while loop in main() after one pass
        # Allow specific sleep calls, then raise error
        sleep_call_count = 0
        def time_sleep_side_effect(duration):
            nonlocal sleep_call_count
            sleep_call_count += 1
            if sleep_call_count > 5: # Adjust based on number of sleeps before loop
                 raise InterruptedError("Break main loop for test")
            return None
        mock_time_sleep.side_effect = time_sleep_side_effect

        # Mock IP dialog and request
        mock_ip_dialog_result = MagicMock(stdout="button returned:Yes", returncode=0)
        mock_subprocess_run_ip_dialog.return_value = mock_ip_dialog_result
        mock_ip_response = MagicMock()
        mock_ip_response.text = "123.123.123.123"
        mock_requests_get.return_value = mock_ip_response

        # --- Run main ---
        with self.assertRaises(InterruptedError): # Expect main to break due to time.sleep mock
            jarvis_main.main()

        # --- Assertions ---
        mock_load_config.assert_called_once()
        mock_show_initial_prompt.assert_called_once()
        mock_ask_password.assert_called_once()
        mock_check_internet.assert_called_once()
        mock_play_video.assert_called_once_with(mock_config_data['startup_video_path'], mock_config_data['voice'])

        # Thread for sound
        mock_thread_class.assert_called_once_with(target=jarvis_main.play_bootup_sound, args=(mock_config_data.get('sound'),))
        # mock_thread_instance.start.assert_called_once() # start is called within open_apps_and_folders

        mock_open_apps.assert_called_once_with(mock_config_data, sound_thread_to_start=mock_thread_instance)
        mock_thread_instance.join.assert_called_once() # Sound thread joined

        # Check speak calls
        speak_calls = mock_speak_main.call_args_list
        # print(f"Speak calls: {speak_calls}") # For debugging
        self.assertIn(call("Network status: Connected and secure.", voice="Daniel"), speak_calls)

        today = datetime.now()
        days_left = (datetime(today.year, 12, 31) - today).days
        expected_final_greeting = f"Welcome home Test User. There are {days_left} days left in the year. Another day, another opportunity."
        self.assertIn(call(expected_final_greeting, voice="Daniel"), speak_calls)
        self.assertIn(call("Your public IP address is 123.123.123.123", voice="Daniel"), speak_calls)

        # Check notification calls
        notification_calls = mock_send_notification_main.call_args_list
        self.assertIn(call("Your IP Address", "123.123.123.123"), notification_calls)
        self.assertIn(call("Jarvis", "Notifications will appear here every hour."), notification_calls)

        mock_schedule_every.return_value.hour.return_value.at.return_value.do.assert_called_once_with(jarvis_main.hourly_checkin, config=mock_config_data)
        mock_sys_exit.assert_not_called() # Should not exit if access granted

    @patch('main.load_config')
    @patch('main.show_initial_prompt') # Updated function name
    @patch('main.ask_for_password')
    @patch('main.speak')
    @patch('sys.exit')
    @patch('time.sleep') # To check the dramatic pause
    # Add other mocks for functions called before sys.exit to ensure they are not called if not expected
    @patch('threading.Thread')
    @patch('main.open_apps_and_folders')
    def test_main_flow_access_denied(self, mock_open_apps, mock_thread_class, mock_time_sleep_denied,
                                     mock_sys_exit, mock_speak_main, mock_ask_password,
                                     mock_show_initial_prompt, mock_load_config):
        mock_load_config.return_value = {} # Minimal config
        mock_ask_password.return_value = False # Access denied

        # Call main
        jarvis_main.main()

        # Assertions
        mock_load_config.assert_called_once()
        mock_show_initial_prompt.assert_called_once()
        mock_ask_password.assert_called_once()
        mock_speak_main.assert_called_once_with("Incorrect passphrase. Unauthorized access attempt detected. Counter-measures initiated. We are coming for you.", voice=None) # Assuming default voice if not in minimal config
        mock_time_sleep_denied.assert_any_call(3) # Check for the dramatic pause
        mock_sys_exit.assert_called_once_with()

        # Ensure later parts of main are not called
        mock_thread_class.assert_not_called()
        mock_open_apps.assert_not_called()

if __name__ == '__main__':
    unittest.main()