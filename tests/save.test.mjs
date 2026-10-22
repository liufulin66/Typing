import { runSaveChecks } from "../typing_app/static/checks.mjs";
const results = await runSaveChecks();
results.forEach((test) => console.log(`${test.passed ? "PASS" : "FAIL"} ${test.name} ${test.detail || ""}`));
if (results.some((test) => !test.passed)) process.exitCode = 1;
