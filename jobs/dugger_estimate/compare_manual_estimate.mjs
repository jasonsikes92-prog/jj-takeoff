import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const files = {
  manual: "C:/Users/jason/Downloads/Dugger Residence - Estimate Items.xlsx",
  estimate: "C:/Users/jason/OneDrive/Desktop/Claude/Dugger Residence - Estimate.xlsx",
  buildern: "C:/Users/jason/OneDrive/Desktop/Claude/Dugger Residence - Buildern Import.xlsx",
};

const outputDir = "C:/Users/jason/OneDrive/Desktop/Claude/dugger_estimate/comparison";
await fs.mkdir(outputDir, { recursive: true });

async function loadWorkbook(path) {
  return SpreadsheetFile.importXlsx(await FileBlob.load(path));
}

function columnName(number) {
  let value = number;
  let name = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}

async function dumpWorkbook(label, path, render = false) {
  const workbook = await loadWorkbook(path);
  const sheetInspect = await workbook.inspect({
    kind: "sheet",
    include: "id,name",
    maxChars: 10000,
  });
  const sheetRecords = String(sheetInspect.ndjson ?? "")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
  const sheetNames = sheetRecords
    .filter((item) => item.kind === "sheet")
    .map((item) => item.name);
  const sheets = [];

  for (let index = 0; index < sheetNames.length; index += 1) {
    const sheet = workbook.worksheets.getItemAt(index);
    const used = sheet.getUsedRange();
    sheets.push({
      name: sheetNames[index],
      address: used?.address ?? null,
      values: used?.values ?? [],
      formulas: used?.formulas ?? [],
    });

    if (render) {
      const rowCount = used?.values?.length ?? 0;
      const columnCount = used?.values?.[0]?.length ?? 0;
      const lastColumn = columnName(columnCount);
      for (let startRow = 1, chunk = 1; startRow <= rowCount; startRow += 60, chunk += 1) {
        const endRow = Math.min(rowCount, startRow + 59);
        const preview = await workbook.render({
          sheetName: sheetNames[index],
          range: `A${startRow}:${lastColumn}${endRow}`,
          scale: 1,
          format: "png",
        });
        const bytes = new Uint8Array(await preview.arrayBuffer());
        await fs.writeFile(`${outputDir}/${label}-${index + 1}-${chunk}.png`, bytes);
      }
    }
  }

  const formulaErrors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: `${label} formula error scan`,
  });

  const dump = { label, path, sheetNames, sheets, formulaErrors };
  await fs.writeFile(`${outputDir}/${label}.json`, JSON.stringify(dump, null, 2));
  return {
    label,
    path,
    sheetNames,
    sheetAddresses: sheets.map((sheet) => ({ name: sheet.name, address: sheet.address })),
    errorCount: String(formulaErrors.ndjson ?? "")
      .split(/\r?\n/)
      .filter((line) => line.includes('"kind":"match"')).length,
  };
}

const results = [];
results.push(await dumpWorkbook("manual", files.manual, true));
results.push(await dumpWorkbook("estimate", files.estimate));
results.push(await dumpWorkbook("buildern", files.buildern));

console.log(JSON.stringify(results, null, 2));
