import json
import os
import tkinter as tk
from typing import Dict, assert_type

type SettingValue = None|bool|int|float|str

_settings_cache = None
_data_path = os.path.abspath('./data/')
_settings_path = os.path.join(_data_path, 'settings.json')
_setting_bindings: dict[str, list[object]] = {}

def get_setting(setting: str, default: SettingValue) -> SettingValue:
    assert_type(setting, str)
    assert_type(default, SettingValue)
    if not _load_settings():
        return default
    value = _settings_cache.get(setting, default)
    if type(value) != type(default):
        if set_setting(setting, default):
            return default
    return value

def set_setting(setting: str, value: SettingValue) -> bool:
    assert_type(setting, str)
    assert_type(value, SettingValue)
    if not _load_settings():
        return False
    _settings_cache[setting] = value
    if _save_settings():
        _update_bound_variables(setting, value)
        return True
    return False

def reset_setting(setting: str) -> bool:
    assert_type(setting, str)
    if not _load_settings():
        return False
    _settings_cache.pop(setting, None)
    return True

def reset_all_settings() -> bool:
    if not _load_settings():
        return False
    _settings_cache.clear()
    return _save_settings()

def apply_settings_from_file(path: str) -> bool:
    assert_type(path, str)
    if not _load_settings():
        return False
    try:
        with open(path, 'r', encoding='utf-8') as file:
            settings = json.load(file)
        if isinstance(settings, dict):
            for setting, value in settings.items():
                _settings_cache[setting] = value
                _update_bound_variables(setting, value)
            return _save_settings()
        else:
            return False
    except:
        return False

def bind_to_setting(variable: object, setting: str, default: SettingValue) -> bool:
    assert_type(setting, str)
    assert_type(default, SettingValue)
    if _setting_bindings.get(setting) == None:
        _setting_bindings[setting] = []
    _setting_bindings[setting].append(variable)
    return _update_variable(variable, get_setting(setting, default))

def bind_tkinter_variable_to_setting(variable: tk.Variable, setting: str, default: SettingValue) -> tk.Variable:
    assert_type(variable, tk.Variable)
    assert_type(setting, str)
    assert_type(default, SettingValue)
    bind_to_setting(variable, setting, default)
    return variable

def _generate_new_settings_file() -> bool:
    global _settings_cache
    try:
        if not os.path.exists(_data_path):
            os.mkdir(_data_path)
        with open(_settings_path, 'w') as file:
            json.dump("{}", file)
        _settings_cache = {}
    except:
        raise RuntimeError("Failed to create 'data/settings.json' file.")
    finally:
        _settings_cache = None

def _save_settings() -> bool:
    if _settings_cache == None:
        return False
    try:
        with open(_settings_path, 'w', encoding='utf8') as file:
            json.dump(_settings_cache, file, indent=4, sort_keys=True)
        return True
    except:
        return False

def _load_settings() -> bool:
    global _settings_cache
    if _settings_cache != None:
        return True
    try:
        with open(_settings_path, 'r', encoding='utf8') as file:
            settings = json.load(file)
        _settings_cache = settings
        return True
    except OSError:
        return _generate_new_settings_file()
    except RuntimeError as e:
        return _generate_new_settings_file()
    except Exception as e:
        return _generate_new_settings_file()

def _update_bound_variables(setting: str, value: SettingValue) -> bool:
    assert_type(setting, str)
    assert_type(value, SettingValue)
    success = True
    if _setting_bindings.get(setting) != None:
        for variable in _setting_bindings[setting]:
            success = min(success, _update_variable(variable, value))
    return success

def _update_variable(variable: object, value: SettingValue) -> bool:
    assert_type(value, SettingValue)
    if isinstance(variable, tk.Variable):
        variable.set(value)
    elif isinstance(variable, tuple[dict[str, object], str]):
        variable[0][variable[1]] = value
    else:
        return False
    return True
