import os, sys, json, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))
from test_conformidade import WEIGHTS

def run_arm(module):
    env = dict(os.environ, APP_MODULE=module, PYTHONPATH=os.path.dirname(__file__))
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_conformidade.py", "-q",
         "--tb=no", "-p", "no:cacheprovider", "--no-header",
         "--json-report", "--json-report-file=none"],
        cwd=os.path.dirname(__file__), env=env, capture_output=True, text=True)
    # parse simples pelo report textual: usamos -rA para status por teste
    p2 = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_conformidade.py",
         "-rA", "--tb=no", "-q", "-p", "no:cacheprovider"],
        cwd=os.path.dirname(__file__), env=env, capture_output=True, text=True)
    results = {}
    for line in p2.stdout.splitlines():
        line = line.strip()
        for status in ("PASSED", "FAILED", "ERROR"):
            if line.startswith(status + " ") and "::" in line:
                name = line.split("::")[-1].split()[0]
                results[name] = (status == "PASSED")
    return results

def score(results):
    tot = passed = 0
    veto_fail = []
    detail = []
    for name, (w, veto) in WEIGHTS.items():
        ok = results.get(name, False)
        tot += w
        if ok:
            passed += w
        elif veto:
            veto_fail.append(name)
        detail.append((name, w, veto, ok))
    conf = passed / tot * 100
    return conf, veto_fail, detail

if __name__ == "__main__":
    out = {}
    arms = (("control", "control.app"), ("treatment_claude", "treatment.app"),
            ("perplexity", "perplexity.app"), ("gemini", "gemini.app"))
    for arm, module in arms:
        res = run_arm(module)
        conf, veto, detail = score(res)
        out[arm] = {"conformidade": round(conf, 1), "veto_fail": veto, "detail": detail}
    print(json.dumps(out, indent=2, ensure_ascii=False))
