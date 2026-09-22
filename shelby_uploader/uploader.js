import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const distFile = path.join(__dirname, "dist", "uploader.js");

if (fs.existsSync(distFile)) {
  await import("./dist/uploader.js");
} else {
  console.log("==================================================================");
  console.log("  Hansen AI Research Engine - Shelby Uploader Service v3.1");
  console.log("==================================================================");
  console.log("Production build not found in ./dist/uploader.js.");
  console.log("Please build TypeScript sources before running:\n");
  console.log("  npm install");
  console.log("  npm run build");
  console.log("  npm start\n");
  console.log("Or launch development runner directly:");
  console.log("  npm run dev (via tsx)\n");
  process.exit(1);
}
