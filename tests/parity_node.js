// Node side of the parity test: node tests/parity_node.js model/redd_lbal.json in.json out.json
const fs = require("fs");
const R = require("../webapp/engine.js");
const [bundlePath, inPath, outPath] = process.argv.slice(2);
const eng = new R.Engine(JSON.parse(fs.readFileSync(bundlePath, "utf8")));
const items = JSON.parse(fs.readFileSync(inPath, "utf8"));
const out = items.map(([text, sender]) => {
  const r = eng.analyze(text, sender || null);
  return {
    tokens: R.tokenize(text).map((t) => [t.raw, t.norm, t.kind, t.s, t.e]),
    logit: r._logit_raw, risk: r._risk_raw, verdict: r.verdict, type: r.type,
    signals: r.signals.map((s) => s.id), hl: r.highlights.filter((h) => h.kind !== "ml").map((h) => [h.s, h.e, h.rule]),
    explain_dar: eng.explain(r, "dar").reasons.map((x) => x.text),
  };
});
fs.writeFileSync(outPath, JSON.stringify(out));
