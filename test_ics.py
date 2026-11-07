"""python3 test_ics.py — no network"""
import re
import sys
from datetime import datetime

sys.path.insert(0, "api")
import ics  # noqa: E402

t = datetime(2026, 11, 7, 19, tzinfo=ics.TR)
m = lambda home, away, ch: {"gevsahibi": home, "gmisafir": away, "gtvkanali": ch, "start": t, "allday": False}
MATCHES = [("Sultanlar Ligi", m("A", "B", "TRT Spor")),
           ("Sultanlar Ligi", m("C", "D", "TVF Voleybol TV-Tabii Spor")),
           ("Kupa Voley", m("A", "C", "TRT Spor Yıldız"))]


def uids(query):
    out = ics.ics(MATCHES, ics.keeper(query))
    return dict(zip(re.findall(r"SUMMARY:(.*)\r", out), re.findall(r"UID:(.*)\r", out)))


all_ = uids("lig=")
assert list(all_) == ["A - B", "C - D", "A - C"]
assert list(uids("")) == list(uids("v=2")) == ["A - B", "A - C"]  # bare link stays trt-only for old subscribers
assert list(uids("kanal=TVF+Voleybol+TV")) == ["C - D"]  # simulcast text is split into channels
assert list(uids("takim=A&lig=Kupa+Voley")) == ["A - C"]  # groups combine with and
assert all(all_[k] == v for k, v in uids("takim=C").items())  # filtering never changes uids
assert ics.team("GALATASARAY DAIKIN") == "Galatasaray Daikin"
assert ics.team("VAKIFBANK") == "Vakıfbank" and ics.team("İLBANK") == "İlbank"  # turkish dotless/dotted i
assert ics.team("AL-KA ALTIN KANATLAR") == "Al-Ka Altın Kanatlar"
print("ok")
