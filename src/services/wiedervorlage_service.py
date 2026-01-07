"""
Wiedervorlage Service - Intelligente Fristenerkennung und Follow-up-System

Erkennt automatisch:
- Zeitangaben in Texten (in 2 Wochen, bis zum 15.03., etc.)
- Zahlungsfristen
- Vergleichsfristen
- Wiedervorlagetermine

Funktionen:
- Automatische WV-Vorschläge nach Nachrichtenversand
- Bedingungsprüfung bei WV-Auslösung
- Vorformulierte Antworten/Briefe
"""

import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class WVGrund(str, Enum):
    """Grund für die Wiedervorlage"""
    ZAHLUNGSFRIST = "zahlungsfrist"
    VERGLEICHSFRIST = "vergleichsfrist"
    WIDERSPRUCHSFRIST = "widerspruchsfrist"
    STELLUNGNAHME = "stellungnahme"
    PRUEFUNG = "pruefung"  # Allgemeine Prüfung nach Zeitraum
    VERJAEHRUNG = "verjaehrung"
    RATENZAHLUNG = "ratenzahlung"
    SONSTIGES = "sonstiges"


class WVBedingung(str, Enum):
    """Bedingung, die bei WV geprüft wird"""
    ZAHLUNG_EINGEGANGEN = "zahlung_eingegangen"
    VERGLEICH_ANGENOMMEN = "vergleich_angenommen"
    WIDERSPRUCH_ERHOBEN = "widerspruch_erhoben"
    STELLUNGNAHME_EINGEGANGEN = "stellungnahme_eingegangen"
    KEINE_REAKTION = "keine_reaktion"
    TEILZAHLUNG = "teilzahlung"
    SONSTIGES = "sonstiges"


class WVErgebnis(str, Enum):
    """Ergebnis der Bedingungsprüfung"""
    BEDINGUNG_ERFUELLT = "erfuellt"
    BEDINGUNG_NICHT_ERFUELLT = "nicht_erfuellt"
    TEILWEISE_ERFUELLT = "teilweise"
    NICHT_PRUEFBAR = "nicht_pruefbar"


@dataclass
class ErkanntesFristdatum:
    """Ein im Text erkanntes Datum oder Zeitraum"""
    original_text: str  # Der erkannte Text
    datum: date  # Das berechnete Datum
    grund: WVGrund
    bedingung: Optional[WVBedingung] = None
    kontext: str = ""  # Umgebender Text
    konfidenz: float = 1.0  # Wie sicher ist die Erkennung


@dataclass
class WVVorschlag:
    """Vorschlag für eine Wiedervorlage"""
    titel: str
    beschreibung: str
    datum: date
    grund: WVGrund
    bedingung: WVBedingung
    prioritaet: str = "normal"  # low, normal, high, critical
    erinnerung_tage_vorher: int = 3
    original_text: str = ""


@dataclass
class WVAusloesung:
    """Daten bei Auslösung einer Wiedervorlage"""
    wv_id: str
    case_id: str
    titel: str
    grund: WVGrund
    bedingung: WVBedingung
    ergebnis: WVErgebnis
    ergebnis_details: Dict[str, Any] = field(default_factory=dict)
    vorgeschlagene_aktion: str = ""
    brief_entwurf: str = ""
    email_entwurf: str = ""


class WiedervorlageService:
    """
    Service für intelligente Wiedervorlagen
    """

    # Deutsche Zeitraum-Patterns
    ZEITRAUM_PATTERNS = [
        # "in X Tagen/Wochen/Monaten/Jahren"
        (r'in\s+(\d+)\s+(tag(?:en?)?|woche(?:n)?|monat(?:en?)?|jahr(?:en?)?)', 'relativ'),
        # "innerhalb von X Tagen"
        (r'innerhalb\s+(?:von\s+)?(\d+)\s+(tag(?:en?)?|woche(?:n)?|monat(?:en?)?)', 'relativ'),
        # "binnen X Tagen"
        (r'binnen\s+(\d+)\s+(tag(?:en?)?|woche(?:n)?|monat(?:en?)?)', 'relativ'),
        # "bis zum DD.MM.YYYY"
        (r'bis\s+(?:zum\s+)?(\d{1,2})\.(\d{1,2})\.(\d{2,4})', 'absolut'),
        # "spätestens am DD.MM.YYYY"
        (r'spätestens\s+(?:am\s+)?(\d{1,2})\.(\d{1,2})\.(\d{2,4})', 'absolut'),
        # "Frist bis DD.MM."
        (r'frist\s+bis\s+(?:zum\s+)?(\d{1,2})\.(\d{1,2})\.?(\d{2,4})?', 'absolut'),
        # "2 Wochen Frist"
        (r'(\d+)\s+(tag(?:en?)?|woche(?:n)?|monat(?:en?)?)\s+frist', 'relativ'),
    ]

    # Kontext-Keywords für Grund-Erkennung
    GRUND_KEYWORDS = {
        WVGrund.ZAHLUNGSFRIST: [
            'zahlung', 'bezahlung', 'überweisen', 'begleichen', 'ausgleichen',
            'zahlen sie', 'zu zahlen', 'zahlbar', 'fälligkeit'
        ],
        WVGrund.VERGLEICHSFRIST: [
            'vergleich', 'vergleichsangebot', 'einigung', 'vereinbarung',
            'angebot annehmen', 'vergleichsvorschlag'
        ],
        WVGrund.WIDERSPRUCHSFRIST: [
            'widerspruch', 'einspruch', 'widersprechen', 'anfechten'
        ],
        WVGrund.STELLUNGNAHME: [
            'stellungnahme', 'äußerung', 'rückmeldung', 'antwort',
            'position beziehen', 'erklären'
        ],
        WVGrund.RATENZAHLUNG: [
            'rate', 'raten', 'ratenzahlung', 'teilzahlung', 'monatlich'
        ],
        WVGrund.PRUEFUNG: [
            'prüfen', 'vorlegen', 'wiedervorlage', 'nochmal', 'erneut',
            'überprüfen', 'nachschauen'
        ],
        WVGrund.VERJAEHRUNG: [
            'verjährung', 'verjährt', 'verjährungsfrist'
        ],
    }

    # Vorlagen für Briefe/Emails bei verschiedenen Ergebnissen
    BRIEF_VORLAGEN = {
        (WVGrund.ZAHLUNGSFRIST, WVErgebnis.BEDINGUNG_NICHT_ERFUELLT): """
Sehr geehrte/r [ANREDE],

trotz unseres Schreibens vom [URSPRUNGSDATUM] und der darin gesetzten Frist bis zum [FRISTDATUM]
haben wir bislang keinen Zahlungseingang feststellen können.

Wir fordern Sie daher letztmalig auf, den offenen Betrag in Höhe von [BETRAG] EUR
unverzüglich, spätestens jedoch bis zum [NEUE_FRIST] auf unser Konto zu überweisen.

Sollte auch diese Frist fruchtlos verstreichen, werden wir ohne weitere Ankündigung
gerichtliche Maßnahmen einleiten.

[SIGNATUR]
""",
        (WVGrund.ZAHLUNGSFRIST, WVErgebnis.TEILWEISE_ERFUELLT): """
Sehr geehrte/r [ANREDE],

wir bestätigen den Eingang Ihrer Teilzahlung in Höhe von [TEILBETRAG] EUR am [ZAHLUNGSDATUM].

Gemäß unserer Vereinbarung verbleibt ein Restbetrag von [RESTBETRAG] EUR, der bis zum [FRISTDATUM]
fällig ist.

Wir bitten um fristgerechte Zahlung.

[SIGNATUR]
""",
        (WVGrund.ZAHLUNGSFRIST, WVErgebnis.BEDINGUNG_ERFUELLT): """
Sehr geehrte/r [ANREDE],

wir bestätigen den vollständigen Ausgleich der Forderung durch Ihre Zahlung
vom [ZAHLUNGSDATUM] in Höhe von [BETRAG] EUR.

Die Angelegenheit ist damit erledigt. Vielen Dank für die Zahlung.

[SIGNATUR]
""",
        (WVGrund.VERGLEICHSFRIST, WVErgebnis.BEDINGUNG_NICHT_ERFUELLT): """
Sehr geehrte/r [ANREDE],

unser Vergleichsangebot vom [URSPRUNGSDATUM] haben Sie nicht innerhalb der gesetzten
Frist bis zum [FRISTDATUM] angenommen.

Das Angebot ist damit hinfällig. Wir werden nunmehr die volle Forderung in Höhe von
[BETRAG] EUR nebst Zinsen und Kosten geltend machen.

[SIGNATUR]
""",
        (WVGrund.VERGLEICHSFRIST, WVErgebnis.BEDINGUNG_ERFUELLT): """
Sehr geehrte/r [ANREDE],

wir bestätigen die Annahme unseres Vergleichsangebots.

Gemäß der Vereinbarung bitten wir um Zahlung des Vergleichsbetrages in Höhe von
[VERGLEICHSBETRAG] EUR bis zum [ZAHLUNGSFRIST].

Nach Zahlungseingang werden wir die Angelegenheit als erledigt betrachten.

[SIGNATUR]
""",
        (WVGrund.PRUEFUNG, WVErgebnis.BEDINGUNG_NICHT_ERFUELLT): """
Aktennotiz zur Wiedervorlage:

Akte: [AKTENZEICHEN]
Schuldner: [SCHULDNER]
Prüfungsdatum: [HEUTE]

Ergebnis der Prüfung:
- Offener Betrag: [BETRAG] EUR
- Letzter Kontakt: [LETZTER_KONTAKT]
- Status: Keine Änderung

Empfohlenes Vorgehen:
[_] Erneute Mahnung versenden
[_] Gerichtliches Mahnverfahren einleiten
[_] Weitere Wiedervorlage in [ZEITRAUM]
[_] Akte schließen (uneinbringlich)

[SIGNATUR]
""",
    }

    def __init__(self):
        self.heute = date.today()

    def _berechne_datum_relativ(self, anzahl: int, einheit: str, basis: date = None) -> date:
        """Berechnet Datum aus relativer Angabe"""
        if basis is None:
            basis = self.heute

        einheit_lower = einheit.lower()

        if 'tag' in einheit_lower:
            return basis + timedelta(days=anzahl)
        elif 'woche' in einheit_lower:
            return basis + timedelta(weeks=anzahl)
        elif 'monat' in einheit_lower:
            # Approximation: 30 Tage pro Monat
            return basis + timedelta(days=anzahl * 30)
        elif 'jahr' in einheit_lower:
            return basis + timedelta(days=anzahl * 365)

        return basis + timedelta(days=anzahl)

    def _parse_absolutes_datum(self, tag: str, monat: str, jahr: str = None) -> Optional[date]:
        """Parst absolutes Datum aus Strings"""
        try:
            tag_int = int(tag)
            monat_int = int(monat)

            if jahr:
                jahr_int = int(jahr)
                if jahr_int < 100:
                    jahr_int += 2000
            else:
                # Aktuelles Jahr oder nächstes Jahr
                jahr_int = self.heute.year
                test_datum = date(jahr_int, monat_int, tag_int)
                if test_datum < self.heute:
                    jahr_int += 1

            return date(jahr_int, monat_int, tag_int)
        except (ValueError, TypeError):
            return None

    def _erkenne_grund(self, text: str, kontext: str = "") -> WVGrund:
        """Erkennt den Grund anhand von Keywords im Text"""
        combined_text = f"{text} {kontext}".lower()

        for grund, keywords in self.GRUND_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return grund

        return WVGrund.SONSTIGES

    def _grund_zu_bedingung(self, grund: WVGrund) -> WVBedingung:
        """Mappt Grund auf typische Bedingung"""
        mapping = {
            WVGrund.ZAHLUNGSFRIST: WVBedingung.ZAHLUNG_EINGEGANGEN,
            WVGrund.VERGLEICHSFRIST: WVBedingung.VERGLEICH_ANGENOMMEN,
            WVGrund.WIDERSPRUCHSFRIST: WVBedingung.WIDERSPRUCH_ERHOBEN,
            WVGrund.STELLUNGNAHME: WVBedingung.STELLUNGNAHME_EINGEGANGEN,
            WVGrund.RATENZAHLUNG: WVBedingung.TEILZAHLUNG,
            WVGrund.PRUEFUNG: WVBedingung.KEINE_REAKTION,
            WVGrund.VERJAEHRUNG: WVBedingung.SONSTIGES,
            WVGrund.SONSTIGES: WVBedingung.SONSTIGES,
        }
        return mapping.get(grund, WVBedingung.SONSTIGES)

    def erkenne_fristen(self, text: str) -> List[ErkanntesFristdatum]:
        """
        Erkennt Fristen und Daten im Text.

        Args:
            text: Der zu analysierende Text

        Returns:
            Liste von erkannten Fristdaten
        """
        erkannte = []
        text_lower = text.lower()

        for pattern, typ in self.ZEITRAUM_PATTERNS:
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                try:
                    if typ == 'relativ':
                        # Relative Zeitangabe (in X Tagen)
                        anzahl = int(match.group(1))
                        einheit = match.group(2)
                        datum = self._berechne_datum_relativ(anzahl, einheit)
                    else:
                        # Absolutes Datum
                        gruppen = match.groups()
                        if len(gruppen) >= 2:
                            tag = gruppen[0]
                            monat = gruppen[1]
                            jahr = gruppen[2] if len(gruppen) > 2 else None
                            datum = self._parse_absolutes_datum(tag, monat, jahr)
                            if datum is None:
                                continue
                        else:
                            continue

                    # Kontext extrahieren (50 Zeichen vor und nach)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    kontext = text[start:end]

                    # Grund erkennen
                    grund = self._erkenne_grund(match.group(0), kontext)
                    bedingung = self._grund_zu_bedingung(grund)

                    erkannte.append(ErkanntesFristdatum(
                        original_text=match.group(0),
                        datum=datum,
                        grund=grund,
                        bedingung=bedingung,
                        kontext=kontext,
                        konfidenz=0.8 if grund != WVGrund.SONSTIGES else 0.5
                    ))

                except (ValueError, IndexError):
                    continue

        # Deduplizieren nach Datum
        seen_dates = set()
        unique = []
        for e in erkannte:
            if e.datum not in seen_dates:
                seen_dates.add(e.datum)
                unique.append(e)

        return sorted(unique, key=lambda x: x.datum)

    def erstelle_wv_vorschlaege(self, text: str, case_info: Dict[str, Any] = None) -> List[WVVorschlag]:
        """
        Erstellt Wiedervorlage-Vorschläge basierend auf erkannten Fristen.

        Args:
            text: Der analysierte Text (Brief, Email, etc.)
            case_info: Informationen zur Akte

        Returns:
            Liste von WV-Vorschlägen
        """
        erkannte = self.erkenne_fristen(text)
        vorschlaege = []

        for frist in erkannte:
            # Titel basierend auf Grund
            titel_map = {
                WVGrund.ZAHLUNGSFRIST: "Zahlungsfrist prüfen",
                WVGrund.VERGLEICHSFRIST: "Vergleichsannahme prüfen",
                WVGrund.WIDERSPRUCHSFRIST: "Widerspruchsfrist",
                WVGrund.STELLUNGNAHME: "Stellungnahme prüfen",
                WVGrund.RATENZAHLUNG: "Ratenzahlung prüfen",
                WVGrund.PRUEFUNG: "Akte zur Prüfung",
                WVGrund.VERJAEHRUNG: "Verjährung prüfen",
                WVGrund.SONSTIGES: "Wiedervorlage",
            }

            titel = titel_map.get(frist.grund, "Wiedervorlage")

            # Beschreibung
            beschreibung = f"Frist erkannt: '{frist.original_text}'\n"
            beschreibung += f"Kontext: ...{frist.kontext}...\n"
            beschreibung += f"Zu prüfen: {frist.bedingung.value}"

            # Priorität basierend auf Zeitraum
            tage_bis = (frist.datum - self.heute).days
            if tage_bis <= 7:
                prioritaet = "high"
            elif tage_bis <= 14:
                prioritaet = "normal"
            else:
                prioritaet = "low"

            vorschlaege.append(WVVorschlag(
                titel=titel,
                beschreibung=beschreibung,
                datum=frist.datum,
                grund=frist.grund,
                bedingung=frist.bedingung,
                prioritaet=prioritaet,
                erinnerung_tage_vorher=min(3, tage_bis) if tage_bis > 0 else 0,
                original_text=frist.original_text
            ))

        return vorschlaege

    def pruefe_bedingung(
        self,
        wv_grund: WVGrund,
        wv_bedingung: WVBedingung,
        case_data: Dict[str, Any]
    ) -> Tuple[WVErgebnis, Dict[str, Any]]:
        """
        Prüft, ob die Bedingung einer WV erfüllt wurde.

        Args:
            wv_grund: Der Grund der WV
            wv_bedingung: Die zu prüfende Bedingung
            case_data: Aktuelle Daten der Akte (Zahlungen, Status, etc.)

        Returns:
            Tuple aus Ergebnis und Details
        """
        details = {}

        if wv_bedingung == WVBedingung.ZAHLUNG_EINGEGANGEN:
            # Prüfe Zahlungseingänge
            offener_betrag = case_data.get('offener_betrag', 0)
            ursprungs_betrag = case_data.get('ursprungs_betrag', offener_betrag)
            letzte_zahlung = case_data.get('letzte_zahlung')

            details['offener_betrag'] = offener_betrag
            details['ursprungs_betrag'] = ursprungs_betrag
            details['letzte_zahlung'] = letzte_zahlung

            if offener_betrag <= 0:
                return WVErgebnis.BEDINGUNG_ERFUELLT, details
            elif letzte_zahlung and offener_betrag < ursprungs_betrag:
                return WVErgebnis.TEILWEISE_ERFUELLT, details
            else:
                return WVErgebnis.BEDINGUNG_NICHT_ERFUELLT, details

        elif wv_bedingung == WVBedingung.VERGLEICH_ANGENOMMEN:
            vergleich_status = case_data.get('vergleich_status')
            if vergleich_status == 'angenommen':
                return WVErgebnis.BEDINGUNG_ERFUELLT, details
            elif vergleich_status == 'verhandlung':
                return WVErgebnis.TEILWEISE_ERFUELLT, details
            else:
                return WVErgebnis.BEDINGUNG_NICHT_ERFUELLT, details

        elif wv_bedingung == WVBedingung.STELLUNGNAHME_EINGEGANGEN:
            letzte_nachricht = case_data.get('letzte_schuldner_nachricht')
            if letzte_nachricht:
                details['letzte_nachricht'] = letzte_nachricht
                return WVErgebnis.BEDINGUNG_ERFUELLT, details
            return WVErgebnis.BEDINGUNG_NICHT_ERFUELLT, details

        elif wv_bedingung == WVBedingung.TEILZAHLUNG:
            zahlungen = case_data.get('zahlungen', [])
            if zahlungen:
                details['zahlungen'] = zahlungen
                return WVErgebnis.BEDINGUNG_ERFUELLT, details
            return WVErgebnis.BEDINGUNG_NICHT_ERFUELLT, details

        # Default
        return WVErgebnis.NICHT_PRUEFBAR, details

    def generiere_brief(
        self,
        grund: WVGrund,
        ergebnis: WVErgebnis,
        case_data: Dict[str, Any],
        platzhalter: Dict[str, str] = None
    ) -> str:
        """
        Generiert einen Briefentwurf basierend auf WV-Ergebnis.

        Args:
            grund: Der WV-Grund
            ergebnis: Das Prüfungsergebnis
            case_data: Daten der Akte
            platzhalter: Zusätzliche Platzhalter für den Brief

        Returns:
            Briefentwurf als String
        """
        key = (grund, ergebnis)
        vorlage = self.BRIEF_VORLAGEN.get(key)

        if not vorlage:
            # Fallback auf allgemeine Prüfungsvorlage
            vorlage = self.BRIEF_VORLAGEN.get((WVGrund.PRUEFUNG, WVErgebnis.BEDINGUNG_NICHT_ERFUELLT), "")

        # Standard-Platzhalter aus case_data
        ersetzungen = {
            '[ANREDE]': case_data.get('schuldner_anrede', 'Frau/Herr'),
            '[SCHULDNER]': case_data.get('schuldner_name', '[Name]'),
            '[AKTENZEICHEN]': case_data.get('aktenzeichen', '[Az.]'),
            '[BETRAG]': f"{case_data.get('offener_betrag', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            '[HEUTE]': self.heute.strftime('%d.%m.%Y'),
            '[SIGNATUR]': case_data.get('signatur', 'Mit freundlichen Grüßen'),
        }

        # Zusätzliche Platzhalter
        if platzhalter:
            ersetzungen.update(platzhalter)

        # Ersetzen
        brief = vorlage
        for key, value in ersetzungen.items():
            brief = brief.replace(key, str(value))

        return brief.strip()

    def erstelle_wv_ausloesung(
        self,
        wv_id: str,
        case_id: str,
        titel: str,
        grund: WVGrund,
        bedingung: WVBedingung,
        case_data: Dict[str, Any]
    ) -> WVAusloesung:
        """
        Erstellt die komplette WV-Auslösung mit Prüfung und Vorschlägen.
        """
        # Bedingung prüfen
        ergebnis, details = self.pruefe_bedingung(grund, bedingung, case_data)

        # Vorgeschlagene Aktion
        aktionen = {
            (WVGrund.ZAHLUNGSFRIST, WVErgebnis.BEDINGUNG_NICHT_ERFUELLT): "Letzte Mahnung versenden oder gerichtliches Mahnverfahren einleiten",
            (WVGrund.ZAHLUNGSFRIST, WVErgebnis.TEILWEISE_ERFUELLT): "Restzahlung anmahnen oder Ratenzahlung vereinbaren",
            (WVGrund.ZAHLUNGSFRIST, WVErgebnis.BEDINGUNG_ERFUELLT): "Akte als erledigt markieren",
            (WVGrund.VERGLEICHSFRIST, WVErgebnis.BEDINGUNG_NICHT_ERFUELLT): "Volle Forderung geltend machen",
            (WVGrund.VERGLEICHSFRIST, WVErgebnis.BEDINGUNG_ERFUELLT): "Vergleichszahlung überwachen",
            (WVGrund.PRUEFUNG, WVErgebnis.BEDINGUNG_NICHT_ERFUELLT): "Weitere Maßnahmen prüfen oder Akte schließen",
        }

        aktion = aktionen.get((grund, ergebnis), "Manuelle Prüfung erforderlich")

        # Brief generieren
        brief = self.generiere_brief(grund, ergebnis, case_data)

        # Email-Version (kürzer)
        email = brief.replace('\n\n', '\n').strip()

        return WVAusloesung(
            wv_id=wv_id,
            case_id=case_id,
            titel=titel,
            grund=grund,
            bedingung=bedingung,
            ergebnis=ergebnis,
            ergebnis_details=details,
            vorgeschlagene_aktion=aktion,
            brief_entwurf=brief,
            email_entwurf=email
        )


# Singleton-Instanz
_wv_service: Optional[WiedervorlageService] = None


def get_wv_service() -> WiedervorlageService:
    """Gibt die WV-Service-Instanz zurück"""
    global _wv_service
    if _wv_service is None:
        _wv_service = WiedervorlageService()
    return _wv_service


def erkenne_fristen_im_text(text: str) -> List[ErkanntesFristdatum]:
    """Convenience-Funktion zum Erkennen von Fristen"""
    return get_wv_service().erkenne_fristen(text)


def erstelle_wv_vorschlaege(text: str, case_info: Dict = None) -> List[WVVorschlag]:
    """Convenience-Funktion für WV-Vorschläge"""
    return get_wv_service().erstelle_wv_vorschlaege(text, case_info)
