#!/usr/bin/env python3
"""Dictionary-anchored scan for residual Burmese orthographic damage.

Read-only.  Token = maximal Myanmar-script run.  A token is accepted when it, or
its stem after stripping a case marker, is in the repository grammatical
dictionary or fully coverable by dictionary words.  Otherwise a single
orthographic repair rule is applied and the token is counted as *damaged* only
when the repaired token becomes a dictionary word / coverable compound.

This yields a lower bound on residual damage: every counted item has a
dictionary anchor, and nothing is rewritten on disk.

Output: analysis/damage-scan.json
"""
import json, re, collections, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = json.load(open(os.path.join(ROOT, "Engine/knowledge/isTreasure/master.json"), encoding="utf-8"))
TEXT = os.path.join(ROOT, "input/ယဲ့နင်1-200.txt")

norm = lambda s: re.sub(r"\s+", "", s)
words = set()
for lst in M["dictionary"].values():
    for w in lst:
        n = norm(w)
        if n:
            words.add(n)
MAXW = max(map(len, words))
CONS = "\u1000-\u1021"
CONS_MED = "[\u1000-\u1021][\u103b\u103c\u103d\u103e]?"

# ---------------------------------------------------------------- coverability
def coverable(t):
    n = len(t); ok = [False] * (n + 1); ok[0] = True
    for i in range(n):
        if not ok[i]:
            continue
        for L in range(min(MAXW, n - i), 0, -1):
            if t[i:i + L] in words:
                ok[i + L] = True
    return ok[n]

# stem stripping: case markers, possessive ့, plural, topic က
SUF = ["\u1019\u103a\u102c\u1038", "\u1010\u103d\u1031\u1037", "\u1019\u103b\u102c\u1038", "\u1010\u102d\u102f\u1037",
       "\u101e\u100a\u103a\u1037", "\u1000\u103c\u1031", "\u1015\u102c", "\u101c\u1032\u1038", "\u101e\u1031\u102c",
       "\u101e\u100a\u103a", "\u1000\u102d\u102f", "\u1019\u103e\u102c", "\u1010\u103d\u1004\u103a",
       "\u1016\u103c\u1004\u1037\u103a", "\u1019\u103e", "\u101e\u102d\u102f\u1037", "\u1021\u102c\u1038",
       "\u1000", "\u1019\u103a", "\u1010\u102c\u1037", "\u1019\u1031\u102c\u103a", "\u104f", "\u1037", "\u1010\u103d\u1031",
       "\u1015\u103c\u102e\u1038", "\u1019\u103b\u102c\u1038", "\u1010\u102d\u102f\u1037", "\u101c\u103b\u103a"]

def stems(tok):
    out = {tok}
    cur = tok
    for _ in range(3):
        for s in SUF:
            if cur.endswith(s) and len(cur) - len(s) >= 2:
                cur = cur[:-len(s)]
                out.add(cur)
                break
        else:
            break
    return out

def known(tok):
    return any(s in words or coverable(s) for s in stems(tok))

# ------------------------------------------------------------------- rules
# Candidate generators: every rule yields all one-edit variants it can see.
C_RANGE = range(0x1000, 0x1022)

def is_cons(c):
    return 0x1000 <= ord(c) <= 0x1021

def del_all(x, ch):
    return [x[:i] + x[i + len(ch):] for i in range(len(x)) if x.startswith(ch, i)]

def repl_all(x, a, b):
    return [x[:i] + b + x[i + len(a):] for i in range(len(x)) if x.startswith(a, i)]

def ins_before(x, ch):
    return [x[:i] + ch + x[i:] for i in range(1, len(x)) if is_cons(x[i])]

def move_e_right(x):
    out = []
    for i, c in enumerate(x):
        if c != "\u1031" or i + 2 >= len(x) or not is_cons(x[i + 1]):
            continue
        j = i + 2
        if j < len(x) and x[j] in "\u103b\u103c\u103d\u103e":
            j += 1
        out.append(x[:i] + x[i + 1:j] + "\u1031" + x[j:])
    return out

def move_ra_right(x):
    out = []
    for i, c in enumerate(x):
        if c == "\u103c" and i > 0 and i + 1 < len(x) and is_cons(x[i + 1]):
            out.append(x[:i] + x[i + 1] + "\u103c" + x[i + 2:])
    return out

def stack_pairs(x):
    out = []
    for i in range(len(x) - 1):
        if is_cons(x[i]) and is_cons(x[i + 1]):
            out.append(x[:i + 1] + "\u1039" + x[i + 1:])
    return out

RULES = [
    ("i_inserted_before_u", [lambda x: del_all(x, "\u102d") if "\u102d\u102f" in x else []]),
    ("e_sign_migrated_left", [move_e_right]),
    ("ra_hswe_migrated_left", [move_ra_right]),
    ("ra_hswe_lost", [lambda x: ins_before(x, "\u103c")]),
    ("ra_hswe_to_ka", [lambda x: repl_all(x, "\u103c", "\u1000")]),
    ("stray_ra_hswe", [lambda x: del_all(x, "\u103c")]),
    ("ha_hto_lost", [lambda x: del_all(x, "\u103e")]),
    ("ha_hto_inserted", [lambda x: ins_before(x, "\u103e")]),
    ("ha_hto_to_ra_hswe", [lambda x: repl_all(x, "\u103e", "\u103c")]),
    ("ya_yit_lost", [lambda x: del_all(x, "\u103b")]),
    ("virama_lost", [lambda x: del_all(x, "\u1039")]),
    ("pali_cluster_linearised", [stack_pairs]),
    ("vowel_order_swapped", [lambda x: repl_all(x, "\u102f\u102d", "\u102d\u102f")]),
    ("asat_ka_to_nga", [lambda x: repl_all(x, "\u102d\u1000\u103a", "\u102d\u102f\u1004\u103a")]),
    ("u_lost_before_i", [lambda x: repl_all(x, "\u102d", "\u102d\u102f")]),
]

SYMPTOMS = [
    ("\u1012\u102f\u1000\u1039\u1001\u101e\u100a\u103a", "\u1012\u102d\u102f\u1000\u1001\u101e\u100a\u103a"),   # ဒုက္ခသည် / ဒိုကခသည်
    ("\u1015\u103c\u102e\u1038", "\u1015\u102e\u1038"),                                                        # ပြီး / ပီး
    ("\u101b\u103e\u102d", "\u101b\u102d"),                                                                    # ရှိ / ရိ
    ("\u1000\u103c\u102c\u1038", "\u1000\u102c\u1038"),                                                        # ကြား / ကား
    ("\u101c\u102f\u1036\u1038", "\u101c\u102d\u102f\u1036\u1038"),                                            # လုံး / လိုံး
    ("\u1019\u101f\u102f\u1010\u103a", "\u1019\u101f\u102d\u102f\u1010\u103a"),                                # မဟုတ် / မဟိုတ်
    ("ရွှံ့", "ရြွိုံ့"),                          # ရွှံ့ / ရြွှိုံ့
    ("\u1010\u103d\u1031\u1037", "\u1010\u103c\u103d\u1031\u1037"),                                            # တွေ့ / တြွေ့
    ("\u101b\u103e\u1031\u1037", "\u101b\u103c\u1031\u1037"),                                                  # ရှေ့ / ရြေ့
    ("\u1019\u103e\u1014\u103a\u1038", "\u1019\u1014\u103a\u1038"),                                            # မှန်း / မန်း
    ("\u1001\u103c\u1031", "\u1031\u1001\u103c"),                                                              # ခြေ / ေခြ
    ("\u1000\u103c\u102d\u1019\u103a\u1038", "\u1000\u1000\u102d\u1019\u103a\u1038"),                          # ကြိမ်း / ကကိမ်း
    ("\u1000\u103c\u102e\u1038", "\u1000\u1000\u102e\u1038"),                                                  # ကြီး / ကကီး
    ("ခန္ဓာ", "ခနဓာ"),                                            # ခန္ဓာ / ခနဓာ
    ("\u1006\u102f\u1036\u1038", "\u1006\u102d\u102f\u1036\u1038"),                                            # ဆုံး / ဆိုံး
    ("\u1005\u102f", "\u1005\u102d\u102f"),                                                                    # စု / စို
    ("\u101f\u102f", "\u101f\u102d\u102f"),                                                                    # ဟု / ဟို
]

TOKEN_RE = re.compile(r"[\u1000-\u109F\uAA60-\uAA7F]+")

def main():
    t = open(TEXT, encoding="utf-8").read()
    toks = [x.strip("\u104a\u104b") for x in TOKEN_RE.findall(t)]
    toks = [x for x in toks if x]
    matched = damaged = unrepaired_n = 0
    repairs = collections.Counter()
    ex = collections.defaultdict(collections.Counter)
    unrepaired = collections.Counter()
    cache = {}

    def is_known(tok):
        r = cache.get(tok)
        if r is None:
            r = known(tok)
            cache[tok] = r
        return r

    for tok in toks:
        if is_known(tok):
            matched += 1
            continue
        hit = False
        tried = 0
        for name, gens in RULES:
            for g in gens:
                for c in g(tok):
                    tried += 1
                    if tried > 400:
                        break
                    if c and c != tok and is_known(c):
                        repairs[name] += 1
                        ex[name][tok + " -> " + c] += 1
                        damaged += 1
                        hit = True
                        break
                if hit or tried > 400:
                    break
            if hit:
                break
        if not hit:
            unrepaired[tok] += 1
            unrepaired_n += 1

    sym = []
    for good, bad in SYMPTOMS:
        sym.append({"correct": good, "damaged": bad, "correct_n": t.count(good),
                    "damaged_n": t.count(bad), "damaged_is_also_a_word": bad in words})

    out = {
        "lexicon": {"dictionary_words": len(words)},
        "tokens": {"total": len(toks), "dictionary_or_compound": matched,
                   "repaired_candidate": damaged, "unrepaired": unrepaired_n},
        "repairs_by_class": dict(repairs),
        "examples": {k: v.most_common(10) for k, v in ex.items()},
        "top_unrepaired_tokens": unrepaired.most_common(40),
        "symptom_table": sym,
    }
    json.dump(out, open(os.path.join(ROOT, "analysis/damage-scan.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("tokens", "repairs_by_class")}, ensure_ascii=False, indent=2))
    print("\nEXAMPLES")
    for k, v in out["examples"].items():
        print(" ", k, v[:4])
    print("\nTOP UNREPAIRED", out["top_unrepaired_tokens"][:12])

if __name__ == "__main__":
    main()
