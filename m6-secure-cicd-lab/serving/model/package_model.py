"""Train the balanced classifier and write a VERIFIED package: model + card + lock + SHA-256 manifest.

    python -m model.package_model            # build the package
    python -m model.package_model --verify   # check hashes and file set
    python -m model.package_model --tamper   # append bytes to the model (for the supply-chain demo)
"""
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(__file__)
PKG = os.path.join(HERE, "package")
PAYLOAD = ["model.joblib", "model_card.json", "requirements.lock"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8192), b""):
            h.update(b)
    return h.hexdigest()


def _train():
    import sklearn
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (confusion_matrix, precision_score, recall_score,
                                 f1_score, roc_auc_score)
    from model.dataset import generate, DEPTS

    df = generate()
    data_sha = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
    NUM = ['hour_of_day', 'failed_attempts_24h', 'distinct_ips_24h', 'session_minutes', 'bytes_downloaded_mb']
    BIN = ['country_changed', 'is_vpn_exit', 'device_is_new', 'mfa_used', 'privileged_action']
    CAT = ['department']
    feats = NUM + BIN + CAT
    pre = ColumnTransformer([('num', StandardScaler(), NUM), ('bin', 'passthrough', BIN),
                             ('cat', OneHotEncoder(handle_unknown='ignore'), CAT)])
    pipe = Pipeline([('pre', pre), ('clf', LogisticRegression(max_iter=2000, class_weight='balanced'))])
    tr, te = train_test_split(df, test_size=0.25, random_state=42, stratify=df.label)
    pipe.fit(tr[feats], tr.label)
    s = pipe.predict_proba(te[feats])[:, 1]
    p = (s >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(te.label, p, labels=[0, 1]).ravel()
    ev = dict(precision=round(precision_score(te.label, p), 4), recall=round(recall_score(te.label, p), 4),
              f1=round(f1_score(te.label, p), 4), roc_auc=round(roc_auc_score(te.label, s), 4),
              caught=int(tp), positives=int(tp + fn), false_alarms=int(fp), normal=int(tn + fp))
    return pipe, ev, data_sha, DEPTS, sklearn.__version__


def build_card(ev, data_sha, depts, skver):
    return {
        "name": "auth-anomaly-classifier", "version": "1.0.0",
        "contract": {
            "features": {
                "hour_of_day": {"type": "int", "min": 0, "max": 23},
                "failed_attempts_24h": {"type": "int", "min": 0},
                "distinct_ips_24h": {"type": "int", "min": 1},
                "country_changed": {"type": "int", "min": 0, "max": 1},
                "is_vpn_exit": {"type": "int", "min": 0, "max": 1},
                "device_is_new": {"type": "int", "min": 0, "max": 1},
                "mfa_used": {"type": "int", "min": 0, "max": 1},
                "session_minutes": {"type": "int", "min": 1},
                "privileged_action": {"type": "int", "min": 0, "max": 1},
                "bytes_downloaded_mb": {"type": "float", "min": 0},
                "department": {"type": "enum", "values": depts}},
            "output": {"risk_score": "float in [0,1]", "flagged": "risk_score >= threshold"},
            "threshold": 0.5},
        "evaluation": {**ev, "split": "stratified 25% holdout (n=1500, 88 positive)", "threshold": 0.5},
        "provenance": {"training_data_sha256": data_sha, "git_commit": os.environ.get("GITHUB_SHA", "(local)"),
                       "python": ".".join(map(str, sys.version_info[:3])), "sklearn": skver},
        "limitations": [
            "Precision 0.61 at the shipped threshold: ~53 false alarms per 1,412 normal logins.",
            "Evasion rate ~26% against cheap bounded evasion (Module 5), before adversarial hardening.",
            "Trained on synthetic data from one org shape; not validated on real traffic.",
            "Department is a closed set of six; an unseen department is rejected, not scored."],
        "approval": {"approved_by": None, "approved_at": None}}


def package():
    import joblib
    if os.path.isdir(PKG):
        shutil.rmtree(PKG)
    os.makedirs(PKG)
    pipe, ev, data_sha, depts, skver = _train()
    joblib.dump(pipe, os.path.join(PKG, "model.joblib"))
    json.dump(build_card(ev, data_sha, depts, skver), open(os.path.join(PKG, "model_card.json"), "w"), indent=2)
    open(os.path.join(PKG, "requirements.lock"), "w").write(f"scikit-learn=={skver}\njoblib\nnumpy\npandas\n")
    manifest = {"algo": "sha256", "files": {fn: sha256(os.path.join(PKG, fn)) for fn in PAYLOAD}}
    json.dump(manifest, open(os.path.join(PKG, "manifest.json"), "w"), indent=2)
    print(f"Packaged to {PKG} — precision {ev['precision']} recall {ev['recall']} "
          f"roc-auc {ev['roc_auc']} | caught {ev['caught']}/{ev['positives']}, {ev['false_alarms']} false alarms")
    return manifest


def verify():
    manifest = json.load(open(os.path.join(PKG, "manifest.json")))
    listed = manifest["files"]
    present = set(os.listdir(PKG)) - {"manifest.json"}
    problems = []
    for fn, expected in listed.items():
        if fn not in present:
            problems.append(("MISSING", fn))
        elif sha256(os.path.join(PKG, fn)) != expected:
            problems.append(("MODIFIED", fn))
    for fn in present - set(listed):
        problems.append(("UNLISTED", fn))
    if not problems:
        print(f"PACKAGE VERIFIED — {len(listed)} files, all hashes match")
        return True
    print("PACKAGE VERIFICATION FAILED")
    for kind, fn in problems:
        print(f"  {kind:9} {fn}")
    return False


def tamper():
    with open(os.path.join(PKG, "model.joblib"), "ab") as f:
        f.write(b"\n# tampered\n")
    print("Appended 2 lines to model.joblib. The file still loads. Nothing about it looks wrong.")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--verify":
        sys.exit(0 if verify() else 1)
    elif arg == "--tamper":
        tamper()
    else:
        package()
