# Cursor Bite — Hotkey Parser Tests
# ============================================================
# parse_hotkey() turns a config string like "Ctrl+Alt+B" into the
# (modifiers, virtual_key_code) pair RegisterHotKey needs. It is pure —
# no window, no registration, no Windows call — so it is tested
# directly rather than only through a live registration.

import win32con

from infrastructure.os.hotkey_listener import parse_hotkey


class TestValidCombinations:
    def test_default_hotkey(self):
        modifiers, vk = parse_hotkey("Ctrl+Alt+B")
        assert modifiers == (win32con.MOD_CONTROL | win32con.MOD_ALT)
        assert vk == 0x42

    def test_single_modifier_plus_letter(self):
        modifiers, vk = parse_hotkey("Ctrl+T")
        assert modifiers == win32con.MOD_CONTROL
        assert vk == 0x54

    def test_three_modifiers(self):
        modifiers, vk = parse_hotkey("Ctrl+Shift+Alt+Q")
        assert modifiers == (win32con.MOD_CONTROL | win32con.MOD_SHIFT | win32con.MOD_ALT)
        assert vk == 0x51

    def test_win_modifier(self):
        modifiers, vk = parse_hotkey("Win+C")
        assert modifiers == win32con.MOD_WIN
        assert vk == 0x43

    def test_function_key(self):
        modifiers, vk = parse_hotkey("Ctrl+F5")
        assert modifiers == win32con.MOD_CONTROL
        assert vk == 0x74

    def test_digit_key(self):
        modifiers, vk = parse_hotkey("Alt+1")
        assert modifiers == win32con.MOD_ALT
        assert vk == 0x31

    def test_named_key(self):
        modifiers, vk = parse_hotkey("Ctrl+Space")
        assert modifiers == win32con.MOD_CONTROL
        assert vk == 0x20

    def test_alternate_spelling_control(self):
        modifiers, vk = parse_hotkey("Control+Alt+B")
        assert modifiers == (win32con.MOD_CONTROL | win32con.MOD_ALT)

    def test_case_insensitive(self):
        modifiers, vk = parse_hotkey("ctrl+alt+b")
        assert modifiers == (win32con.MOD_CONTROL | win32con.MOD_ALT)
        assert vk == 0x42

    def test_whitespace_is_tolerated(self):
        modifiers, vk = parse_hotkey(" Ctrl + Alt + B ")
        assert modifiers == (win32con.MOD_CONTROL | win32con.MOD_ALT)
        assert vk == 0x42


class TestInvalidCombinations:
    def test_empty_string(self):
        assert parse_hotkey("") is None

    def test_none_like_empty(self):
        assert parse_hotkey(None) is None

    def test_modifier_only(self):
        """No key at all — needs at least modifier+key."""
        assert parse_hotkey("Ctrl") is None

    def test_key_only_with_no_modifier(self):
        """A single token can't distinguish a bare key from a typo."""
        assert parse_hotkey("B") is None

    def test_unknown_key_name(self):
        assert parse_hotkey("Ctrl+Alt+NotAKey") is None

    def test_unknown_modifier_name(self):
        assert parse_hotkey("Super+B") is None

    def test_multiple_keys_uses_the_last_one(self):
        """Documented behaviour: ambiguous input degrades, it doesn't crash."""
        modifiers, vk = parse_hotkey("Ctrl+B+C")
        assert vk == 0x43
