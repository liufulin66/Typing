import { readFileSync } from "node:fs";
import { runBufferChecks } from "../typing_app/static/checks.mjs";

const cases = JSON.parse(readFileSync(new URL("../typing_app/static/score-cases.json", import.meta.url), "utf8"));
const results = runBufferChecks(cases);
results.forEach((test) => console.log(`${test.passed ? "PASS" : "FAIL"} ${test.name} ${test.passed ? "" : test.detail}`));
if (results.some((test) => !test.passed)) process.exitCode = 1;
