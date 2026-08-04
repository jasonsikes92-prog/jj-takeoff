import { readFile } from "node:fs/promises";
import { SpreadsheetFile } from "@oai/artifact-tool";

const source = "C:/Users/jason/.claude/skills/jnj-estimate-takeoff/templates/estimate-template.xlsx";
const input = await readFile(source);
const workbook = await SpreadsheetFile.importXlsx(input.buffer.slice(input.byteOffset, input.byteOffset + input.byteLength));

const sheets = await workbook.inspect({ kind: "sheet", include: "id,name" });
const firstSheetName = sheets.items?.[0]?.name ?? "Estimate";
const table = await workbook.inspect({
  kind: "table",
  sheetId: firstSheetName,
  range: "A1:J80",
  include: "values,formulas",
  tableMaxRows: 80,
  tableMaxCols: 10,
  maxChars: 30000,
});
const formulas = await workbook.inspect({
  kind: "formula",
  sheetId: firstSheetName,
  range: "A1:J120",
  options: { maxResults: 100 },
  maxChars: 12000,
});

console.log(JSON.stringify({ sheets, firstSheetName, table, formulas }, null, 2));
