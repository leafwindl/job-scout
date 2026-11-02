import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../data/dashboard.html");
const destDir = resolve(here, "../public");
const dest = resolve(destDir, "dashboard.html");

if (!existsSync(src)) {
  console.warn("[sync] data/dashboard.html 不存在，跳过（先运行 job-scout dashboard）");
  process.exit(0);
}

mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log("[sync] dashboard.html -> public/dashboard.html");
