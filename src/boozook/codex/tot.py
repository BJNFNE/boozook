from collections.abc import Iterator
import io
import operator
from itertools import groupby
from pathlib import Path
from typing import Iterable
from boozook.archive import GameBase
from boozook.codex.cat import Language
from boozook.codex.replace_tot import extract_texts, replace_texts, save_lang_file
from boozook.totfile import fix_value, parse_text_data, read_tot, read_uint32le

from pakal.archive import ArchivePath


def empty_lang(group, lang):
    return all(line[lang] is None for line in group)


def compose(
    game: GameBase,
    lines: Iterable[tuple[str, dict[str, bytes | None]]],
) -> None:
    grouped = groupby(lines, key=operator.itemgetter(0))
    for tfname, group in grouped:
        basename = Path(tfname).name
        cgroup = [t for _, t in group]
        langs = list(cgroup[0].keys())
        for pattern, entry in game.search([basename]):
            texts = get_original_texts(game, entry)
            available_langs = [lang for lang in langs if not empty_lang(cgroup, lang)]
            backup = {
                lang: lang if lang in texts
                # else 'DAT'
                else next((alang for alang in available_langs if alang != lang))
                for lang in available_langs
            }
            new_texts = {
                lang: dict(
                    enumerate(replace_texts(iter(cgroup), texts[backup[lang]], lang))
                )
                for lang in available_langs
            }

            for lang, lang_text in new_texts.items():
                if lang == 'INT' and 'INT' not in texts:
                    continue
                with io.BytesIO() as lang_out:
                    save_lang_file(lang_out, lang_text)
                    new_texts_data = lang_out.getvalue()
                # assert texts_data == lang_text, (texts_data, lang_text)

                parsed = dict(enumerate(parse_text_data(new_texts_data)))
                assert parsed == lang_text, (parsed, lang_text)

                if lang != 'INT':
                    game.patch(
                        (
                            f'{Path(tfname).stem}.{lang}'
                            if lang in texts
                            else f'{Path(tfname).stem}.{backup[lang]}'
                        ),
                        new_texts_data,
                        f'{Path(tfname).stem}.{lang}',
                    )

                else:
                    orig_tot = bytearray(entry.read_bytes())
                    with io.BytesIO() as lang_out:
                        save_lang_file(lang_out, texts[backup[lang]])
                        texts_data = lang_out.getvalue()
                    assert texts_data in orig_tot, orig_tot
                    orig_tot = orig_tot.replace(texts_data, new_texts_data)
                    resoff = fix_value(read_uint32le(orig_tot[52:]), 0xFFFFFFFF, 0)
                    if resoff != 0:
                        orig_tot[52:56] = (
                            resoff + len(new_texts_data) - len(texts_data)
                        ).to_bytes(4, byteorder='little', signed=False)
                    game.patch(basename, bytes(orig_tot))
            break
        else:
            raise ValueError(f'entry {basename} was not found')


def get_original_texts(
    game: GameBase,
    entry: ArchivePath,
) -> dict[str, dict[int, tuple[int, int, bytes]]]:
    sources = {}
    with entry.open('rb') as stream:
        _, _, texts_data, res_data, _, _ = read_tot(stream)
    if texts_data:
        sources['INT'] = texts_data
    lang_patterns = [f'{entry.stem}.{ext.name}' for ext in Language]
    for pattern, lang_file in game.search(lang_patterns):
        sources[lang_file.suffix[1:]] = lang_file.read_bytes()

    return {
        source: dict(enumerate(parse_text_data(texts_data)))
        for source, texts_data in sources.items()
    }


def write_parsed(
    game: GameBase,
    entry: ArchivePath,
) -> Iterator[dict[str, bytes | None]]:
    texts = get_original_texts(game, entry)
    if not texts:
        return
    yield from extract_texts(texts)
