import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_modules():
    """Mock MicroPython modules"""
    with patch.dict('sys.modules', {
        'machine': MagicMock(),
        'time': MagicMock(),
        'gc': MagicMock()
    }):
        yield

class TestGetTimezoneOffset:
    """Tests para get_timezone_offset()"""

    def test_argentina_cordoba(self, mock_modules):
        import timezone

        # Córdoba, Argentina: -64.1833 → -4 hours
        tz_offset = timezone.get_timezone_offset(-64.1833)
        assert tz_offset == -4

    def test_uruguay(self, mock_modules):
        import timezone

        # Uruguay: -60.0 → -4 hours
        tz_offset = timezone.get_timezone_offset(-60.0)
        assert tz_offset == -4

    def test_greenwich(self, mock_modules):
        import timezone

        # Greenwich: 0.0 → 0 hours
        tz_offset = timezone.get_timezone_offset(0.0)
        assert tz_offset == 0

    def test_china(self, mock_modules):
        import timezone

        # China: 120.0 → +8 hours
        tz_offset = timezone.get_timezone_offset(120.0)
        assert tz_offset == 8

    def test_usa_west_coast(self, mock_modules):
        import timezone

        # USA West Coast: -122.0 → -8 hours
        tz_offset = timezone.get_timezone_offset(-122.0)
        assert tz_offset == -8

    def test_rounding(self, mock_modules):
        import timezone

        # Test rounding: -62.5 → -4 hours (rounds from -4.16)
        tz_offset = timezone.get_timezone_offset(-62.5)
        assert tz_offset == -4

        # Test rounding: -67.5 → -4 hours (Python's round(-4.5) = -4, bankers' rounding)
        tz_offset = timezone.get_timezone_offset(-67.5)
        assert tz_offset == -4

        # Test rounding: -68.0 → -5 hours (rounds from -4.53)
        tz_offset = timezone.get_timezone_offset(-68.0)
        assert tz_offset == -5

    def test_string_conversion(self, mock_modules):
        """Test que get_timezone_offset acepta strings (desde .env config)"""
        import timezone

        # String desde .env
        tz_offset = timezone.get_timezone_offset("-64.1833")
        assert tz_offset == -4

        # String positivo
        tz_offset = timezone.get_timezone_offset("120.0")
        assert tz_offset == 8

        # String negativo
        tz_offset = timezone.get_timezone_offset("-60.0")
        assert tz_offset == -4

class TestApplyTimezoneToTime:
    """Tests para apply_timezone_to_time()"""

    def test_apply_positive_offset(self, mock_modules):
        import timezone

        # 10:00 UTC + 8 hours → 18:00
        time_tuple = (2025, 1, 28, 10, 0, 0, 1, 28)
        adjusted = timezone.apply_timezone_to_time(time_tuple, 8)

        assert adjusted[3] == 18  # hour
        assert adjusted[0] == 2025  # year unchanged
        assert adjusted[1] == 1     # month unchanged
        assert adjusted[2] == 28    # day unchanged

    def test_apply_negative_offset(self, mock_modules):
        import timezone

        # 10:00 UTC - 4 hours → 06:00
        time_tuple = (2025, 1, 28, 10, 0, 0, 1, 28)
        adjusted = timezone.apply_timezone_to_time(time_tuple, -4)

        assert adjusted[3] == 6  # hour

    def test_wrap_around_midnight(self, mock_modules):
        import timezone

        # 23:00 UTC + 2 hours → 01:00 (wraps around)
        time_tuple = (2025, 1, 28, 23, 0, 0, 1, 28)
        adjusted = timezone.apply_timezone_to_time(time_tuple, 2)

        assert adjusted[3] == 1  # hour wraps to 1

    def test_negative_wrap(self, mock_modules):
        import timezone

        # 01:00 UTC - 4 hours → 21:00 (previous day in hours)
        time_tuple = (2025, 1, 28, 1, 0, 0, 1, 28)
        adjusted = timezone.apply_timezone_to_time(time_tuple, -4)

        assert adjusted[3] == 21  # wraps to 21 (previous day)

    def test_zero_offset(self, mock_modules):
        import timezone

        # 10:00 UTC + 0 hours → 10:00
        time_tuple = (2025, 1, 28, 10, 0, 0, 1, 28)
        adjusted = timezone.apply_timezone_to_time(time_tuple, 0)

        assert adjusted[3] == 10  # hour unchanged
