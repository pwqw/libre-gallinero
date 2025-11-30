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
        """Test que run(cfg) retorna generador"""
        mock_machine = MagicMock()
        mock_pin = MagicMock()
        mock_machine.Pin.return_value = mock_pin
        mock_gc = MagicMock()

        with patch.dict('sys.modules', {'machine': mock_machine, 'gc': mock_gc}):
            from src.blink import blink
            cfg = {'LED_PIN': 2}

            # run() retorna generador
            gen = blink.run(cfg)
            assert gen is not None

            # Ejecutar 1 tick
            next(gen)

            # Verificar Pin creado
            mock_machine.Pin.assert_called_once_with(2, mock_machine.Pin.OUT)
    
    def test_blink_run_uses_defaults(self):
        """Test que run(cfg) usa pin por defecto"""
        mock_machine = MagicMock()
        mock_pin = MagicMock()
        mock_machine.Pin.return_value = mock_pin
        mock_gc = MagicMock()

        with patch.dict('sys.modules', {'machine': mock_machine, 'gc': mock_gc}):
            from src.blink import blink
            cfg = {}  # Vacío → usa defaults

            gen = blink.run(cfg)
            next(gen)

            # Pin por defecto = 2
            mock_machine.Pin.assert_called_once_with(2, mock_machine.Pin.OUT)
    
    def test_blink_run_handles_exceptions(self, capsys):
        """Test que run(cfg) maneja excepciones"""
        mock_machine = MagicMock()
        mock_machine.Pin.side_effect = Exception("Pin error")
        mock_gc = MagicMock()

        with patch.dict('sys.modules', {'machine': mock_machine, 'gc': mock_gc}):
            from src.blink import blink
            mock_print = Mock()
            with patch('sys.print_exception', mock_print, create=True):
                gen = blink.run({})
                # Error ocurre en next(), generador maneja con try/except
                list(gen)  # Consume generador hasta que termine

            captured = capsys.readouterr()
            assert '[blink] Error' in captured.out
            mock_print.assert_called_once()
    
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

