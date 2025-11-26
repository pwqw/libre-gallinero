import pytest
from unittest.mock import Mock, patch, MagicMock
import sys


class TestBlinkApp:
    """Tests para la app blink"""
    
    def test_blink_module_imports(self):
        """Test que el módulo blink se puede importar"""
        # Mock MicroPython modules
        mock_machine = MagicMock()
        mock_time = MagicMock()
        mock_gc = MagicMock()
        
        with patch.dict('sys.modules', {
            'machine': mock_machine,
            'time': mock_time,
            'gc': mock_gc
        }):
            from src.blink import blink
            assert blink is not None
    
    def test_blink_run_accepts_config(self):
        """Test que run(cfg) acepta configuración"""
        # Mock MicroPython modules
        mock_machine = MagicMock()
        mock_pin = MagicMock()
        mock_machine.Pin.return_value = mock_pin
        mock_time = MagicMock()
        mock_gc = MagicMock()
        
        with patch.dict('sys.modules', {
            'machine': mock_machine,
            'time': mock_time,
            'gc': mock_gc
        }):
            from src.blink import blink
            
            cfg = {
                'LED_PIN': 2,
                'LED_DELAY': 0.5
            }
            
            # Mock sys.print_exception para MicroPython compatibility
            with patch('sys.print_exception', Mock(), create=True):
                # run() entra en un loop infinito, así que lo interrumpimos
                with patch('time.sleep', side_effect=KeyboardInterrupt()):
                    try:
                        blink.run(cfg)
                    except KeyboardInterrupt:
                        pass  # Esperado
            
            # Verificar que se creó el Pin
            mock_machine.Pin.assert_called_once_with(2, mock_machine.Pin.OUT)
    
    def test_blink_run_uses_defaults(self):
        """Test que run(cfg) usa valores por defecto"""
        # Mock MicroPython modules
        mock_machine = MagicMock()
        mock_pin = MagicMock()
        mock_machine.Pin.return_value = mock_pin
        mock_time = MagicMock()
        mock_gc = MagicMock()
        
        # Configurar sleep para que lance KeyboardInterrupt en la primera llamada
        sleep_call_count = [0]
        def sleep_side_effect(delay):
            sleep_call_count[0] += 1
            if sleep_call_count[0] == 1:
                # Primera llamada, verificar que el delay es 0.5
                assert delay == 0.5, f"Expected delay 0.5, got {delay}"
            raise KeyboardInterrupt()
        mock_time.sleep.side_effect = sleep_side_effect
        
        with patch.dict('sys.modules', {
            'machine': mock_machine,
            'time': mock_time,
            'gc': mock_gc
        }):
            from src.blink import blink
            
            cfg = {}  # Config vacía, debe usar defaults
            
            # Mock sys.print_exception para MicroPython compatibility
            with patch('sys.print_exception', Mock(), create=True):
                # run() entra en un loop infinito, así que lo interrumpimos
                try:
                    blink.run(cfg)
                except KeyboardInterrupt:
                    pass  # Esperado
            
            # Verificar que se creó el Pin con valor por defecto (2)
            mock_machine.Pin.assert_called_once_with(2, mock_machine.Pin.OUT)
            # Verificar que sleep fue llamado al menos una vez
            assert mock_time.sleep.called, "time.sleep should have been called"
    
    def test_blink_run_handles_exceptions(self, capsys):
        """Test que run(cfg) maneja excepciones correctamente"""
        # Mock MicroPython modules
        mock_machine = MagicMock()
        mock_machine.Pin.side_effect = Exception("Pin error")
        mock_time = MagicMock()
        mock_gc = MagicMock()
        
        with patch.dict('sys.modules', {
            'machine': mock_machine,
            'time': mock_time,
            'gc': mock_gc
        }):
            from src.blink import blink
            
            cfg = {}
            
            # Mock sys.print_exception para MicroPython compatibility
            mock_print_exception = Mock()
            with patch('sys.print_exception', mock_print_exception, create=True):
                blink.run(cfg)
            
            # Verificar que se imprimió el error
            captured = capsys.readouterr()
            assert '[blink] Error' in captured.out
            # Verificar que se llamó sys.print_exception
            mock_print_exception.assert_called_once()
    
    def test_blink_init_exports_run(self):
        """Test que __init__.py exporta la función run"""
        # Mock MicroPython modules para que blink.py se pueda importar
        mock_machine = MagicMock()
        mock_time = MagicMock()
        mock_gc = MagicMock()
        
        with patch.dict('sys.modules', {
            'machine': mock_machine,
            'time': mock_time,
            'gc': mock_gc
        }):
            from src.blink import run
            assert callable(run)
            assert run.__name__ == 'run'


class TestBlinkAppIntegration:
    """Tests de integración para la app blink"""
    
    def test_blink_app_loader_compatibility(self):
        """Test que blink es compatible con app_loader"""
        # Mock MicroPython modules
        mock_machine = MagicMock()
        mock_pin = MagicMock()
        mock_machine.Pin.return_value = mock_pin
        mock_time = MagicMock()
        mock_gc = MagicMock()
        
        # Configurar sleep para que lance KeyboardInterrupt
        mock_time.sleep.side_effect = KeyboardInterrupt()
        
        with patch.dict('sys.modules', {
            'machine': mock_machine,
            'time': mock_time,
            'gc': mock_gc
        }):
            # Importar blink primero para que esté disponible para app_loader
            from src.blink import blink
            
            # Hacer que el módulo 'blink' esté disponible para app_loader.load_app
            # app_loader hace 'import blink', así que necesitamos que esté en sys.modules
            import sys
            sys.modules['blink'] = blink
            
            # Ahora importar app_loader
            from src import app_loader
            
            cfg = {'APP': 'blink'}
            
            # Mock sys.print_exception para MicroPython compatibility
            with patch('sys.print_exception', Mock(), create=True):
                # load_app entra en un loop infinito, así que lo interrumpimos
                try:
                    app_loader.load_app('blink', cfg)
                except KeyboardInterrupt:
                    pass  # Esperado
            
            # Verificar que se importó blink
            assert 'blink' in sys.modules

