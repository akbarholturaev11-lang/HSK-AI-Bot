/** Execute the actual Mini App N1 retry selector under Node (no DOM needed).
 * The tested function is extracted verbatim from the shipping HTML: if a
 * frontend refactor changes its name or signature the test fails loudly.
 */
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync("app/static/course-v3.html", "utf8");
const start = html.indexOf("function skipN1PilotRechecks(index){");
const end = html.indexOf("\nfunction flowProg()", start);
assert.ok(start >= 0 && end > start, "N1 retry function missing in Mini App");
const source = html.slice(start, end);

function run(queue, failures, startIndex) {
  const sandbox = {Flow: {queue, pilotFailures: failures}};
  vm.runInNewContext(source, sandbox, {timeout: 1000});
  return sandbox.skipN1PilotRechecks(startIndex);
}
const lesson1 = [
  {type: "quick_quiz"},
  ...["polite", "listening", "farewell"].map(learning_objective => ({
    learning_objective, learning_retry: "n1_exit_check_v1",
  })),
];
assert.equal(run(lesson1, {polite:false,listening:false,farewell:false},1),4,
  "all correct: skip all three alternate checks");
assert.equal(run(lesson1, {polite:false,listening:true,farewell:false},1),2,
  "failed listening objective: show its alternate");
assert.equal(run(lesson1, {polite:false,listening:true,farewell:false},3),4,
  "passed farewell: skip its alternate");
assert.equal(run(lesson1, {},1),1, "unknown resume history must not drop an alternate");

const lesson2 = [
  {type: "quick_quiz"},
  {type: "listening_choice",learning_objective:"n1_source_02_listen",learning_retry:"n1_exit_check_v1"},
  {type: "meaning_guess",learning_objective:"n1_source_02_sentence",learning_retry:"n1_exit_check_v1"},
];
assert.equal(run(lesson2, {n1_source_02_listen:false,n1_source_02_sentence:false},1),3);
assert.equal(run(lesson2, {n1_source_02_listen:true,n1_source_02_sentence:false},1),1);
assert.equal(run(lesson2, {n1_source_02_listen:true,n1_source_02_sentence:false},2),3);
assert.equal(run(lesson2, {},1),1);
console.log("PASS: actual Mini App N1 alternate-example selector (8 cases)");
