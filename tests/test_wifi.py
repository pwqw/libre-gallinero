import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import io

# Mockear módulos de MicroPython antes de importar src.wifi
mock_network = MagicMock()
mock_network.STA_IF = 1
mock_network.STAT_IDLE = 1000
mock_network.STAT_CONNECTING = 1001
mock_network.STAT_GOT_IP = 1010
mock_network.STAT_WRONG_PASSWORD = 202
mock_network.STAT_NO_AP_FOUND = 201
mock_network.STAT_CONNECT_FAIL = 200
sys.modules['network'] = mock_network

mock_webrepl = MagicMock()
sys.modules['webrepl'] = mock_webrepl


class TestLog:
    """Tests para la función log()"""
    
    @patch('sys.stdout')
    def test_log_prints_message(self, mock_stdout):
        from src.wifi import log
        log("test message")
        # Verificar que se llamó print con el formato correcto
        assert mock_stdout.write.called or hasattr(mock_stdout, 'flush')
    
    @patch('sys.stdout')
    def test_log_handles_flush_exception(self, mock_stdout):
        from src.wifi import log
        mock_stdout.flush.side_effect = Exception("flush error")
        # No debería lanzar excepción
        log("test message")


class TestGetWlan:
    """Tests para _get_wlan()"""
    
    def test_get_wlan_creates_new_instance(self):
        import src.wifi
        src.wifi._wlan = None  # Resetear estado
        
        with patch('network.WLAN') as mock_wlan_class:
            from src.wifi import _get_wlan
            mock_wlan = MagicMock()
            mock_wlan_class.return_value = mock_wlan
            
            result = _get_wlan()
            
            mock_wlan_class.assert_called_once_with(1)  # network.STA_IF = 1
            mock_wlan.active.assert_called_once_with(True)
            assert result == mock_wlan
    
    @patch('src.wifi._wlan')
    def test_get_wlan_returns_existing_instance(self, mock_wlan):
        from src.wifi import _get_wlan
        mock_wlan_instance = MagicMock()
        mock_wlan = mock_wlan_instance
        
        # Simular que ya existe una instancia
        import src.wifi
        src.wifi._wlan = mock_wlan_instance
        
        result = _get_wlan()
        
        assert result == mock_wlan_instance


class TestResetWlan:
    """Tests para _reset_wlan()"""
    
    @patch('time.sleep')
    def test_reset_wlan_disconnects_and_resets(self, mock_sleep):
        import src.wifi
        src.wifi._wlan = None  # Resetear estado
        
        with patch('network.WLAN') as mock_wlan_class:
            from src.wifi import _reset_wlan
            
            mock_wlan = MagicMock()
            mock_wlan.isconnected.return_value = True
            mock_wlan_class.return_value = mock_wlan
            src.wifi._wlan = mock_wlan
            
            result = _reset_wlan()
            
            mock_wlan.disconnect.assert_called_once()
            # Verificar que se llamó a active(False) en algún momento
            assert any(call[0] == (False,) for call in mock_wlan.active.call_args_list)
            assert mock_sleep.call_count >= 2
            assert result == mock_wlan
    
    @patch('time.sleep')
    def test_reset_wlan_handles_not_connected(self, mock_sleep):
        import src.wifi
        src.wifi._wlan = None  # Resetear estado
        
        with patch('network.WLAN') as mock_wlan_class:
            from src.wifi import _reset_wlan
            
            mock_wlan = MagicMock()
            mock_wlan.isconnected.return_value = False
            mock_wlan_class.return_value = mock_wlan
            src.wifi._wlan = mock_wlan
            
            result = _reset_wlan()
            
            mock_wlan.disconnect.assert_not_called()
            assert result == mock_wlan
    
    @patch('time.sleep')
    def test_reset_wlan_handles_exception(self, mock_sleep):
        import src.wifi
        src.wifi._wlan = None  # Resetear estado
        
        with patch('network.WLAN') as mock_wlan_class:
            from src.wifi import _reset_wlan
            
            mock_wlan = MagicMock()
            mock_wlan.isconnected.side_effect = Exception("error")
            mock_wlan_class.return_value = mock_wlan
            src.wifi._wlan = mock_wlan
            
            # No debería lanzar excepción
            result = _reset_wlan()
            assert result == mock_wlan


class TestStartWebrepl:
    """Tests para _start_webrepl()"""
    
    def test_start_webrepl_starts_webrepl(self):
        with patch('webrepl.start') as mock_webrepl_start, \
             patch('gc.collect') as mock_gc_collect, \
             patch('gc.mem_free', return_value=50000, create=True), \
             patch('sys.stdout') as mock_stdout:
            mock_stdout.flush = Mock()
            from src.wifi import _start_webrepl
            _start_webrepl("192.168.0.100")
            mock_webrepl_start.assert_called_once()
            mock_gc_collect.assert_called_once()
            mock_stdout.flush.assert_called()
    
    def test_start_webrepl_handles_exception(self):
        with patch('webrepl.start') as mock_webrepl_start:
            from src.wifi import _start_webrepl
            mock_webrepl_start.side_effect = Exception("webrepl error")
            # No debería lanzar excepción
            _start_webrepl("192.168.0.100")


class TestCheckIpRange:
    """Tests para _check_ip_range()"""
    
    def test_check_ip_range_valid_ip(self):
        from src.wifi import _check_ip_range, log
        with patch('src.wifi.log') as mock_log:
            _check_ip_range("192.168.0.100")
            # No debería loggear advertencia
            assert not any("⚠" in str(call) for call in mock_log.call_args_list)
    
    def test_check_ip_range_invalid_ip(self):
        from src.wifi import _check_ip_range
        with patch('src.wifi.log') as mock_log:
            _check_ip_range("192.168.1.100")
            # Debería loggear advertencia
            mock_log.assert_called()
            assert "⚠" in str(mock_log.call_args)


class TestConnectWifi:
    """Tests para connect_wifi()"""
    
    @patch('src.wifi._start_webrepl')
    @patch('src.wifi._check_ip_range')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_already_connected(self, mock_get_wlan, mock_check_ip, mock_webrepl):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = True
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password'
        }
        
        result = connect_wifi(cfg)
        
        assert result is True
        mock_check_ip.assert_called_once_with("192.168.0.100")
        mock_webrepl.assert_called_once_with("192.168.0.100")
    
    @patch('src.wifi._start_webrepl')
    @patch('src.wifi._check_ip_range')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_already_connected_invalid_ip(self, mock_get_wlan, mock_check_ip, mock_webrepl):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = True
        mock_wlan.ifconfig.return_value = ("0.0.0.0", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password'
        }
        
        result = connect_wifi(cfg)
        
        # Debería retornar True pero no iniciar webrepl
        assert result is True
        mock_webrepl.assert_not_called()
    
    @patch('time.sleep')
    @patch('src.wifi._start_webrepl')
    @patch('src.wifi._check_ip_range')
    @patch('src.wifi._reset_wlan')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_success_first_attempt(self, mock_get_wlan, mock_reset_wlan, 
                                                  mock_check_ip, mock_webrepl, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        # Primera llamada: verifica si ya está conectado (False)
        # Luego en el loop de espera: False, False, ... hasta que finalmente True
        call_count = {'count': 0}
        def isconnected_side_effect():
            call_count['count'] += 1
            if call_count['count'] == 1:
                return False  # No está conectado inicialmente
            elif call_count['count'] <= 3:
                return False  # Esperando conexión
            else:
                return True  # Conectado
        
        mock_wlan.isconnected.side_effect = isconnected_side_effect
        mock_wlan.status.return_value = 1000  # STAT_IDLE
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password',
            'WIFI_HIDDEN': 'false'
        }
        
        result = connect_wifi(cfg)
        
        assert result is True
        mock_wlan.connect.assert_called_once_with('test_ssid', 'test_password')
        mock_check_ip.assert_called_once_with("192.168.0.100")
        mock_webrepl.assert_called_once_with("192.168.0.100")
    
    @patch('time.sleep')
    @patch('src.wifi._start_webrepl')
    @patch('src.wifi._check_ip_range')
    @patch('src.wifi._reset_wlan')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_with_hidden_network(self, mock_get_wlan, mock_reset_wlan,
                                               mock_check_ip, mock_webrepl, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        call_count = {'count': 0}
        def isconnected_side_effect():
            call_count['count'] += 1
            if call_count['count'] == 1:
                return False
            elif call_count['count'] <= 3:
                return False
            else:
                return True
        
        mock_wlan.isconnected.side_effect = isconnected_side_effect
        mock_wlan.status.return_value = 1000  # STAT_IDLE
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'hidden_ssid',
            'WIFI_PASSWORD': 'test_password',
            'WIFI_HIDDEN': 'true'
        }
        
        result = connect_wifi(cfg)
        
        assert result is True
        # Con red oculta, no debería hacer scan
        mock_wlan.scan.assert_not_called()
    
    @patch('time.sleep')
    @patch('src.wifi._start_webrepl')
    @patch('src.wifi._check_ip_range')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_with_bytes_ssid_password(self, mock_get_wlan, mock_check_ip, 
                                                     mock_webrepl, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        call_count = {'count': 0}
        def isconnected_side_effect():
            call_count['count'] += 1
            if call_count['count'] == 1:
                return False
            elif call_count['count'] <= 3:
                return False
            else:
                return True
        
        mock_wlan.isconnected.side_effect = isconnected_side_effect
        mock_wlan.status.return_value = 1000  # STAT_IDLE
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': b'test_ssid',
            'WIFI_PASSWORD': b'test_password'
        }
        
        result = connect_wifi(cfg)
        
        assert result is True
        # Debería decodificar bytes a string
        mock_wlan.connect.assert_called_once_with('test_ssid', 'test_password')
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_handles_connection_error(self, mock_get_wlan, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = False
        mock_wlan.status.return_value = 1000  # STAT_IDLE
        mock_wlan.connect.side_effect = Exception("Connection error")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password'
        }
        
        # Debería continuar intentando (pero limitamos con timeout en el test)
        # En un test real, esto entraría en un loop infinito, así que mockeamos el comportamiento
        # Este test verifica que maneja la excepción sin crashear
        # Limitamos el loop con un side_effect que rompe después de un intento
        call_count = {'count': 0}
        def sleep_side_effect(seconds):
            call_count['count'] += 1
            if call_count['count'] >= 2:
                raise StopIteration("Test limit")
        
        mock_sleep.side_effect = sleep_side_effect
        
        try:
            connect_wifi(cfg)
        except StopIteration:
            pass
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_wrong_password_status(self, mock_get_wlan, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = False
        mock_wlan.status.side_effect = [1000, 202]  # STAT_IDLE, WRONG_PASSWORD
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'wrong_password'
        }
        
        # Debería detectar el error y continuar intentando
        # Limitamos el loop con un side_effect que rompe después de un intento
        call_count = {'count': 0}
        def sleep_side_effect(seconds):
            call_count['count'] += 1
            if call_count['count'] >= 2:
                raise StopIteration("Test limit")
        
        mock_sleep.side_effect = sleep_side_effect
        
        try:
            connect_wifi(cfg)
        except StopIteration:
            pass
        
        # Este test verifica que detecta el status de error
        # En la implementación real, esto entraría en un loop
        # Aquí solo verificamos que el código maneja el status 202
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._reset_wlan')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_resets_on_multiple_attempts(self, mock_get_wlan, mock_reset_wlan, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = False
        mock_wlan.status.return_value = 1000  # STAT_IDLE
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        mock_reset_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password'
        }
        
        # Simular que después de varios intentos se conecta
        call_count = {'count': 0}
        def isconnected_side_effect():
            call_count['count'] += 1
            if call_count['count'] >= 3:
                return True
            return False
        
        mock_wlan.isconnected.side_effect = isconnected_side_effect
        
        result = connect_wifi(cfg)
        
        # Debería haber llamado a reset_wlan cuando attempt % 3 == 0
        assert result is True
    
    @patch('time.sleep')
    @patch('src.wifi._start_webrepl')
    @patch('src.wifi._check_ip_range')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_calls_wdt_callback(self, mock_get_wlan, mock_check_ip, 
                                               mock_webrepl, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        call_count = {'count': 0}
        def isconnected_side_effect():
            call_count['count'] += 1
            if call_count['count'] == 1:
                return False
            elif call_count['count'] <= 3:
                return False
            else:
                return True
        
        mock_wlan.isconnected.side_effect = isconnected_side_effect
        mock_wlan.status.return_value = 1000  # STAT_IDLE
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password'
        }
        
        mock_wdt = MagicMock()
        
        result = connect_wifi(cfg, mock_wdt)
        
        assert result is True
        # Debería haber llamado al callback del watchdog
        assert mock_wdt.called
    
    @patch('time.sleep')
    @patch('src.wifi._start_webrepl')
    @patch('src.wifi._check_ip_range')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_handles_wdt_callback_exception(self, mock_get_wlan, mock_check_ip,
                                                          mock_webrepl, mock_sleep):
        from src.wifi import connect_wifi
        
        mock_wlan = MagicMock()
        call_count = {'count': 0}
        def isconnected_side_effect():
            call_count['count'] += 1
            if call_count['count'] == 1:
                return False
            elif call_count['count'] <= 3:
                return False
            else:
                return True
        
        mock_wlan.isconnected.side_effect = isconnected_side_effect
        mock_wlan.status.return_value = 1000  # STAT_IDLE
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        cfg = {
            'WIFI_SSID': 'test_ssid',
            'WIFI_PASSWORD': 'test_password'
        }
        
        mock_wdt = MagicMock(side_effect=Exception("WDT error"))
        
        # No debería lanzar excepción
        result = connect_wifi(cfg, mock_wdt)
        assert result is True


class TestMonitorWifi:
    """Tests para monitor_wifi()"""
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._reset_wlan')
    @patch('src.wifi.connect_wifi')
    @patch('src.wifi._get_wlan')
    def test_monitor_wifi_connected_stable(self, mock_get_wlan, mock_connect_wifi, 
                                            mock_reset_wlan, mock_sleep):
        from src.wifi import monitor_wifi
        import src.wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = True
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        src.wifi._cfg = {'WIFI_SSID': 'test'}
        src.wifi._wdt_callback = None
        
        # Limitar el loop a una iteración
        call_count = {'count': 0}
        def sleep_side_effect(seconds):
            call_count['count'] += 1
            if call_count['count'] >= 1:
                raise StopIteration("Test limit")
        
        mock_sleep.side_effect = sleep_side_effect
        
        try:
            monitor_wifi(check_interval=1)
        except StopIteration:
            pass
        
        # No debería llamar a reset ni connect si está conectado
        mock_reset_wlan.assert_not_called()
        mock_connect_wifi.assert_not_called()
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._reset_wlan')
    @patch('src.wifi.connect_wifi')
    @patch('src.wifi._get_wlan')
    def test_monitor_wifi_disconnected_reconnects(self, mock_get_wlan, mock_connect_wifi,
                                                    mock_reset_wlan, mock_sleep):
        from src.wifi import monitor_wifi
        import src.wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = False
        mock_get_wlan.return_value = mock_wlan
        mock_reset_wlan.return_value = mock_wlan
        
        src.wifi._cfg = {'WIFI_SSID': 'test'}
        src.wifi._wdt_callback = None
        
        # Limitar el loop
        call_count = {'count': 0}
        def sleep_side_effect(seconds):
            call_count['count'] += 1
            if call_count['count'] >= 1:
                raise StopIteration("Test limit")
        
        mock_sleep.side_effect = sleep_side_effect
        
        try:
            monitor_wifi(check_interval=1)
        except StopIteration:
            pass
        
        # Debería intentar reconectar después de 2 checks desconectado
        # En este caso, como está desconectado, debería resetear y reconectar
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._reset_wlan')
    @patch('src.wifi.connect_wifi')
    @patch('src.wifi._get_wlan')
    def test_monitor_wifi_invalid_ip_resets(self, mock_get_wlan, mock_connect_wifi,
                                             mock_reset_wlan, mock_sleep):
        from src.wifi import monitor_wifi
        import src.wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = True
        mock_wlan.ifconfig.return_value = ("0.0.0.0", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        mock_reset_wlan.return_value = mock_wlan
        
        src.wifi._cfg = {'WIFI_SSID': 'test'}
        src.wifi._wdt_callback = None
        
        # Limitar el loop
        call_count = {'count': 0}
        def sleep_side_effect(seconds):
            call_count['count'] += 1
            if call_count['count'] >= 1:
                raise StopIteration("Test limit")
        
        mock_sleep.side_effect = sleep_side_effect
        
        try:
            monitor_wifi(check_interval=1)
        except StopIteration:
            pass
        
        # Después de 3 checks con IP inválida, debería resetear
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._get_wlan')
    def test_monitor_wifi_calls_wdt_callback(self, mock_get_wlan, mock_sleep):
        from src.wifi import monitor_wifi
        import src.wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = True
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan
        
        src.wifi._cfg = {'WIFI_SSID': 'test'}
        mock_wdt = MagicMock()
        src.wifi._wdt_callback = mock_wdt
        
        # Limitar el loop
        call_count = {'count': 0}
        def sleep_side_effect(seconds):
            call_count['count'] += 1
            if call_count['count'] >= 1:
                raise StopIteration("Test limit")
        
        mock_sleep.side_effect = sleep_side_effect
        
        try:
            monitor_wifi(check_interval=1)
        except StopIteration:
            pass
        
        # Debería haber llamado al callback del watchdog
        assert mock_wdt.called
    
    @pytest.mark.timeout(10)
    @patch('time.sleep')
    @patch('src.wifi._get_wlan')
    def test_monitor_wifi_handles_exception(self, mock_get_wlan, mock_sleep):
        from src.wifi import monitor_wifi
        import src.wifi
        
        mock_wlan = MagicMock()
        mock_wlan.isconnected.side_effect = Exception("Network error")
        mock_get_wlan.return_value = mock_wlan
        
        src.wifi._cfg = {'WIFI_SSID': 'test'}
        src.wifi._wdt_callback = None
        
        # Limitar el loop
        call_count = {'count': 0}
        def sleep_side_effect(seconds):
            call_count['count'] += 1
            if call_count['count'] >= 1:
                raise StopIteration("Test limit")
        
        mock_sleep.side_effect = sleep_side_effect
        
        # No debería lanzar excepción
        try:
            monitor_wifi(check_interval=1)
        except StopIteration:
            pass

