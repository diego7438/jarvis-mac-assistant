import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import os
import sys
from datetime import datetime
import socket # For mocking network check
import subprocess # For mocking subprocess.run specifically for network scan

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
    def test_show_initial_prompt(self, mock_subprocess_run):
        jarvis_main.show_initial_prompt()
        expected_script = 'display dialog "Ready to proceed?" buttons {"Continue"} default button 1 with title "Jarvis"'
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

    @patch('subprocess.run')
    def test_ask_for_name_correct(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "button returned:Confirm\ntext returned:Diego"
        mock_subprocess_run.return_value = mock_result
        self.assertTrue(jarvis_main.ask_for_name("Diego"))
        expected_script = 'display dialog "Please state your name to confirm identity:" default answer "" buttons {"Confirm"} default button 1 with title "Jarvis Identity Check"'
        mock_subprocess_run.assert_called_once_with(["osascript", "-e", expected_script], capture_output=True, text=True)

    @patch('subprocess.run')
    def test_ask_for_name_incorrect(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "button returned:Confirm\ntext returned:NotDiego"
        mock_subprocess_run.return_value = mock_result
        self.assertFalse(jarvis_main.ask_for_name("Diego"))

    @patch('subprocess.run')
    def test_ask_for_name_cancel(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "button returned:Cancel"
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result
        self.assertFalse(jarvis_main.ask_for_name("Diego"))

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
    @patch('subprocess.run')
    @patch('main.speak')
    @patch('threading.Thread')
    def test_open_apps_and_folders_with_arc_confirm(self, mock_thread_class, mock_speak, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Arc", "Spotify", "Notion"],
            "folders": ["/Users/test/Desktop"],
            "voice": "Alex"
        }
        mock_general_dialog_result = MagicMock(stdout="button returned:Open Apps", returncode=0)
        mock_arc_dialog_result = MagicMock(stdout="button returned:Continue", returncode=0)
        mock_subprocess_run_dialog.side_effect = [mock_general_dialog_result, mock_arc_dialog_result]

        mock_sound_thread = MagicMock()
        mock_thread_class.return_value = mock_sound_thread

        jarvis_main.open_apps_and_folders(config, sound_thread_to_start=mock_sound_thread)

        expected_arc_dialog_script = 'display dialog "Open Arc?" buttons {"Continue", "Cancel"} default button "Continue" with title "Jarvis"'
        expected_general_dialog_script = 'display dialog "Open configured applications and folders (excluding Arc)?" buttons {"Open Apps", "Continue"} default button "Open Apps" with title "Jarvis"'

        self.assertEqual(mock_subprocess_run_dialog.call_count, 2)
        mock_subprocess_run_dialog.assert_any_call(
            ["osascript", "-e", expected_general_dialog_script], capture_output=True, text=True
        )
        mock_subprocess_run_dialog.assert_any_call(
            ["osascript", "-e", expected_arc_dialog_script], capture_output=True, text=True
        )

        expected_popen_calls = [
            call(["open", "-a", "Spotify"]),
            call(["open", "-a", "Notion"]),
            call(["open", "/Users/test/Desktop"]),
            call(["open", "-a", "Arc"])
        ]
        mock_subprocess_popen.assert_has_calls(expected_popen_calls, any_order=False)
        self.assertEqual(mock_subprocess_popen.call_count, 4)
        mock_speak.assert_not_called()
        mock_sound_thread.start.assert_called_once()

    @patch('subprocess.Popen')
    @patch('subprocess.run')
    @patch('main.speak')
    @patch('threading.Thread')
    def test_open_apps_and_folders_with_arc_cancel(self, mock_thread_class, mock_speak, mock_subprocess_run_dialog, mock_subprocess_popen):
        config = {
            "apps": ["Arc", "Spotify"],
            "folders": [],
            "voice": "Alex"
        }
        mock_general_dialog_result = MagicMock(stdout="button returned:Open Apps", returncode=0)
        mock_arc_dialog_result = MagicMock(stdout="button returned:Cancel", returncode=0)
        mock_subprocess_run_dialog.side_effect = [mock_general_dialog_result, mock_arc_dialog_result]

        mock_sound_thread = MagicMock()
        mock_thread_class.return_value = mock_sound_thread

        jarvis_main.open_apps_and_folders(config, sound_thread_to_start=mock_sound_thread)

        expected_arc_dialog_script = 'display dialog "Open Arc?" buttons {"Continue", "Cancel"} default button "Continue" with title "Jarvis"'
        mock_subprocess_run_dialog.assert_any_call(
            ["osascript", "-e", expected_arc_dialog_script], capture_output=True, text=True
        )
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
        mock_subprocess_popen.assert_has_calls(expected_popen_calls, any_order=True)
        self.assertEqual(mock_subprocess_popen.call_count, 3)
        expected_general_dialog_script = 'display dialog "Open configured applications and folders (excluding Arc)?" buttons {"Open Apps", "Continue"} default button "Open Apps" with title "Jarvis"'
        mock_subprocess_run_dialog.assert_called_once_with(
            ["osascript", "-e", expected_general_dialog_script], capture_output=True, text=True
        )
        mock_sound_thread.start.assert_called_once()

    @patch('os.path.exists', return_value=False)
    @patch('main.send_notification')
    def test_hourly_checkin_no_pause(self, mock_send_notification, mock_os_path_exists):
        config = {"user_name": "TestUser", "hourly_checkin_message": "Hi {user_name}, check in!"}
        jarvis_main.hourly_checkin(config)
        mock_os_path_exists.assert_called_once_with(jarvis_main.PAUSE_FLAG)
        mock_send_notification.assert_called_once_with("Jarvis", "Hi TestUser, check in!")

    @patch('os.path.exists', return_value=True)
    @patch('main.send_notification')
    def test_hourly_checkin_with_pause(self, mock_send_notification, mock_os_path_exists):
        config = {"user_name": "TestUser"}
        jarvis_main.hourly_checkin(config)
        mock_os_path_exists.assert_called_once_with(jarvis_main.PAUSE_FLAG)
        mock_send_notification.assert_not_called()

    @patch('subprocess.run')
    def test_get_network_device_info_success(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "? (192.168.1.1) at 00:1a:11:xx:xx:xx on en0 ifscope [ethernet]\n"
            "? (192.168.1.100) at 70:3a:0e:yy:yy:yy on en0 ifscope [ethernet]\n"
            "? (192.168.1.101) at aa:bb:cc:zz:zz:zz on en0 ifscope [ethernet]\n" # Unknown OUI
            "? (192.168.1.255) at (incomplete) on en0 ifscope [ethernet]\n"
        )
        mock_subprocess_run.return_value = mock_result

        count, manufacturers = jarvis_main.get_network_device_info()

        mock_subprocess_run.assert_called_once_with(["arp", "-a"], capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(count, 3)
        self.assertEqual(manufacturers, {
            "Apple": 1,
            "Amazon Technologies Inc.": 1,
            "Unknown Manufacturer": 1
        })

    @patch('subprocess.run')
    def test_get_network_device_info_arp_command_fail(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "arp command failed"
        mock_subprocess_run.return_value = mock_result

        count, manufacturers = jarvis_main.get_network_device_info()
        self.assertEqual(count, 0)
        self.assertEqual(manufacturers, {})

    @patch('subprocess.run', side_effect=FileNotFoundError("arp not found"))
    def test_get_network_device_info_arp_not_found(self, mock_subprocess_run):
        count, manufacturers = jarvis_main.get_network_device_info()
        self.assertEqual(count, 0)
        self.assertEqual(manufacturers, {})

    @patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd="arp -a", timeout=5))
    def test_get_network_device_info_timeout(self, mock_subprocess_run):
        count, manufacturers = jarvis_main.get_network_device_info()
        self.assertEqual(count, 0)
        self.assertEqual(manufacturers, {})

    @patch('subprocess.run')
    def test_get_network_device_info_empty_output(self, mock_subprocess_run):
        mock_result = MagicMock(returncode=0, stdout="")
        mock_subprocess_run.return_value = mock_result
        count, manufacturers = jarvis_main.get_network_device_info()
        self.assertEqual(count, 0)
        self.assertEqual(manufacturers, {})

    @patch('subprocess.run')
    def test_get_network_device_info_incomplete_only(self, mock_subprocess_run):
        mock_result = MagicMock(returncode=0, stdout="? (192.168.1.255) at (incomplete) on en0 ifscope [ethernet]\n")
        mock_subprocess_run.return_value = mock_result
        count, manufacturers = jarvis_main.get_network_device_info()
        self.assertEqual(count, 0)
        self.assertEqual(manufacturers, {})




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

    @patch('cv2.VideoCapture')
    @patch('cv2.CascadeClassifier')
    @patch('os.path.exists', return_value=True)
    @patch('main.speak')
    def test_perform_facial_scan_face_detected(self, mock_speak, mock_os_path_exists, mock_cascade_classifier, mock_video_capture):
        mock_cap_instance = MagicMock()
        mock_cap_instance.isOpened.return_value = True
        mock_cap_instance.read.return_value = (True, MagicMock())
        mock_video_capture.return_value = mock_cap_instance

        mock_cascade_instance = MagicMock()
        mock_cascade_instance.detectMultiScale.return_value = [(10, 20, 30, 40)]
        mock_cascade_classifier.return_value = mock_cascade_instance

        self.assertTrue(jarvis_main.perform_facial_scan(voice_for_errors="Alex", duration_seconds=0.1))
        mock_cap_instance.release.assert_called_once()
        mock_speak.assert_not_called()

    @patch('cv2.VideoCapture')
    @patch('cv2.CascadeClassifier')
    @patch('os.path.exists', return_value=True)
    @patch('main.speak')
    def test_perform_facial_scan_no_face_detected(self, mock_speak, mock_os_path_exists, mock_cascade_classifier, mock_video_capture):
        mock_cap_instance = MagicMock()
        mock_cap_instance.isOpened.return_value = True
        mock_cap_instance.read.return_value = (True, MagicMock())
        mock_video_capture.return_value = mock_cap_instance

        mock_cascade_instance = MagicMock()
        mock_cascade_instance.detectMultiScale.return_value = []
        mock_cascade_classifier.return_value = mock_cascade_instance

        self.assertFalse(jarvis_main.perform_facial_scan(voice_for_errors="Alex", duration_seconds=0.1))
        mock_cap_instance.release.assert_called_once()
        mock_speak.assert_not_called()

    @patch('cv2.VideoCapture')
    @patch('os.path.exists', return_value=True)
    @patch('main.speak')
    def test_perform_facial_scan_webcam_error(self, mock_speak, mock_os_path_exists, mock_video_capture):
        mock_cap_instance = MagicMock()
        mock_cap_instance.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap_instance

        self.assertFalse(jarvis_main.perform_facial_scan(voice_for_errors="Alex"))
        mock_speak.assert_called_once_with("Unable to access webcam for facial scan.", voice="Alex")

    @patch('os.path.exists', return_value=False)
    @patch('main.speak')
    def test_perform_facial_scan_cascade_file_missing(self, mock_speak, mock_os_path_exists):
        self.assertFalse(jarvis_main.perform_facial_scan(voice_for_errors="Alex"))
        mock_os_path_exists.assert_called_once()
        mock_speak.assert_called_once_with("Facial recognition module error. Cascade file missing.", voice="Alex")

    @patch('main.load_config')
    @patch('main.perform_facial_scan')
    @patch('main.ask_for_name')
    @patch('main.show_initial_prompt')
    @patch('main.ask_for_password')
    @patch('main.check_internet_connection')
    @patch('main.play_video_fullscreen')
    @patch('main.get_network_device_info') # New patch
    @patch('threading.Thread')
    @patch('main.open_apps_and_folders')
    @patch('main.speak')
    @patch('main.send_notification')
    @patch('requests.get')
    @patch('schedule.every')
    @patch('time.time', side_effect=[0, 0.1, 0.2, 0.3, 10]) # For facial scan loop
    @patch('time.sleep')
    @patch('sys.exit')
    @patch('subprocess.run')
    def test_main_flow_access_granted(self, mock_subprocess_run_ip_dialog, mock_sys_exit, mock_time_sleep, mock_time_time, mock_schedule_every,
                                      mock_requests_get, mock_send_notification_main, mock_speak_main, mock_open_apps,
                                      mock_thread_class, mock_get_network_device_info, mock_play_video, mock_check_internet,
                                      mock_ask_password, mock_show_initial_prompt, mock_ask_for_name, mock_perform_facial_scan, mock_load_config):
        # Note: mock_time_time is for perform_facial_scan, mock_time_sleep is for main loop
        mock_config_data = {
            "sound": "boot.wav", "apps": ["TestApp"], "folders": ["/test/folder"],
            "user_name": "Test User", "voice": "Daniel",
            "startup_video_path": "/path/to/video.mp4",
            "hourly_checkin_message": "Hourly check for {user_name}",
            "perform_network_scan": True, # Enable network scan for this test
            "facial_scan_duration_seconds": 0.2 # Short duration for test
        }
        mock_load_config.return_value = mock_config_data
        mock_perform_facial_scan.return_value = True
        mock_ask_for_name.return_value = True
        mock_ask_password.return_value = True
        mock_check_internet.return_value = True
        mock_get_network_device_info.return_value = (2, {"Apple": 1, "Google": 1}) # Mock network scan result

        mock_thread_instance = MagicMock()
        mock_thread_instance.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread_instance

        mock_job = MagicMock()
        mock_schedule_every.return_value.hour.return_value.at.return_value.do.return_value = mock_job

        sleep_call_count = 0
        def time_sleep_side_effect(duration):
            nonlocal sleep_call_count
            sleep_call_count += 1
            if sleep_call_count > 12:
                 raise InterruptedError("Break main loop for test")
            return None
        mock_time_sleep.side_effect = time_sleep_side_effect

        mock_ip_dialog_result = MagicMock(stdout="button returned:Yes", returncode=0)
        mock_subprocess_run_ip_dialog.return_value = mock_ip_dialog_result
        mock_ip_response = MagicMock(text="123.123.123.123")
        mock_requests_get.return_value = mock_ip_response

        with self.assertRaises(InterruptedError):
            jarvis_main.main()

        mock_load_config.assert_called_once()
        mock_perform_facial_scan.assert_called_once_with(voice_for_errors=mock_config_data['voice'], duration_seconds=mock_config_data['facial_scan_duration_seconds'])
        mock_ask_for_name.assert_called_once_with("Diego")
        mock_show_initial_prompt.assert_called_once()
        mock_ask_password.assert_called_once()
        mock_check_internet.assert_called_once()
        mock_get_network_device_info.assert_called_once() # Verify network scan is called
        mock_play_video.assert_called_once_with(mock_config_data['startup_video_path'], mock_config_data['voice'])
        mock_thread_class.assert_called_once_with(target=jarvis_main.play_bootup_sound, args=(mock_config_data.get('sound'),))
        mock_open_apps.assert_called_once_with(mock_config_data, sound_thread_to_start=mock_thread_instance)
        mock_thread_instance.join.assert_called_once()

        speak_calls = mock_speak_main.call_args_list
        self.assertIn(call("Initiating identity verification sequence.", voice="Daniel"), speak_calls)
        self.assertIn(call("Facial scan successful. Primary user profile detected.", voice="Daniel"), speak_calls)
        expected_network_speak_message = "Network status: Connected and secure. I've also detected 2 other devices on your local network. This includes 1 Apple device, and 1 Google device."
        self.assertIn(call(expected_network_speak_message, voice="Daniel"), speak_calls)
        today = datetime.now()
        graduation_date = datetime.strptime("2026-05-29", "%Y-%m-%d")
        days_until_graduation = (graduation_date - today).days
        expected_countdown_message = f"There are {days_until_graduation} days left until graduation on May 29, 2026."
        expected_final_greeting = f"Welcome home Test User. {expected_countdown_message} Another day, another opportunity."
        self.assertIn(call(expected_final_greeting, voice="Daniel"), speak_calls)
        self.assertIn(call("Your public IP address is 123.123.123.123", voice="Daniel"), speak_calls)

        notification_calls = mock_send_notification_main.call_args_list
        self.assertIn(call("Your IP Address", "123.123.123.123"), notification_calls)
        self.assertIn(call("Jarvis", "Notifications will appear here every hour."), notification_calls)
        mock_schedule_every.return_value.hour.return_value.at.return_value.do.assert_called_once_with(jarvis_main.hourly_checkin, config=mock_config_data)
        mock_sys_exit.assert_not_called()

    @patch('main.load_config')
    @patch('main.perform_facial_scan')
    @patch('main.ask_for_name')
    @patch('main.show_initial_prompt')
    @patch('main.ask_for_password')
    @patch('main.speak')
    @patch('sys.exit')
    @patch('time.sleep')
    @patch('threading.Thread')
    @patch('main.open_apps_and_folders')
    def test_main_flow_password_denied(self, mock_open_apps, mock_thread_class, mock_time_sleep, mock_sys_exit,
                                     mock_speak_main, mock_ask_password, mock_show_initial_prompt, mock_ask_name,
                                     mock_perform_facial_scan, mock_load_config):
        mock_load_config.return_value = {"voice": "Ava", "facial_scan_duration_seconds": 5}
        mock_perform_facial_scan.return_value = True
        mock_ask_name.return_value = True
        mock_ask_password.return_value = False

        jarvis_main.main()

        mock_load_config.assert_called_once()
        mock_speak_main.assert_any_call("Initiating identity verification sequence.", voice="Ava")
        mock_perform_facial_scan.assert_called_once_with(voice_for_errors="Ava", duration_seconds=5)
        mock_speak_main.assert_any_call("Facial scan successful. Primary user profile detected.", voice="Ava")
        mock_ask_name.assert_called_once_with("Diego")
        mock_show_initial_prompt.assert_called_once()
        mock_ask_password.assert_called_once()
        mock_speak_main.assert_any_call("Incorrect passphrase. Unauthorized access attempt detected. Counter-measures initiated. We are coming for you.", voice="Ava")
        mock_time_sleep.assert_any_call(3) # Check for the specific sleep after denial
        mock_sys_exit.assert_called_once_with()
        mock_thread_class.assert_not_called()
        mock_open_apps.assert_not_called()

    @patch('main.load_config')
    @patch('main.perform_facial_scan', return_value=True)
    @patch('main.ask_for_name', return_value=False)
    @patch('main.show_initial_prompt')
    @patch('main.ask_for_password')
    @patch('main.speak')
    @patch('sys.exit')
    @patch('time.sleep')
    def test_main_flow_name_denied(self, mock_time_sleep, mock_sys_exit, mock_speak, mock_ask_password,
                                 mock_show_prompt, mock_ask_name, mock_perform_facial_scan, mock_load_config):
        mock_load_config.return_value = {"voice": "Zarvox", "facial_scan_duration_seconds": 5}
        jarvis_main.main()

        mock_perform_facial_scan.assert_called_once_with(voice_for_errors="Zarvox", duration_seconds=5)
        mock_ask_name.assert_called_once_with("Diego")
        mock_ask_password.assert_not_called()
        mock_speak.assert_any_call("Name verification failed. Identity not confirmed. Access denied.", voice="Zarvox")
        mock_time_sleep.assert_any_call(3) # Check for the specific sleep after denial
        mock_sys_exit.assert_called_once_with()
        mock_show_prompt.assert_not_called() # Should not be called if name fails

    @patch('main.load_config')
    @patch('main.perform_facial_scan', return_value=False)
    @patch('main.speak')
    @patch('sys.exit')
    @patch('time.sleep')
    @patch('main.ask_for_name')
    @patch('main.show_initial_prompt')
    @patch('main.ask_for_password')
    def test_main_flow_facial_scan_denied(self, mock_ask_password, mock_show_initial_prompt, mock_ask_name,
                                          mock_time_sleep, mock_sys_exit, mock_speak,
                                          mock_perform_facial_scan, mock_load_config):
        mock_load_config.return_value = {"voice": "Tom", "facial_scan_duration_seconds": 5}
        jarvis_main.main()

        mock_perform_facial_scan.assert_called_once_with(voice_for_errors="Tom", duration_seconds=5)
        mock_speak.assert_any_call("Facial scan failed or no face detected. Access denied.", voice="Tom")
        mock_sys_exit.assert_called_once_with()
        mock_ask_name.assert_not_called()
        mock_show_initial_prompt.assert_not_called()
        mock_ask_password.assert_not_called()

if __name__ == '__main__':
    unittest.main()