"""Tests minimalistas para ampy_utils.py"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import sys

# Agregar tools/common al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools' / 'common'))

from ampy_utils import run_ampy, get_base_files_to_upload


class TestRunAmpy:
    """Tests para run_ampy()"""

    @patch('ampy_utils.subprocess.run')
    def test_run_ampy_success(self, mock_run):
        """Test ejecución exitosa de ampy"""
        mock_run.return_value = Mock(returncode=0, stderr='', stdout='')

        result = run_ampy(['--port', '/dev/ttyUSB0', 'put', 'file.py', 'file.py'])

        assert result is True
        mock_run.assert_called_once_with(
            ['ampy', '--port', '/dev/ttyUSB0', 'put', 'file.py', 'file.py'],
            capture_output=True,
            text=True,
            timeout=30
        )

    @patch('ampy_utils.subprocess.run')
    @patch('builtins.print')
    def test_run_ampy_failure(self, mock_print, mock_run):
        """Test cuando ampy falla"""
        mock_run.return_value = Mock(returncode=1, stderr='Error: Device not found', stdout='')

        result = run_ampy(['--port', '/dev/ttyUSB0', 'put', 'file.py', 'file.py'])

        assert result is False

    @patch('ampy_utils.subprocess.run')
    def test_run_ampy_timeout(self, mock_run):
        """Test cuando ampy timeout"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('ampy', 30)

        result = run_ampy(['--port', '/dev/ttyUSB0', 'put', 'file.py', 'file.py'], verbose=False)

        assert result is False


class TestGetBaseFilesToUpload:
    """Tests para get_base_files_to_upload()"""

    def test_get_base_files_returns_list(self):
        """Test que retorna lista de archivos base"""
        project_dir = Path(__file__).parent.parent

        files = get_base_files_to_upload(project_dir, include_app=False)

        assert isinstance(files, list)
        assert len(files) > 0

        # Verificar que incluye archivos críticos
        file_names = [item[1] for item in files if item[0] is not None]
        assert 'boot.py' in file_names
        assert 'main.py' in file_names
        assert 'logger.py' in file_names
        assert 'timezone.py' in file_names

    def test_get_base_files_includes_app(self):
        """Test que incluye app cuando se solicita"""
        project_dir = Path(__file__).parent.parent

        files = get_base_files_to_upload(project_dir, include_app=True, app_name='blink')

        # Verificar que incluye directorio de app
        items = [item[1] for item in files]
        assert any('blink' in str(item) for item in items)

    def test_get_base_files_format(self):
        """Test formato de retorno (tuplas con paths)"""
        project_dir = Path(__file__).parent.parent

        files = get_base_files_to_upload(project_dir, include_app=False)

        for item in files:
            assert isinstance(item, tuple)
            assert len(item) == 2
            # Puede ser (path, remote_name) o (None, "mkdir:dir")
            if item[0] is not None:
                assert Path(item[0]).exists() or 'mkdir:' in item[1]
