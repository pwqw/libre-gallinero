"""Tests minimalistas para logger.py"""
import pytest
from unittest.mock import patch, MagicMock
import sys

# Mock MicroPython sys si es necesario
if 'src.logger' in sys.modules:
    del sys.modules['src.logger']


class TestLogger:
    """Tests para el sistema de logging circular"""

    def test_init(self):
        """Test inicialización del buffer"""
        import src.logger

        src.logger.init(50)

        # Buffer debe ser lista después de init
        assert isinstance(src.logger._buf, list)

    def test_log_stores_message(self):
        """Test que log() almacena mensajes"""
        from src.logger import init, log, get

        init(10)
        log('test', 'mensaje de prueba')

        buffer = get()
        assert '[test] mensaje de prueba' in buffer

    def test_log_circular_buffer(self):
        """Test que buffer es circular (descarta viejos)"""
        from src.logger import init, log, get

        init(3)  # Buffer de solo 3 líneas

        log('t', 'msg1')
        log('t', 'msg2')
        log('t', 'msg3')
        log('t', 'msg4')  # Este debe sacar msg1

        buffer = get()
        assert 'msg1' not in buffer  # Descartado
        assert 'msg4' in buffer      # Más reciente

    def test_clear(self):
        """Test que clear() vacía el buffer"""
        from src.logger import init, log, clear, get

        init(10)
        log('t', 'test')
        clear()

        buffer = get()
        assert buffer == ''

    @patch('sys.stdout')
    def test_log_prints_to_stdout(self, mock_stdout):
        """Test que log() imprime a stdout"""
        from src.logger import init, log

        init(10)
        mock_stdout.flush = MagicMock()

        log('tag', 'mensaje')

        # Verificar que se imprimió algo (print llamado)
        assert mock_stdout.write.called or mock_stdout.flush.called

    def test_log_before_init(self):
        """Test que log() funciona incluso sin init()"""
        import src.logger
        src.logger._buf = None

        from src.logger import log

        # No debería lanzar excepción
        log('test', 'mensaje')

    def test_get_when_empty(self):
        """Test get() cuando buffer está vacío"""
        from src.logger import init, get

        init(10)

        buffer = get()
        assert buffer == ''
