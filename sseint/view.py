"""Curses front end for ViewModel.

Deliberately thin. Everything that decides what is on screen is in
viewmodel.py and tested there; this file only draws and translates
keys.

Keys:
    j / k / arrows   move
    g / G            top / follow the tail
    n / p            next / previous exchange
    /                filter, Enter to apply, empty to clear
    r                toggle regex filtering
    t                show only frames a rule touched
    c                toggle keep-alive comments
    s                timing summary
    a                reassembled message
    f                re-enter follow mode
    q                quit
"""
from __future__ import annotations

import curses

from sseint.viewmodel import ViewModel


def run(exchanges):
    curses.wrapper(lambda scr: _loop(scr, exchanges))


def _loop(scr, exchanges):
    curses.use_default_colors()
    scr.timeout(250)
    vm = ViewModel(exchanges)
    pane = None
    prompt = None
    while True:
        height, width = scr.getmaxyx()
        vm.height = max(1, height - 4)
        scr.erase()
        _draw(scr, vm, pane, prompt, height, width)
        scr.refresh()
        try:
            key = scr.get_wch()
        except curses.error:
            continue
        if prompt is not None:
            prompt, done = _edit(prompt, key)
            if done:
                vm.set_filter(text=prompt or "")
                prompt = None
            continue
        if key in ("q", "\x1b"):
            return
        pane = _key(vm, key, pane)
        if key == "/":
            prompt = vm.filter.text


def _key(vm, key, pane):
    if key in ("j", curses.KEY_DOWN):
        vm.move(1)
    elif key in ("k", curses.KEY_UP):
        vm.move(-1)
    elif key == curses.KEY_NPAGE:
        vm.move(vm.height)
    elif key == curses.KEY_PPAGE:
        vm.move(-vm.height)
    elif key == "g":
        vm.selected = 0
        vm.top = 0
        vm.follow = False
    elif key in ("G", "f"):
        vm.follow = True
    elif key == "n":
        vm.next_exchange()
    elif key == "p":
        vm.prev_exchange()
    elif key == "r":
        vm.set_filter(regex=not vm.filter.regex)
    elif key == "t":
        vm.set_filter(touched_only=not vm.filter.touched_only)
    elif key == "c":
        vm.set_filter(kinds=set() if vm.filter.kinds else {"event"})
    elif key == "s":
        return None if pane == "summary" else "summary"
    elif key == "a":
        return None if pane == "message" else "message"
    return pane


def _edit(prompt, key):
    if key in ("\n", "\r", curses.KEY_ENTER):
        return prompt, True
    if key in ("\x7f", curses.KEY_BACKSPACE):
        return prompt[:-1], False
    if isinstance(key, str) and key.isprintable():
        return prompt + key, False
    return prompt, False


def _draw(scr, vm, pane, prompt, height, width):
    _addstr(scr, 0, 0, vm.status()[:width - 1], curses.A_REVERSE)
    if pane == "summary":
        body = vm.summary()
    elif pane == "message":
        body = vm.reassembled().split("\n")
    else:
        body = [vm.line(f, ops, width - 10)
                for f, ops in vm.visible()]
    for i, line in enumerate(body[:height - 3]):
        _addstr(scr, 1 + i, 0, line[:width - 1])
    if pane is None:
        detail = vm.detail()
        row = height - 2 - min(len(detail), 3)
        _addstr(scr, row - 1, 0, "-" * (width - 1))
        for i, line in enumerate(detail[:3]):
            _addstr(scr, row + i, 0, line[:width - 1])
    footer = (f"/{prompt}" if prompt is not None
              else "j/k move  n/p exchange  / filter  t touched  "
                   "s summary  a message  q quit")
    _addstr(scr, height - 1, 0, footer[:width - 1], curses.A_REVERSE)


def _addstr(scr, y, x, text, attr=0):
    """curses raises at the bottom-right cell. It is not interesting."""
    try:
        scr.addstr(y, x, text, attr)
    except curses.error:
        pass
