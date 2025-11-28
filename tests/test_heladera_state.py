import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
import sys
import json

@pytest.fixture
def mock_modules():
    """Mock MicroPython modules"""
    mock_ujson = MagicMock()
    mock_ujson.load = json.load
    mock_ujson.dump = json.dump

    with patch.dict('sys.modules', {
        'ujson': mock_ujson,
        'machine': MagicMock(),
        'time': MagicMock(),
        'gc': MagicMock(),
        'os': MagicMock()
    }):
        yield

class TestGetDefaultState:
    """Tests para get_default_state()"""

    def test_default_state_structure(self, mock_modules):
        from src.heladera import state

        default = state.get_default_state()

        assert default['version'] == 1
        assert default['last_ntp_timestamp'] == 0
        assert default['last_save_timestamp'] == 0
        assert default['fridge_on'] is True
        assert default['cycle_elapsed_seconds'] == 0
        assert default['total_runtime_seconds'] == 0
        assert default['boot_count'] == 0

class TestValidateState:
    """Tests para validate_state()"""

    def test_validate_complete_state(self, mock_modules):
        from src.heladera import state

        valid_state = state.get_default_state()
        assert state.validate_state(valid_state) is True

    def test_validate_incomplete_state(self, mock_modules):
        from src.heladera import state

        invalid_state = {'version': 1}
        assert state.validate_state(invalid_state) is False

class TestLoadState:
    """Tests para load_state()"""

    def test_load_valid_state(self, mock_modules):
        from src.heladera import state

        valid_json = json.dumps({
            'version': 1,
            'last_ntp_timestamp': 1000,
            'last_save_timestamp': 1000,
            'fridge_on': False,
            'cycle_elapsed_seconds': 500,
            'total_runtime_seconds': 10000,
            'boot_count': 5
        })

        with patch('builtins.open', mock_open(read_data=valid_json)):
            loaded = state.load_state()

            assert loaded['boot_count'] == 6  # Incrementado
            assert loaded['fridge_on'] is False
            assert loaded['cycle_elapsed_seconds'] == 500

    def test_load_missing_file(self, mock_modules):
        from src.heladera import state

        with patch('builtins.open', side_effect=OSError("File not found")):
            loaded = state.load_state()

            # Debería retornar defaults
            assert loaded == state.get_default_state()

    def test_load_corrupted_file(self, mock_modules):
        from src.heladera import state

        with patch('builtins.open', mock_open(read_data="corrupted json {")):
            loaded = state.load_state()

            # Debería retornar defaults
            assert loaded == state.get_default_state()

class TestSaveState:
    """Tests para save_state()"""

    def test_save_state_success(self, mock_modules):
        from src.heladera import state

        mock_os = sys.modules['os']
        mock_os.remove = Mock()
        mock_os.rename = Mock()

        with patch('builtins.open', mock_open()) as mock_file:
            test_state = state.get_default_state()
            result = state.save_state(test_state)

            assert result is True
            mock_file.assert_called()
            mock_os.rename.assert_called_once()

class TestRecoverStateAfterBoot:
    """Tests para recover_state_after_boot()"""

    def test_recover_without_ntp(self, mock_modules):
        from src.heladera import state

        test_state = state.get_default_state()
        test_state['fridge_on'] = False
        test_state['cycle_elapsed_seconds'] = 1000

        fridge_on, elapsed = state.recover_state_after_boot(test_state, has_ntp=False)

        # Sin NTP: arrancar conservador con 15 min ON
        assert fridge_on is True
        assert elapsed == 0

    def test_recover_with_ntp_short_outage(self, mock_modules):
        from src.heladera import state

        mock_time = sys.modules['time']
        mock_time.time = Mock(return_value=2000)  # 2000s desde epoch

        test_state = state.get_default_state()
        test_state['last_save_timestamp'] = 1700  # 300s atrás (5 min)
        test_state['fridge_on'] = True
        test_state['cycle_elapsed_seconds'] = 600  # 10 min en ciclo

        fridge_on, elapsed = state.recover_state_after_boot(test_state, has_ntp=True)

        # 5 min pasaron, debería estar en 10+5=15 min del ciclo
        assert fridge_on is True
        assert elapsed == 900  # 15 min

    def test_recover_with_ntp_long_outage(self, mock_modules):
        from src.heladera import state

        mock_time = sys.modules['time']
        mock_time.time = Mock(return_value=10000)

        test_state = state.get_default_state()
        test_state['last_save_timestamp'] = 1000  # 9000s atrás (>2h)
        test_state['fridge_on'] = False

        fridge_on, elapsed = state.recover_state_after_boot(test_state, has_ntp=True)

        # Corte largo: resetear
        assert fridge_on is True
        assert elapsed == 0

    def test_recover_with_ntp_first_boot(self, mock_modules):
        from src.heladera import state

        mock_time = sys.modules['time']
        mock_time.time = Mock(return_value=1000)

        test_state = state.get_default_state()
        # last_save_timestamp = 0 (nunca guardado)

        fridge_on, elapsed = state.recover_state_after_boot(test_state, has_ntp=True)

        # Primer boot con NTP
        assert fridge_on is True
        assert elapsed == 0
        assert test_state['last_ntp_timestamp'] == 1000

    def test_recover_with_ntp_clock_went_backwards(self, mock_modules):
        from src.heladera import state

        mock_time = sys.modules['time']
        mock_time.time = Mock(return_value=1000)

        test_state = state.get_default_state()
        test_state['last_save_timestamp'] = 2000  # Reloj retrocedió

        fridge_on, elapsed = state.recover_state_after_boot(test_state, has_ntp=True)

        # Reloj retrocedió: conservador
        assert fridge_on is True
        assert elapsed == 0

    def test_recover_with_ntp_cycle_transition(self, mock_modules):
        from src.heladera import state

        mock_time = sys.modules['time']
        mock_time.time = Mock(return_value=3700)  # 1 hora después

        test_state = state.get_default_state()
        test_state['last_save_timestamp'] = 100
        test_state['fridge_on'] = True
        test_state['cycle_elapsed_seconds'] = 100  # 100s en ciclo ON

        # Pasaron 3600s (1 hora) = 2 ciclos completos de 30 min
        # Ciclo 1 (30 min): ON → OFF
        # Ciclo 2 (30 min): OFF → ON
        # Estado debería volver a ON
        fridge_on, elapsed = state.recover_state_after_boot(test_state, has_ntp=True)

        assert fridge_on is True
        # elapsed_total = 100 + 3600 = 3700
        # full_cycles = 3700 // 1800 = 2
        # remainder = 3700 % 1800 = 100
        assert elapsed == 100
