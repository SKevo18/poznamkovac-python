import typing as t

import json
import shutil

from pathlib import Path


KORENOVA_CESTA = Path(__file__).parent.absolute()
"""Koreňová cesta k zdrojovému kódu Poznámkovača"""

SABLONY_CESTA = KORENOVA_CESTA / "sablony"
"""Cesta ku Jinja2 šablónam"""
POZNAMKY_CESTA = KORENOVA_CESTA.parent / "poznamky"
"""Cesta k priečinku s poznámkami"""
VYSTUPNA_CESTA = KORENOVA_CESTA.parent / "site"
"""Výstupná cesta, t. j. kde budú umiestnené konvertované poznámky, HTML a statické súbory."""


from poznamkovac.konvertor import nacitat_json_konstanty, vytvorit_poznamky
from poznamkovac.sablony import ZAKLAD_POZNAMOK, konvertovat_sablonu
from poznamkovac.pojmova_mapa import vytvorit_pojmovu_mapu



def vycistit_docasne(vystupny_priecinok: Path) -> None:
    """
        Odstráni všetky súbory a priečinky, ktorých meno začína s podtržníkom, nakoľko sa jedná o dočasné súbory.
    """

    for cesta in vystupny_priecinok.rglob("_*"):
        if cesta.is_dir():
            shutil.rmtree(cesta)
        
        elif cesta.is_file():
            cesta.unlink()



def konvertovat_vsetky_poznamky(vystupny_priecinok: Path) -> None:
    """
        Konvertuje všetky súbory poznámok na HTML a vytvorí priečinok `site`, pripravený na publikovanie na web.

        - `vystupna_cesta` - cesta `site` priečinku. Tento priečinok už musí byť vytvorený a musí obsahovať všetky šablóny a poznámky (viz. `poznamkovac.sablony:kopirovat_sablony_a_poznamky`);
    """

    konstanty = nacitat_json_konstanty(vystupny_priecinok)

    zoznam_sablona = (vystupny_priecinok / '_zoznam.html').read_text(encoding='utf-8')
    poznamky_zaklad_sablona = ZAKLAD_POZNAMOK.read_text(encoding='utf-8')


    def _spracovat_priecinok(priecinok_cesta: Path) -> t.Optional[dict[tuple[str], list[dict[str, t.Any]]]]:
        if priecinok_cesta == vystupny_priecinok:
            kategorie = ('_',)
        else:
            kategorie = priecinok.relative_to(vystupny_priecinok).parts

        zoznam_poznamok: dict[tuple[str], list[dict[str, t.Any]]] = {}


        for subor_poznamok in priecinok_cesta.glob("*.md"):
            markdown_poznamky = subor_poznamok.read_text(encoding='utf-8')
            poznamky, metadata = vytvorit_poznamky(konvertovat_sablonu(markdown_poznamky, k=konstanty))


            html = konvertovat_sablonu(poznamky_zaklad_sablona,
                titulok=f"{' - '.join(kategorie)} {subor_poznamok.stem}",
                poznamky=poznamky,
                metadata=metadata,
                pojmova_mapa=json.dumps(vytvorit_pojmovu_mapu(markdown_poznamky)) if metadata.get("mapa", ["áno"])[0].lower() != "nie" else None
            )

            zoznam_poznamok.setdefault(kategorie, []).append({
                "nazov": subor_poznamok.stem,
                "popis": metadata.get("popis", [None])[0],
                "autori": metadata.get("autori", []),
                "href": f"/{subor_poznamok.relative_to(vystupny_priecinok).as_posix()}"
            })

            subor_poznamok.with_suffix('.html').write_text(html, encoding='utf-8')
            subor_poznamok.unlink()


        return zoznam_poznamok if zoznam_poznamok != {} else None


    zoznam_vsetkych_poznamok = []

    for priecinok in vystupny_priecinok.glob("**/"):
        if (zoznam_poznamok := _spracovat_priecinok(priecinok)) is not None:
            zoznam_vsetkych_poznamok.append(zoznam_poznamok)
            (priecinok / 'index.html').write_text(konvertovat_sablonu(zoznam_sablona, zoznam_poznamok=[zoznam_poznamok]), encoding='utf-8')


    (vystupny_priecinok / 'index.html').write_text(konvertovat_sablonu(zoznam_sablona, zoznam_poznamok=zoznam_vsetkych_poznamok), encoding='utf-8')
    vycistit_docasne(vystupny_priecinok)
