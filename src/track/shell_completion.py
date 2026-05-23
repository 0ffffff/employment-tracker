"""Click shell completion with track-specific bash/zsh behavior.

- Bash: quote plain values so role_text with spaces completes correctly.
- Bash/zsh: when Click returns no candidates, suppress default filename completion.
"""

from __future__ import annotations

from click.shell_completion import (
    BashComplete,
    ZshComplete,
    add_completion_class,
)

# Bash >= 4.4 template (derived from Click's _SOURCE_BASH).
_TRACK_SOURCE_BASH = """\
%(complete_func)s() {
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD \\
%(complete_var)s=bash_complete $1)

    if [ -z "$response" ]; then
        compopt +o default +o bashdefault +o dirnames 2>/dev/null || true
        return 0
    fi

    for completion in $response; do
        IFS=',' read -r type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=("$value")
        fi
    done

    return 0
}

%(complete_func)s_setup() {
    complete -o nosort -F %(complete_func)s %(prog_name)s
}

%(complete_func)s_setup;
"""

# Zsh template (derived from Click's _SOURCE_ZSH).
_TRACK_SOURCE_ZSH = """\
#compdef %(prog_name)s

%(complete_func)s() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[%(prog_name)s] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) \\
%(complete_var)s=zsh_complete %(prog_name)s)}")

    if [ -z "$response" ]; then
        _message ''
        return 0
    fi

    for type key descr in ${response}; do
        if [[ "$type" == "plain" ]]; then
            if [[ "$descr" == "_" ]]; then
                completions+=("$key")
            else
                completions_with_descriptions+=("$key":"$descr")
            fi
        elif [[ "$type" == "dir" ]]; then
            _path_files -/
        elif [[ "$type" == "file" ]]; then
            _path_files -f
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

if [[ $zsh_eval_context[-1] == loadautofunc ]]; then
    %(complete_func)s "$@"
else
    compdef %(complete_func)s %(prog_name)s
fi
"""


@add_completion_class
class TrackBashComplete(BashComplete):
    """Bash completion with quoted plain values and no filename fallback."""

    name = "bash"
    source_template = _TRACK_SOURCE_BASH


@add_completion_class
class TrackZshComplete(ZshComplete):
    """Zsh completion that does not fall through to path completion when empty."""

    name = "zsh"
    source_template = _TRACK_SOURCE_ZSH
