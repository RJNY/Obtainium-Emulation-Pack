"""Styled argparse help formatter with ANSI colors."""

import argparse
import re
import sys

BOLD = "\033[1m"
DIM = "\033[2m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RESET = "\033[0m"

ANSI_ESCAPE = re.compile(r"\033\[[0-9;]*m")


def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _visible_len(s: str) -> int:
    return len(ANSI_ESCAPE.sub("", s))


class StyledHelpFormatter(argparse.HelpFormatter):

    def __init__(self, prog: str, **kwargs) -> None:
        kwargs.setdefault("max_help_position", 36)
        super().__init__(prog, **kwargs)
        self._color = _supports_color()

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = "usage: "
        if self._color:
            prefix = f"{YELLOW}{prefix}{RESET}"
        return super()._format_usage(usage, actions, groups, prefix)

    def start_section(self, heading):
        if self._color and heading:
            heading = f"{BOLD}{heading}{RESET}"
        super().start_section(heading)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            # Positional arg: just the metavar
            result = self._metavar_formatter(action, action.dest)(1)[0]
            if self._color:
                result = f"{CYAN}{result}{RESET}"
            return result

        # Sort: short flags (-v) before long flags (--version)
        short = [s for s in action.option_strings if not s.startswith("--")]
        long = [s for s in action.option_strings if s.startswith("--")]
        parts = short + long

        # Append metavar once at the end (not after each flag)
        if action.nargs != 0:
            metavar = self._metavar_formatter(action, action.dest.upper())(1)[0]
            result = ", ".join(parts) + " " + metavar
        else:
            result = ", ".join(parts)

        # Pad with leading spaces when no short flag, to align with those that have one
        if not short:
            result = "    " + result

        if self._color:
            result = f"{GREEN}{result}{RESET}"
        return result

    def _format_action(self, action):
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # Use visible length (ignoring ANSI codes) for layout decisions
        visible = _visible_len(action_header) if self._color else len(action_header)

        indent_first = 0
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
        elif visible <= action_width:
            # Pad based on visible width so columns align despite ANSI codes
            ansi_pad = len(action_header) - visible
            tup = self._current_indent, '', action_width + ansi_pad, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        parts = [action_header]

        if action.help and action.help.strip():
            help_text = self._expand_help(action)
            if help_text:
                if self._color:
                    help_text = f"{DIM}{help_text}{RESET}"
                help_lines = self._split_lines(help_text, help_width)
                parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
                for line in help_lines[1:]:
                    parts.append('%*s%s\n' % (help_position, '', line))
        elif not action_header.endswith('\n'):
            parts.append('\n')

        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        return self._join_parts(parts)
