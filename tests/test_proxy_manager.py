"""
Tests for core.proxy_manager module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os


class TestProxyManager:
    """Test proxy manager functions"""

    def test_get_proxy_url_from_env(self):
        with patch.dict(os.environ, {'HTTPS_PROXY': 'http://proxy.example.com:8080'}):
            from core.proxy_manager import get_proxy_url
            result = get_proxy_url()
            assert result == 'http://proxy.example.com:8080'

    def test_get_proxy_url_from_http_env(self):
        with patch.dict(os.environ, {'HTTP_PROXY': 'http://proxy.example.com:8080'}, clear=False):
            # Clear HTTPS_PROXY if set
            env = os.environ.copy()
            env.pop('HTTPS_PROXY', None)
            env['HTTP_PROXY'] = 'http://proxy.example.com:8080'
            with patch.dict(os.environ, env, clear=True):
                from core.proxy_manager import get_proxy_url
                result = get_proxy_url()
                assert result == 'http://proxy.example.com:8080'

    def test_get_proxy_url_none(self):
        env = os.environ.copy()
        env.pop('HTTP_PROXY', None)
        env.pop('HTTPS_PROXY', None)
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)
        with patch.dict(os.environ, env, clear=True):
            from core.proxy_manager import get_proxy_url
            result = get_proxy_url()
            assert result is None

    def test_get_proxy_dict_with_proxy(self):
        with patch.dict(os.environ, {'HTTPS_PROXY': 'http://proxy.example.com:8080'}):
            from core.proxy_manager import get_proxy_dict
            result = get_proxy_dict()
            assert result == {'http': 'http://proxy.example.com:8080', 'https': 'http://proxy.example.com:8080'}

    def test_get_proxy_dict_without_proxy(self):
        env = os.environ.copy()
        env.pop('HTTP_PROXY', None)
        env.pop('HTTPS_PROXY', None)
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)
        with patch.dict(os.environ, env, clear=True):
            from core.proxy_manager import get_proxy_dict
            result = get_proxy_dict()
            assert result is None

    @patch('core.proxy_manager.winreg')
    def test_setup_proxy_windows_enabled(self, mock_winreg):
        from core.proxy_manager import setup_proxy

        # Clear environment variables
        env = os.environ.copy()
        env.pop('HTTP_PROXY', None)
        env.pop('HTTPS_PROXY', None)
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)

        with patch.dict(os.environ, env, clear=True):
            # Mock registry
            mock_key = Mock()
            mock_winreg.OpenKey.return_value = mock_key
            mock_winreg.QueryValueEx.side_effect = lambda key, name: {
                "ProxyEnable": (1, None),
                "ProxyServer": ("proxy.example.com:8080", None)
            }[name]

            result = setup_proxy()
            assert result == "http://proxy.example.com:8080"

    @patch('core.proxy_manager.winreg')
    def test_setup_proxy_windows_disabled(self, mock_winreg):
        from core.proxy_manager import setup_proxy

        # Clear environment variables
        env = os.environ.copy()
        env.pop('HTTP_PROXY', None)
        env.pop('HTTPS_PROXY', None)
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)

        with patch.dict(os.environ, env, clear=True):
            # Mock registry
            mock_key = Mock()
            mock_winreg.OpenKey.return_value = mock_key
            mock_winreg.QueryValueEx.side_effect = lambda key, name: {
                "ProxyEnable": (0, None),
            }[name]

            result = setup_proxy()
            assert result is None

    @patch('core.proxy_manager.winreg')
    def test_setup_proxy_exception(self, mock_winreg):
        from core.proxy_manager import setup_proxy

        # Clear environment variables
        env = os.environ.copy()
        env.pop('HTTP_PROXY', None)
        env.pop('HTTPS_PROXY', None)
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)

        with patch.dict(os.environ, env, clear=True):
            # Mock registry exception
            mock_winreg.OpenKey.side_effect = Exception("Registry error")

            result = setup_proxy()
            assert result is None

    def test_setup_proxy_existing_env(self):
        with patch.dict(os.environ, {'HTTP_PROXY': 'http://existing.proxy.com:8080'}):
            from core.proxy_manager import setup_proxy
            result = setup_proxy()
            assert result == 'http://existing.proxy.com:8080'