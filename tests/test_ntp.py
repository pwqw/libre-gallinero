"""Tests minimalistas para ntp.py"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import sys

# Mock MicroPython modules
sys.modules['ntptime'] = MagicMock()
sys.modules['utime'] = MagicMock()
sys.modules['machine'] = MagicMock()
sys.modules['logger'] = MagicMock()


class TestNtpSync:
    """Tests minimalistas para sync_ntp()"""

    @patch('utime.time')
    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_success_without_timezone(self, mock_logger, mock_sleep, mock_time):
        """Test NTP sync exitoso sin timezone"""
        from src.ntp import sync_ntp
        import ntptime

        ntptime.settime = Mock()
        mock_time.return_value = 1234567890

        result = sync_ntp(longitude=None)

        assert result == (True, 1234567890)  # Returns (True, timestamp)
        assert isinstance(result[1], int)
        ntptime.settime.assert_called_once()

    @patch('timezone.get_timezone_offset')
    @patch('time.sleep')
    @patch('src.ntp.logger')
    @patch('utime.localtime')
    @patch('utime.time')
    def test_sync_ntp_success_with_timezone(self, mock_time, mock_localtime, mock_logger, mock_sleep, mock_tz_offset):
        """Test NTP sync exitoso con timezone"""
        from src.ntp import sync_ntp
        import ntptime
        import machine

        ntptime.settime = Mock()
        mock_time.return_value = 1234567890
        mock_localtime.return_value = (2024, 1, 1, 12, 0, 0, 0, 1)

        mock_rtc = MagicMock()
        machine.RTC = Mock(return_value=mock_rtc)

        mock_tz_offset.return_value = -3

        result = sync_ntp(longitude=-45.0)

        assert result == (True, 1234567890)  # Returns (True, timestamp)
        ntptime.settime.assert_called_once()
        mock_tz_offset.assert_called_once_with(-45.0)

    @patch('utime.time')
    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_retries_on_failure(self, mock_logger, mock_sleep, mock_time):
        """Test que NTP reintenta en caso de falla"""
        from src.ntp import sync_ntp
        import ntptime

        # Falla 3 veces, luego éxito
        call_count = {'count': 0}
        def settime_side_effect():
            call_count['count'] += 1
            if call_count['count'] < 4:
                raise Exception("NTP error")

        ntptime.settime = Mock(side_effect=settime_side_effect)
        mock_time.return_value = 1234567890

        result = sync_ntp(longitude=None)

        assert result[0] is True  # Returns (True, timestamp)
        assert isinstance(result[1], int)
        assert result[1] == 1234567890
        assert ntptime.settime.call_count == 4

    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_fails_after_5_attempts(self, mock_logger, mock_sleep):
        """Test que NTP falla después de 5 intentos"""
        from src.ntp import sync_ntp
        import ntptime

        ntptime.settime = Mock(side_effect=Exception("NTP error"))

        result = sync_ntp(longitude=None)

        assert result == (False, 0)  # Returns (False, 0) on failure
        assert ntptime.settime.call_count == 5

    @patch('utime.time')
    @patch('timezone.get_timezone_offset')
    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_handles_timezone_int_conversion(self, mock_logger, mock_sleep, mock_tz_offset, mock_time):
        """Test que timezone offset se convierte a int correctamente"""
        from src.ntp import sync_ntp
        import ntptime

        ntptime.settime = Mock()
        mock_time.return_value = 1234567890

        # Simular que get_timezone_offset retorna float
        mock_tz_offset.return_value = -3.5

        # No debería lanzar excepción por formato :+d
        result = sync_ntp(longitude=-52.5)

        assert result[0] is True  # Returns (True, timestamp)
        assert isinstance(result[1], int)
        assert result[1] == 1234567890
