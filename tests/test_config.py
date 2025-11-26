import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
import sys
import io
import tempfile
import os


class TestLog:
    """Tests para la función log()"""
    
    def test_log_prints_message(self, capsys):
        """Test que log() imprime el mensaje con el prefijo [config]"""
        from src import config
        config.log("test message")
        captured = capsys.readouterr()
        assert "[config] test message" in captured.out
    
    def test_log_handles_flush(self, capsys):
        """Test que log() intenta hacer flush si está disponible"""
        mock_stdout = MagicMock()
        mock_stdout.flush = Mock()
        with patch('sys.stdout', mock_stdout):
            from src import config
            config.log("test")
            mock_stdout.flush.assert_called_once()
    
    def test_log_handles_no_flush(self, capsys):
        """Test que log() maneja cuando flush no está disponible"""
        mock_stdout = MagicMock()
        del mock_stdout.flush
        with patch('sys.stdout', mock_stdout):
            from src import config
            # No debería lanzar excepción
            config.log("test")
    
    def test_log_handles_flush_exception(self, capsys):
        """Test que log() maneja excepciones al hacer flush"""
        mock_stdout = MagicMock()
        mock_stdout.flush.side_effect = Exception("Flush error")
        with patch('sys.stdout', mock_stdout):
            from src import config
            # No debería lanzar excepción
            config.log("test")


class TestParseEnv:
    """Tests para la función parse_env()"""
    
    def test_parse_env_valid_file(self):
        """Test que parse_env() parsea correctamente un archivo .env válido"""
        env_content = """WIFI_SSID=test_ssid
WIFI_PASSWORD=test_password
LATITUDE=-31.4167
LONGITUDE=-64.1833
PROJECT=gallinero
"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            from src import config
            cfg = config.parse_env('.env')
            
            assert cfg['WIFI_SSID'] == 'test_ssid'
            assert cfg['WIFI_PASSWORD'] == 'test_password'
            assert cfg['LATITUDE'] == '-31.4167'
            assert cfg['LONGITUDE'] == '-64.1833'
            assert cfg['PROJECT'] == 'gallinero'
    
    def test_parse_env_with_quotes(self):
        """Test que parse_env() elimina comillas de los valores"""
        env_content = """WIFI_SSID="test_ssid"
WIFI_PASSWORD='test_password'
LATITUDE="-31.4167"
"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            from src import config
            cfg = config.parse_env('.env')
            
            assert cfg['WIFI_SSID'] == 'test_ssid'
            assert cfg['WIFI_PASSWORD'] == 'test_password'
            assert cfg['LATITUDE'] == '-31.4167'
    
    def test_parse_env_ignores_comments(self):
        """Test que parse_env() ignora líneas comentadas"""
        env_content = """# This is a comment
WIFI_SSID=test_ssid
# Another comment
WIFI_PASSWORD=test_password
"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            from src import config
            cfg = config.parse_env('.env')
            
            assert 'WIFI_SSID' in cfg
            assert 'WIFI_PASSWORD' in cfg
            assert len(cfg) == 2
    
    def test_parse_env_ignores_empty_lines(self):
        """Test que parse_env() ignora líneas vacías"""
        env_content = """
WIFI_SSID=test_ssid

WIFI_PASSWORD=test_password

"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            from src import config
            cfg = config.parse_env('.env')
            
            assert 'WIFI_SSID' in cfg
            assert 'WIFI_PASSWORD' in cfg
            assert len(cfg) == 2
    
    def test_parse_env_handles_whitespace(self):
        """Test que parse_env() elimina espacios en blanco de claves y valores"""
        env_content = """  WIFI_SSID  =  test_ssid  
WIFI_PASSWORD=test_password
"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            from src import config
            cfg = config.parse_env('.env')
            
            assert cfg['WIFI_SSID'] == 'test_ssid'
            assert cfg['WIFI_PASSWORD'] == 'test_password'
    
    def test_parse_env_handles_multiple_equals(self):
        """Test que parse_env() maneja valores con múltiples signos igual"""
        env_content = """WIFI_SSID=test=ssid=value
PASSWORD=pass=word
"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            from src import config
            cfg = config.parse_env('.env')
            
            assert cfg['WIFI_SSID'] == 'test=ssid=value'
            assert cfg['PASSWORD'] == 'pass=word'
    
    def test_parse_env_handles_file_not_found(self, capsys):
        """Test que parse_env() maneja archivo no encontrado"""
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            from src import config
            cfg = config.parse_env('.env')
            
            assert cfg == {}
            captured = capsys.readouterr()
            assert "No se pudo leer" in captured.out
    
    def test_parse_env_handles_io_error(self, capsys):
        """Test que parse_env() maneja errores de IO"""
        with patch('builtins.open', side_effect=IOError("IO error")):
            from src import config
            cfg = config.parse_env('.env')
            
            assert cfg == {}
            captured = capsys.readouterr()
            assert "No se pudo leer" in captured.out
    
    def test_parse_env_handles_permission_error(self, capsys):
        """Test que parse_env() maneja errores de permisos"""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            from src import config
            cfg = config.parse_env('.env')
            
            assert cfg == {}
            captured = capsys.readouterr()
            assert "No se pudo leer" in captured.out
    
    def test_parse_env_ignores_lines_without_equals(self):
        """Test que parse_env() ignora líneas sin signo igual"""
        env_content = """WIFI_SSID=test_ssid
INVALID_LINE_NO_EQUALS
WIFI_PASSWORD=test_password
"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            from src import config
            cfg = config.parse_env('.env')
            
            assert 'WIFI_SSID' in cfg
            assert 'WIFI_PASSWORD' in cfg
            assert 'INVALID_LINE_NO_EQUALS' not in cfg
            assert len(cfg) == 2


class TestLoadConfig:
    """Tests para la función load_config()"""
    
    @patch('src.config.parse_env')
    @patch('src.config.log')
    def test_load_config_from_env(self, mock_log, mock_parse_env):
        """Test que load_config() carga desde .env cuando existe"""
        mock_parse_env.side_effect = lambda path: {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password',
            'APP': 'gallinero'
        } if path == '.env' else {}
        
        from src import config
        cfg = config.load_config()
        
        assert cfg['WIFI_SSID'] == 'test_ssid'
        assert cfg['WIFI_PASSWORD'] == 'test_password'
        assert cfg['APP'] == 'gallinero'
        mock_log.assert_any_call("Configuración cargada desde .env")
        mock_log.assert_any_call("SSID configurado: test_ssid")
        mock_log.assert_any_call("App: gallinero")
    
    @patch('src.config.parse_env')
    @patch('src.config.log')
    def test_load_config_from_env_example(self, mock_log, mock_parse_env):
        """Test que load_config() carga desde .env.example cuando .env no existe"""
        mock_parse_env.side_effect = lambda path: {} if path == '.env' else {
            'WIFI_SSID': 'example_ssid',
            'WIFI_PASSWORD': 'example_password',
            'APP': 'heladera'
        } if path == '.env.example' else {}
        
        from src import config
        cfg = config.load_config()
        
        assert cfg['WIFI_SSID'] == 'example_ssid'
        assert cfg['WIFI_PASSWORD'] == 'example_password'
        assert cfg['APP'] == 'heladera'
        mock_log.assert_any_call("Configuración cargada desde .env.example")
    
    @patch('src.config.parse_env')
    @patch('src.config.log')
    def test_load_config_defaults(self, mock_log, mock_parse_env):
        """Test que load_config() usa valores por defecto cuando no hay archivos"""
        mock_parse_env.return_value = {}
        
        from src import config
        cfg = config.load_config()
        
        assert cfg['WIFI_SSID'] == 'libre gallinero'
        assert cfg['WIFI_PASSWORD'] == 'huevos1'
        assert cfg['WIFI_HIDDEN'] == 'false'
        assert cfg['LATITUDE'] == '-31.4167'
        assert cfg['LONGITUDE'] == '-64.1833'
        assert cfg['APP'] == 'heladera'
        mock_log.assert_any_call("Usando configuración por defecto")
        mock_log.assert_any_call("SSID configurado: libre gallinero")
        mock_log.assert_any_call("App: heladera")
    
    @patch('src.config.parse_env')
    @patch('src.config.log')
    def test_load_config_logs_loading(self, mock_log, mock_parse_env):
        """Test que load_config() registra el proceso de carga"""
        mock_parse_env.return_value = {}
        
        from src import config
        config.load_config()
        
        mock_log.assert_any_call("Cargando configuración...")
    
    @patch('src.config.parse_env')
    @patch('src.config.log')
    def test_load_config_handles_missing_keys(self, mock_log, mock_parse_env):
        """Test que load_config() maneja claves faltantes en la configuración"""
        mock_parse_env.return_value = {
            'WIFI_SSID': 'test_ssid'
            # Faltan otras claves
        }
        
        from src import config
        cfg = config.load_config()
        
        assert cfg['WIFI_SSID'] == 'test_ssid'
        # Verificar que get() no falla con claves faltantes
        assert cfg.get('APP', 'N/A') == 'N/A'
        mock_log.assert_any_call("SSID configurado: test_ssid")
        mock_log.assert_any_call("App: N/A")
    
    @patch('src.config.parse_env')
    @patch('src.config.log')
    def test_load_config_priority_env_over_example(self, mock_log, mock_parse_env):
        """Test que load_config() prioriza .env sobre .env.example"""
        def parse_side_effect(path):
            if path == '.env':
                return {'WIFI_SSID': 'from_env', 'APP': 'gallinero'}
            elif path == '.env.example':
                return {'WIFI_SSID': 'from_example', 'APP': 'heladera'}
            return {}
        
        mock_parse_env.side_effect = parse_side_effect
        
        from src import config
        cfg = config.load_config()
        
        assert cfg['WIFI_SSID'] == 'from_env'
        assert cfg['APP'] == 'gallinero'
        mock_log.assert_any_call("Configuración cargada desde .env")
        # No debería llamar a parse_env con .env.example
        assert mock_parse_env.call_count == 1
    
    @patch('src.config.parse_env')
    @patch('src.config.log')
    def test_load_config_empty_env_falls_back(self, mock_log, mock_parse_env):
        """Test que load_config() usa .env.example cuando .env está vacío"""
        mock_parse_env.side_effect = lambda path: {} if path == '.env' else {
            'WIFI_SSID': 'from_example',
            'APP': 'heladera'
        } if path == '.env.example' else {}
        
        from src import config
        cfg = config.load_config()
        
        assert cfg['WIFI_SSID'] == 'from_example'
        assert cfg['APP'] == 'heladera'
        mock_log.assert_any_call("Configuración cargada desde .env.example")

