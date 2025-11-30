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

    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_success_without_timezone(self, mock_logger, mock_sleep):
        """Test NTP sync exitoso sin timezone"""
        from src.ntp import sync_ntp
        import ntptime

        ntptime.settime = Mock()

        result = sync_ntp(longitude=None)

        assert result is True
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

        assert result is True
        ntptime.settime.assert_called_once()
        mock_tz_offset.assert_called_once_with(-45.0)

    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_retries_on_failure(self, mock_logger, mock_sleep):
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

        result = sync_ntp(longitude=None)

        assert result is True
        assert ntptime.settime.call_count == 4

    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_fails_after_5_attempts(self, mock_logger, mock_sleep):
        """Test que NTP falla después de 5 intentos"""
        from src.ntp import sync_ntp
        import ntptime

        ntptime.settime = Mock(side_effect=Exception("NTP error"))

        result = sync_ntp(longitude=None)

        assert result is False
        assert ntptime.settime.call_count == 5

    @patch('timezone.get_timezone_offset')
    @patch('time.sleep')
    @patch('src.ntp.logger')
    def test_sync_ntp_handles_timezone_int_conversion(self, mock_logger, mock_sleep, mock_tz_offset):
        """Test que timezone offset se convierte a int correctamente"""
        from src.ntp import sync_ntp
        import ntptime

        ntptime.settime = Mock()

        # Simular que get_timezone_offset retorna float
        mock_tz_offset.return_value = -3.5

        # No debería lanzar excepción por formato :+d
        result = sync_ntp(longitude=-52.5)

        assert result is True
