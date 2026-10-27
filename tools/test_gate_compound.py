"""Control for qa_gate.append_tail's compound rule (2026-10-06).

rc 0 = the split compound passes AND every known append still fires.
With HEXAPLA_NO_COMPOUND=1 the armourbearer cases must fire again (rc 1),
which proves this test can see the rule.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_gate import append_tail, norm_ref  # noqa: E402

want = ("And when he saw that mighty army, he prayed and said, Blessed art thou, "
        "O Saviour of Israel, who didst quell the violence of the mighty man by the "
        "hand of thy servant David, and gavest the host of strangers into the hands "
        "of Jonathan the son of Saul, and his armourbearer;")
base = want.replace("armourbearer;", "")
CLEAN = [base + "armour bearer.", base + "armor bearer."]          # 1 Macc 4:30 draws
DIRTY = [("... zerah shaul", "... zera shawl shri"),                # ylt 12/3 v24
         ("... zerah shaul", "... zerah shaul shop"),
         (want, base + "armour bearer so try"),
         (want, base + "armourbearer bearer")]

bad = 0
for h in CLEAN:
    x = append_tail(norm_ref(want), norm_ref(h))
    print("CLEAN", "FIRED " + str(x) if x else "pass", h[-30:])
    bad += bool(x)
for w, h in DIRTY:
    x = append_tail(norm_ref(w), norm_ref(h))
    print("DIRTY", "fired " + str(x) if x else "MISSED", h[-30:])
    bad += not x
print("rc", 1 if bad else 0, "(HEXAPLA_NO_COMPOUND set)" if os.environ.get("HEXAPLA_NO_COMPOUND") else "")
sys.exit(1 if bad else 0)
