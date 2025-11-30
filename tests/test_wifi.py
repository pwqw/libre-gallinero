import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock MicroPython modules
mock_network = MagicMock()
mock_network.STA_IF = 1
mock_network.AP_IF = 2
sys.modules['network'] = mock_network
sys.modules['webrepl'] = MagicMock()


class TestConnectWifiBasic:
    """Tests minimalistas para connect_wifi()"""

    @patch('src.wifi._get_wlan')
    @patch('network.WLAN')
    def test_connect_wifi_already_connected(self, mock_wlan_class, mock_get_wlan):
        """Test cuando WiFi ya está conectado"""
        from src.wifi import connect_wifi

        mock_wlan = MagicMock()
        mock_wlan.isconnected.return_value = True
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan

        mock_ap = MagicMock()
        mock_ap.active.return_value = False
        mock_wlan_class.return_value = mock_ap

        cfg = {'WIFI_SSID': 'test_ssid', 'WIFI_PASSWORD': 'test_password'}

        result = connect_wifi(cfg)

        assert result is True

    @patch('time.sleep')
    @patch('src.wifi._get_wlan')
    def test_connect_wifi_success(self, mock_get_wlan, mock_sleep):
        """Test conexión exitosa después de intentar"""
        from src.wifi import connect_wifi

        mock_wlan = MagicMock()
        call_count = {'count': 0}
        def isconnected_side_effect():
            call_count['count'] += 1
            return call_count['count'] > 2  # Conecta en tercer intento

        mock_wlan.isconnected.side_effect = isconnected_side_effect
        mock_wlan.status.return_value = 1000
        mock_wlan.ifconfig.return_value = ("192.168.0.100", "255.255.255.0", "192.168.0.1", "8.8.8.8")
        mock_get_wlan.return_value = mock_wlan

        cfg = {'WIFI_SSID': 'test_ssid', 'WIFI_PASSWORD': 'test_password', 'WIFI_HIDDEN': 'false'}

        result = connect_wifi(cfg)

        assert result is True
        # connect() se llama 2 veces: sin params (SDK cache) y con params
        assert mock_wlan.connect.call_count >= 1


class TestStartApFallback:
    """Tests para _start_ap_fallback()"""

    @patch('src.wifi._start_webrepl')
    @patch('src.wifi.log')
    @patch('network.WLAN')
    def test_start_ap_fallback_activates_ap(self, mock_wlan_class, mock_log, mock_webrepl):
        """Test que AP fallback se activa correctamente"""
        from src.wifi import _start_ap_fallback

        mock_ap = MagicMock()
        mock_ap.active.return_value = False
        mock_wlan_class.return_value = mock_ap

        cfg = {'WIFI_PASSWORD': 'test_password'}

        result = _start_ap_fallback(cfg)

        assert result is True
        mock_wlan_class.assert_called_once_with(2)  # AP_IF
        mock_ap.active.assert_called_once_with(True)
        mock_ap.config.assert_called_once_with(essid='Gallinero-Setup', password='test_password')
        mock_webrepl.assert_called_once_with('192.168.4.1')
