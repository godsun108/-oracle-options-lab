import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const html = fs.readFileSync("markets-now/index.html", "utf8");
assert.match(html, /Markets Now/);
assert.match(html, /markets-now\.json/);
assert.match(html, /orders_enabled/);
assert.match(html, /No trade is a valid result/);
assert.match(html, /localStorage/);
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
assert.equal(scripts.length, 1, "expected one inline application script");
for (const script of scripts) new vm.Script(script[1]);
console.log("Markets Now HTML and JavaScript syntax checks passed.");
