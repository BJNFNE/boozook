import os
from pathlib import Path

from boozook import archive
from boozook.codex import ext


GRAPHICS_PATTERNS = {
    '*.TOT': ('graphics', ext.parse, ext.compose),
}


def decode(game, patterns, target):
    for pattern, entry in game.search(patterns):
        _, parse, _ = patterns[pattern]
        parse(game, entry, target)


def encode(game, patterns, target):
    for pattern, entry in game.search(patterns):
        _, _, compose = patterns[pattern]
        compose(game, entry, target)
    game.rebuild()


def menu():
    import argparse

    parser = argparse.ArgumentParser(description='extract graphics from archive')
    parser.add_argument('directory', help='game directory to work on')
    parser.add_argument(
        '--rebuild',
        '-r',
        action='store_true',
        help='create modified game resource with the changes',
    )
    return parser.parse_args()


def main(gamedir, rebuild):
    patterns = GRAPHICS_PATTERNS

    target = Path('graphics')
    os.makedirs(target, exist_ok=True)

    game = archive.open_game(gamedir)
    if not rebuild:
        decode(game, patterns, target)
    else:
        encode(game, patterns, target)


if __name__ == '__main__':
    args = menu()

    main(args.directory, args.rebuild)
