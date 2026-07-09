"""
Motore di validazione e decodifica del Codice Fiscale italiano.

Implementa l'algoritmo ufficiale (D.M. 12/03/1977 e successive modifiche)
per la validazione della struttura, il calcolo del CIN (carattere di controllo)
e la decodifica delle componenti anagrafiche.
"""

import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Tabelle mese
# ---------------------------------------------------------------------------
MONTHS: dict[str, str] = {
    'A': 'Gennaio',   'B': 'Febbraio',  'C': 'Marzo',
    'D': 'Aprile',    'E': 'Maggio',    'H': 'Giugno',
    'L': 'Luglio',    'M': 'Agosto',    'P': 'Settembre',
    'R': 'Ottobre',   'S': 'Novembre',  'T': 'Dicembre',
}

MONTH_NUM: dict[str, int] = {k: i + 1 for i, k in enumerate('ABCDEHLMPRST')}

# ---------------------------------------------------------------------------
# Tabelle per il calcolo del CIN (D.M. 12/03/1977)
# ---------------------------------------------------------------------------
ODD_VALUES: dict[str, int] = {
    '0': 1, '1': 0, '2': 5, '3': 7, '4': 9,
    '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
    'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9,
    'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
    'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11,
    'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
    'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23,
}

EVEN_VALUES: dict[str, int] = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
    '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4,
    'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
    'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14,
    'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19,
    'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25,
}

CHECK_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

VOWELS = set('AEIOU')
CONSONANTS = set('BCDFGHJKLMNPQRSTVWXYZ')

# ---------------------------------------------------------------------------
# Pattern regex per la validazione rapida
# ---------------------------------------------------------------------------
CF_PATTERN = re.compile(
    r'^[A-Z]{6}'          # cognome(3) + nome(3)
    r'\d{2}'               # anno
    r'[ABCDEHLMPRST]'      # mese
    r'(?:0[1-9]|[12]\d|3[01]|[4-7][0-9])'  # giorno (01-31 o 41-71)
    r'[A-Z]\d{3}'          # codice catastale (lettera + 3 cifre)
    r'[A-Z]$'              # CIN (carattere di controllo)
)

# ---------------------------------------------------------------------------
# Calcolo del carattere di controllo (CIN)
# ---------------------------------------------------------------------------
def calcola_cin(cf15: str) -> str:
    """Calcola il sedicesimo carattere di controllo dai primi 15."""
    totale = 0
    for i, c in enumerate(cf15):
        if i % 2 == 0:  # posizione dispari (1-indexed)
            totale += ODD_VALUES.get(c, 0)
        else:
            totale += EVEN_VALUES.get(c, 0)
    return CHECK_CHARS[totale % 26]


# ---------------------------------------------------------------------------
# Estrazione componenti nome/cognome per il codice
# ---------------------------------------------------------------------------
def _estrai_consonanti(s: str) -> list[str]:
    return [c for c in s.upper() if c in CONSONANTS]


def _estrai_vocali(s: str) -> list[str]:
    return [c for c in s.upper() if c in VOWELS]


def cognome_a_codice(cognome: str) -> str:
    """Converte un cognome nella tripletta del CF (posizioni 1-3)."""
    cons = _estrai_consonanti(cognome)
    vows = _estrai_vocali(cognome)
    code = ''.join((cons + vows)[:3])
    return code.ljust(3, 'X')


def nome_a_codice(nome: str) -> str:
    """Converte un nome nella tripletta del CF (posizioni 4-6)."""
    cons = _estrai_consonanti(nome)
    vows = _estrai_vocali(nome)

    if len(cons) >= 4:
        code_chars = [cons[0], cons[2], cons[3]] + vows
    else:
        code_chars = cons + vows

    code = ''.join(code_chars[:3])
    return code.ljust(3, 'X')


# ---------------------------------------------------------------------------
# Validazione completa
# ---------------------------------------------------------------------------
def valida_cf(cf: str) -> tuple[bool, list[str], str | None]:
    """
    Valida un codice fiscale italiano.

    Restituisce (valido, lista_errori, cf_normalizzato).
    """
    errori: list[str] = []
    cf = cf.strip().upper()

    # 1. Lunghezza
    if len(cf) != 16:
        errori.append(
            f"Lunghezza errata: il codice fiscale deve avere esattamente "
            f"16 caratteri (ne hai inseriti {len(cf)})."
        )
        return False, errori, None

    # 2. Caratteri consentiti
    if not re.match(r'^[A-Z0-9]{16}$', cf):
        errori.append(
            "Caratteri non validi: il codice fiscale può contenere solo "
            "lettere maiuscole (A-Z) e cifre (0-9)."
        )
        return False, errori, None

    # 3. Struttura con regex
    if not CF_PATTERN.match(cf):
        # Diamo messaggi più specifici
        if cf[8] not in MONTHS:
            errori.append(
                f"Mese non valido alla posizione 9: '{cf[8]}'. "
                f"I codici mese validi sono: A-L (esclusi F,G,I,K,N,O,Q) e M-T (esclusi N,O,Q)."
            )
        else:
            giorno = cf[9:11]
            try:
                g = int(giorno)
                if g > 71 or g == 0 or (31 < g < 41):
                    errori.append(
                        f"Giorno non valido alle posizioni 10-11: '{giorno}'. "
                        f"Deve essere tra 01 e 31 (uomini) o tra 41 e 71 (donne)."
                    )
                elif g > 31:
                    # female range — check valid day
                    d = g - 40
                    if d < 1 or d > 31:
                        errori.append(
                            f"Giorno non valido alle posizioni 10-11: '{giorno}' "
                            f"corrisponde al giorno {d} che non esiste."
                        )
            except ValueError:
                errori.append(f"Giorno non valido alle posizioni 10-11: '{giorno}'.")
        if not errori:
            errori.append("La struttura del codice fiscale non è valida.")
        return False, errori, None

    # 4. CIN
    atteso = calcola_cin(cf[:15])
    if cf[15] != atteso:
        errori.append(
            f"Carattere di controllo (CIN) non valido: "
            f"atteso '{atteso}', trovato '{cf[15]}'. "
            f"Verifica di aver inserito correttamente tutte le lettere e cifre."
        )
        return False, errori, None

    return True, [], cf


# ---------------------------------------------------------------------------
# Decodifica
# ---------------------------------------------------------------------------
def decodifica_cf(cf: str) -> dict:
    """
    Decodifica un codice fiscale valido estraendo tutti i dati anagrafici.

    Restituisce un dizionario con cognome derivato, nome derivato, anno,
    mese, giorno, sesso, codice catastale, data di nascita, CIN.
    """
    cf = cf.upper()

    cognome_part = cf[0:3]
    nome_part = cf[3:6]

    # Anno: determiniamo il secolo più probabile
    anno_short = int(cf[6:8])
    corrente = datetime.now().year
    soglia = int(str(corrente)[2:])
    if anno_short <= soglia:
        anno = 2000 + anno_short
    else:
        anno = 1900 + anno_short

    # Mese
    mese_char = cf[8]
    mese_nome = MONTHS[mese_char]
    mese_num = MONTH_NUM[mese_char]

    # Giorno e sesso
    giorno_code = int(cf[9:11])
    if giorno_code > 40:
        sesso = 'F'
        giorno = giorno_code - 40
    else:
        sesso = 'M'
        giorno = giorno_code

    # Codice catastale
    codice_catastale = cf[11:15]

    # CIN
    cin = cf[15]
    cin_atteso = calcola_cin(cf[:15])

    return {
        'codice_fiscale': cf,
        'cognome_derivato': cognome_part,
        'nome_derivato': nome_part,
        'anno': anno,
        'anno_corto': anno_short,
        'mese': mese_nome,
        'mese_numero': mese_num,
        'giorno': giorno,
        'sesso': 'Femmina' if sesso == 'F' else 'Maschio',
        'sesso_char': sesso,
        'codice_catastale': codice_catastale,
        'carattere_controllo': cin,
        'controllo_valido': cin == cin_atteso,
        'data_nascita': f"{giorno:02d}/{mese_num:02d}/{anno}",
    }
