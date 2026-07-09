"""
Test suite per il validatore di codici fiscali.

Copre:
- Calcolo del CIN
- Codifica nome/cognome
- Validazione struttura (lunghezza, caratteri, CIN)
- Decodifica componenti
- Ricerca comuni nel database
- Casi limite
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cf_engine import (
    valida_cf,
    decodifica_cf,
    calcola_cin,
    cognome_a_codice,
    nome_a_codice,
    MONTHS,
)
from comuni_data import COMUNI


# ---- Helpers ----
def build_cf(cognome, nome, anno, mese, giorno, catastale) -> str:
    """Costruisce un CF valido a partire dalle componenti."""
    cf15 = (
        cognome_a_codice(cognome)
        + nome_a_codice(nome)
        + anno
        + mese
        + giorno
        + catastale
    )
    return cf15 + calcola_cin(cf15)


class TestCINCalculation(unittest.TestCase):
    """Test del calcolo del carattere di controllo (CIN)."""

    def test_cin_rossi_mario(self):
        """RSSMRA80A01H501 ha CIN = U (verificato con algoritmo standard)."""
        self.assertEqual(calcola_cin("RSSMRA80A01H501"), "U")

    def test_cin_verdi_anna(self):
        """VRDNNA85B51H501 ha CIN = M."""
        self.assertEqual(calcola_cin("VRDNNA85B51H501"), "M")

    def test_cin_is_alpha(self):
        """Il CIN è sempre una lettera A-Z."""
        cf15 = "RSSMRA80A01H501"
        result = calcola_cin(cf15)
        self.assertIn(result, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def test_cin_consistency(self):
        """Calcoli ripetuti danno lo stesso risultato."""
        cf15 = "RSSMRA80A01H501"
        self.assertEqual(calcola_cin(cf15), calcola_cin(cf15))

    def test_cin_known_pairs(self):
        """Test di coppie CF15/CIN note e verificate."""
        pairs = [
            ("RSSMRA80A01H501", "U"),
            ("VRDNNA85B51H501", "M"),
            ("BNCMRA80A01H501", "A"),
        ]
        for cf15, expected in pairs:
            with self.subTest(cf15=cf15):
                self.assertEqual(calcola_cin(cf15), expected)


class TestNameEncoding(unittest.TestCase):
    """Test della codifica nome/cognome per le prime 6 lettere del CF."""

    def test_cognome_rossi(self):
        self.assertEqual(cognome_a_codice("ROSSI"), "RSS")

    def test_cognome_short(self):
        self.assertEqual(cognome_a_codice("RE"), "REX")

    def test_cognome_single(self):
        self.assertEqual(cognome_a_codice("A"), "AXX")

    def test_cognome_no_consonants(self):
        self.assertEqual(cognome_a_codice("AIA"), "AIA")

    def test_nome_mario(self):
        self.assertEqual(nome_a_codice("MARIO"), "MRA")

    def test_nome_francesco(self):
        """4+ consonanti: salta la seconda consonante."""
        # FRANCESCO → F,R,N,C,S,C → prendi 1a, 3a, 4a = F,N,C
        self.assertEqual(nome_a_codice("FRANCESCO"), "FNC")

    def test_nome_short(self):
        self.assertEqual(nome_a_codice("BO"), "BOX")

    def test_nome_anna(self):
        self.assertEqual(nome_a_codice("ANNA"), "NNA")

    def test_nome_verdi(self):
        self.assertEqual(cognome_a_codice("VERDI"), "VRD")


class TestCFValidation(unittest.TestCase):
    """Test della validazione completa del codice fiscale."""

    def test_empty(self):
        valido, errori, _ = valida_cf("")
        self.assertFalse(valido)
        self.assertTrue(any("16" in e for e in errori))

    def test_too_short(self):
        valido, errori, _ = valida_cf("RSSMRA80")
        self.assertFalse(valido)

    def test_too_long(self):
        valido, errori, _ = valida_cf("RSSMRA80A01H501XX")
        self.assertFalse(valido)

    def test_invalid_chars(self):
        valido, errori, _ = valida_cf("RSSMRA80A01H501!")
        self.assertFalse(valido)

    def test_lowercase_accepted(self):
        cf = build_cf("ROSSI", "MARIO", "80", "A", "01", "H501")
        valido, _, cf_norm = valida_cf(cf.lower())
        self.assertTrue(valido)
        self.assertEqual(cf_norm, cf.upper())

    def test_spaces_trimmed(self):
        cf = build_cf("ROSSI", "MARIO", "80", "A", "01", "H501")
        valido, _, cf_norm = valida_cf(f"  {cf}  ")
        self.assertTrue(valido)

    def test_invalid_month(self):
        cf15 = "RSSMRA80Z01H501"
        cin = calcola_cin(cf15)
        valido, errori, _ = valida_cf(cf15 + cin)
        self.assertFalse(valido)
        self.assertTrue(any("Mese" in e for e in errori))

    def test_invalid_day_zero(self):
        cf15 = "RSSMRA80A00H501"
        cin = calcola_cin(cf15)
        valido, errori, _ = valida_cf(cf15 + cin)
        self.assertFalse(valido)

    def test_invalid_day_range(self):
        cf15 = "RSSMRA80A35H501"
        cin = calcola_cin(cf15)
        valido, errori, _ = valida_cf(cf15 + cin)
        self.assertFalse(valido)

    def test_invalid_cin(self):
        """Altera il CIN e verifica che venga rilevato."""
        cf_ok = build_cf("ROSSI", "MARIO", "80", "A", "01", "H501")
        # Cambia l'ultima lettera
        cf_wrong = cf_ok[:-1] + ("A" if cf_ok[-1] != "A" else "B")
        valido, errori, _ = valida_cf(cf_wrong)
        self.assertFalse(valido)
        self.assertTrue(any("controllo" in e.lower() for e in errori))


class TestCFDecoding(unittest.TestCase):
    """Test della decodifica di codici validi."""

    def test_decode_male(self):
        """Decodifica maschile (giorno <= 31)."""
        cf = build_cf("ROSSI", "MARIO", "80", "A", "01", "H501")
        valido, _, cf_norm = valida_cf(cf)
        self.assertTrue(valido)

        dati = decodifica_cf(cf_norm)
        self.assertEqual(dati["cognome_derivato"], "RSS")
        self.assertEqual(dati["nome_derivato"], "MRA")
        self.assertEqual(dati["giorno"], 1)
        self.assertEqual(dati["mese"], "Gennaio")
        self.assertEqual(dati["mese_numero"], 1)
        self.assertEqual(dati["anno"], 1980)
        self.assertEqual(dati["sesso"], "Maschio")
        self.assertEqual(dati["sesso_char"], "M")
        self.assertEqual(dati["codice_catastale"], "H501")

    def test_decode_female(self):
        """Decodifica femminile (giorno > 40)."""
        cf = build_cf("VERDI", "ANNA", "85", "B", "51", "H501")
        valido, _, cf_norm = valida_cf(cf)
        self.assertTrue(valido)

        dati = decodifica_cf(cf_norm)
        self.assertEqual(dati["giorno"], 11)
        self.assertEqual(dati["sesso"], "Femmina")
        self.assertEqual(dati["sesso_char"], "F")
        self.assertEqual(dati["mese"], "Febbraio")

    def test_decode_2000_year(self):
        """Anno 2000+."""
        cf = build_cf("ROSSI", "MARIO", "05", "A", "01", "H501")
        valido, _, cf_norm = valida_cf(cf)
        self.assertTrue(valido)

        dati = decodifica_cf(cf_norm)
        self.assertEqual(dati["anno"], 2005)
        self.assertEqual(dati["anno_corto"], 5)

    def test_all_months(self):
        """Verifica tutti i 12 mesi."""
        for mese_char in "ABCDEHLMPRST":
            cf = build_cf("ROSSI", "MARIO", "80", mese_char, "01", "H501")
            valido, errori, _ = valida_cf(cf)
            self.assertTrue(valido, f"Mese {mese_char}: errori={errori}")


class TestComuniDatabase(unittest.TestCase):
    """Test del database dei comuni italiani."""

    def test_has_roma(self):
        self.assertIn("H501", COMUNI)
        self.assertEqual(COMUNI["H501"], "Roma")

    def test_has_milano(self):
        self.assertIn("F205", COMUNI)
        self.assertEqual(COMUNI["F205"], "Milano")

    def test_has_napoli(self):
        self.assertIn("F839", COMUNI)
        self.assertEqual(COMUNI["F839"], "Napoli")

    def test_major_cities(self):
        """Verifica 10+ capoluoghi di provincia con i codici corretti."""
        cities = {
            "H501": "Roma",
            "F205": "Milano",
            "F839": "Napoli",
            "L219": "Torino",
            "G273": "Palermo",
            "D969": "Genova",
            "A944": "Bologna",
            "D612": "Firenze",
            "A662": "Bari",
            "C351": "Catania",
            "L736": "Venezia",
            "A345": "L'Aquila",
        }
        for code, name in cities.items():
            with self.subTest(code=code):
                self.assertIn(code, COMUNI, f"Codice {code} ({name}) non trovato")
                self.assertEqual(COMUNI[code], name,
                                 f"Atteso {name}, trovato {COMUNI[code]}")

    def test_database_size(self):
        """Almeno 200 comuni nel database."""
        self.assertGreater(len(COMUNI), 200,
                           f"Solo {len(COMUNI)} comuni trovati")

    def test_all_codes_4_chars(self):
        """Tutti i codici catastali devono essere di 4 caratteri."""
        for code in COMUNI:
            self.assertEqual(len(code), 4,
                             f"Codice '{code}' non è di 4 caratteri")


class TestFiscalCodeFlow(unittest.TestCase):
    """Test end-to-end del flusso completo."""

    def test_valid_cf_roma(self):
        """Valida, decodifica e cerca comune per un CF di Roma."""
        cf = build_cf("ROSSI", "MARIO", "80", "A", "01", "H501")
        valido, errori, cf_norm = valida_cf(cf)
        self.assertTrue(valido, f"CF {cf} non valido: {errori}")

        dati = decodifica_cf(cf_norm)
        self.assertEqual(dati["codice_catastale"], "H501")
        self.assertEqual(COMUNI.get("H501"), "Roma")

    def test_build_and_validate_cycle(self):
        """Costruisce un CF da componenti e lo valida."""
        cf = build_cf("VERDI", "ANNA", "85", "B", "51", "H501")
        valido, errori, _ = valida_cf(cf)
        self.assertTrue(valido, f"CF {cf} non valido: {errori}")

    def test_multiple_cities(self):
        """Test CF con diversi codici catastali di comuni noti."""
        tests = [
            ("ROSSI", "MARIO", "80", "A", "01", "F205", "Milano"),
            ("ROSSI", "MARIO", "80", "A", "01", "F839", "Napoli"),
            ("ROSSI", "MARIO", "80", "A", "01", "L219", "Torino"),
            ("ROSSI", "MARIO", "80", "A", "01", "D612", "Firenze"),
            ("ROSSI", "MARIO", "80", "A", "01", "A944", "Bologna"),
            ("ROSSI", "MARIO", "80", "A", "01", "D969", "Genova"),
            ("ROSSI", "MARIO", "80", "A", "01", "A662", "Bari"),
            ("ROSSI", "MARIO", "80", "A", "01", "C351", "Catania"),
            ("ROSSI", "MARIO", "80", "A", "01", "L736", "Venezia"),
            ("ROSSI", "MARIO", "80", "A", "01", "A345", "L'Aquila"),
        ]
        for cognome, nome, anno, mese, giorno, catastale, comune_atteso in tests:
            with self.subTest(catastale=catastale):
                cf = build_cf(cognome, nome, anno, mese, giorno, catastale)
                valido, errori, cf_norm = valida_cf(cf)
                self.assertTrue(valido, f"CF {cf} non valido: {errori}")
                dati = decodifica_cf(cf_norm)
                self.assertEqual(dati["codice_catastale"], catastale)
                comune = COMUNI.get(catastale)
                self.assertEqual(comune, comune_atteso,
                                 f"Per {catastale}: atteso {comune_atteso}, trovato {comune}")


class TestEdgeCases(unittest.TestCase):
    """Casi limite e situazioni particolari."""

    def test_X_padding(self):
        """CF con X di padding (nome/cognome cortissimi)."""
        cf = build_cf("A", "BO", "80", "A", "01", "H501")
        valido, errori, _ = valida_cf(cf)
        self.assertTrue(valido, f"CF con X non valido: {errori}")

    def test_foreign_born(self):
        """Codice catastale Z404 (nato all'estero)."""
        cf = build_cf("ROSSI", "MARIO", "80", "A", "01", "Z404")
        valido, _, _ = valida_cf(cf)
        self.assertTrue(valido)
        # Z404 potrebbe non essere nel database — non è un errore

    def test_francesco_name_encoding(self):
        """Verifica che il nome FRANCESCO venga codificato correttamente."""
        cf = build_cf("ROSSI", "FRANCESCO", "80", "A", "01", "H501")
        valido, _, cf_norm = valida_cf(cf)
        self.assertTrue(valido)
        dati = decodifica_cf(cf_norm)
        # Il nome derivato dovrebbe essere FNC
        self.assertEqual(dati["nome_derivato"], "FNC")

    def test_double_consonant_surname(self):
        """Cognome con doppia consonante (es. RUSSO)."""
        # RUSSO → R,S,S → RSS
        self.assertEqual(cognome_a_codice("RUSSO"), "RSS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
