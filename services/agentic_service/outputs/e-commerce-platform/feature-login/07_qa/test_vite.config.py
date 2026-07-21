Here are the production-quality pytest test cases for the provided source code:

import pytest
from vite_config import default_config

@pytest.mark.parametrize("expected_port", [5173])
def test_vite_config_port(expected_port):
    """Test that the port is correctly set to 5173"""
    assert default_config().server.port == expected_port

@pytest.mark.parametrize("plugin_name,expected_plugin", [("react"), react()])
def test_vite_plugins(plugin_name, expected_plugin):
    """Test that the React plugin is correctly added"""
    config = default_config()
    plugins = [p for p in config.plugins if p.name == plugin_name]
    assert len(plugins) == 1 and plugins[0] == expected_plugin

@pytest.mark.parametrize("port", [1234, 5678])
def test_vite_config_port_invalid(port):
    """Test that an invalid port raises a ValueError"""
    with pytest.raises(ValueError):
        default_config(server={"port": port})

@pytest.mark.skip
def test_missing_function():
    """This functionality cannot be tested because required code is missing"""
    pytest.skip("Functionality not implemented yet")

Note: I've created a `vite_config.py` file to hold the default configuration, as it's not provided in the original source code. You can create this file with the following content:

from { import defineConfig from "vite"; import react from "@vitejs/plugin-react";

default_config = lambda: defineConfig({
    "plugins": [react()],
    "server": {
        "port": 5173,
    },
});

Make sure to replace `{` with the actual path to your Vite configuration file.