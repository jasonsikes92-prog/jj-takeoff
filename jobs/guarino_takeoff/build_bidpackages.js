const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, WidthType, ShadingType, BorderStyle,
  HeadingLevel, PageBreak, VerticalAlign
} = require('docx');

// ---------- Project constants ----------
const NAVY = "1F3864";
const LIGHTBLUE = "D5E8F0";
const PROJ = {
  name: "Guarino Residence",
  address: "Lot 11 River Cove Meadows, Monticello, GA",
  id: "PR-111",
  builder: "J & J Custom Homes, LLC",
  county: "Newton County",
  type: "Custom New Home — 2,637 SF Heated (single-story, slab-on-grade; +1,204 SF conditioned garage, 347 SF covered porch)",
  date: "June 25, 2026",
  duration: "10 months"
};
const CONTACT = "Keli Rector — 404-934-8214 — keli@jnjcustomhomes.com — www.jnjcustomhomes.com";

const lines = JSON.parse(fs.readFileSync('scope_lines.json', 'utf-8'));

// ---------- Helpers ----------
function fmtQty(q) {
  if (q === null || q === undefined || q === '') return '—';
  if (typeof q === 'number') {
    let r = Math.round(q * 10) / 10;
    return (Number.isInteger(r) ? r.toString() : r.toString());
  }
  return String(q);
}
function run(text, opts = {}) { return new TextRun({ text, ...opts }); }
function para(children, opts = {}) {
  if (typeof children === 'string') children = [run(children)];
  return new Paragraph({ children, ...opts });
}
function bullet(text, level = 0) {
  return new Paragraph({ numbering: { reference: "bullets", level }, children: [run(text)] });
}
function bulletRuns(runs, level = 0) {
  return new Paragraph({ numbering: { reference: "bullets", level }, children: runs });
}
function sectionLabel(text) {
  return new Paragraph({
    spacing: { before: 200, after: 80 },
    children: [run(text, { bold: true, color: NAVY, size: 24 })]
  });
}

// Scope header bar: 2-col table, navy fill
function scopeHeaderBar(title, subtitle) {
  const cell = (children, w, align = AlignmentType.LEFT) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    margins: { top: 100, bottom: 100, left: 160, right: 160 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: align, children })]
  });
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [5400, 3960],
    rows: [new TableRow({ children: [
      cell([run(title, { bold: true, color: "FFFFFF", size: 28 })], 5400),
      cell([run(subtitle, { color: "FFFFFF", size: 20, italics: true })], 3960, AlignmentType.RIGHT)
    ]})]
  });
}

// Project info table (4-col)
function projectInfoTable() {
  const lbl = (l, v) => new TableCell({
    width: { size: 2340, type: WidthType.DXA },
    borders: allBorders("CCCCCC"),
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [
      new Paragraph({ children: [run(l, { bold: true, size: 16, color: "555555" })] }),
      new Paragraph({ children: [run(v, { size: 18 })] })
    ]
  });
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2340, 2340, 2340, 2340],
    rows: [new TableRow({ children: [
      lbl("PROJECT", PROJ.name),
      lbl("ADDRESS", PROJ.address),
      lbl("PROJECT ID", PROJ.id),
      lbl("BUILDER", PROJ.builder)
    ]})]
  });
}

function allBorders(color) {
  const b = { style: BorderStyle.SINGLE, size: 1, color };
  return { top: b, bottom: b, left: b, right: b };
}

// Quantities table from line items
function quantitiesTable(items) {
  const headerCell = (t, w) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: { fill: LIGHTBLUE, type: ShadingType.CLEAR },
    borders: allBorders("BBBBBB"),
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [run(t, { bold: true, size: 18 })] })]
  });
  const cell = (t, w, opts = {}) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: allBorders("CCCCCC"),
    margins: { top: 50, bottom: 50, left: 100, right: 100 },
    children: [new Paragraph({ children: [run(t, { size: 17, ...opts })] })]
  });
  const cols = [4360, 1200, 1200, 2600];
  const rows = [new TableRow({ tableHeader: true, children: [
    headerCell("Item Description", cols[0]),
    headerCell("Quantity", cols[1]),
    headerCell("Unit", cols[2]),
    headerCell("Notes / Spec", cols[3])
  ]})];
  for (const it of items) {
    let note = it.desc || '';
    if (it.allowance && !/allowance/i.test(note)) note = (note ? note + ' ' : '') + 'Allowance.';
    // trim redundancy: if note equals name, blank it
    if (note.trim() === it.name.trim()) note = it.allowance ? 'Allowance.' : '';
    rows.push(new TableRow({ children: [
      cell(it.name, cols[0]),
      cell(fmtQty(it.qty), cols[1]),
      cell(it.unit || '—', cols[2]),
      cell(note, cols[3])
    ]}));
  }
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: cols, rows });
}

// J&J standard requirements (identical every scope)
const STD_REQS = [
  `All work must comply with applicable 2018 IRC, state amendments, and ${PROJ.county} codes.`,
  "Subcontractor is responsible for all trade-specific permits and inspections (unless noted otherwise).",
  "Work areas to be cleaned and debris removed at end of each work day.",
  "Coordinate scheduling with J & J project manager a minimum of 72 hours in advance.",
  "Any work outside this scope requires a written change order signed by J & J before proceeding.",
  "Current General Liability and Workers Compensation COI required before work begins.",
  "All subcontractors must hold a current Georgia license for their trade.",
  "Verify all field dimensions before ordering or installing. Do not scale from drawings.",
  "Payment tied to draw schedule. Invoices at draw milestones only.",
  "Lien waiver (conditional) required with each invoice; final (unconditional) at completion."
];
const STD_REQS_SUPPLY = STD_REQS.filter(r => !/Georgia license/.test(r));

// ---------- Build one scope ----------
function buildScope(s) {
  const out = [];
  out.push(scopeHeaderBar(`${s.num} — ${s.title}`, s.subtitle));
  out.push(para([], { spacing: { after: 60 } }));
  out.push(projectInfoTable());

  out.push(sectionLabel("SCOPE OVERVIEW"));
  out.push(para([run(s.overview)], { spacing: { after: 40 } }));

  out.push(sectionLabel("SCOPE INCLUDES"));
  for (const inc of s.includes) {
    if (Array.isArray(inc)) out.push(bullet(inc[0], inc[1]));
    else out.push(bullet(inc));
  }

  out.push(sectionLabel("SCOPE EXCLUDES"));
  for (const ex of s.excludes) out.push(bullet(ex));

  out.push(sectionLabel("QUANTITIES & SPECIFICATIONS"));
  const items = lines[s.num] || [];
  if (items.length) out.push(quantitiesTable(items));
  else out.push(para([run("See drawings; quantities to be verified in field.", { italics: true })]));

  if (s.note) {
    out.push(sectionLabel("SPECIAL NOTES"));
    out.push(para([run("NOTE: ", { bold: true, italics: true }), run(s.note, { italics: true })]));
  }

  out.push(sectionLabel("APPLICABLE CODES & STANDARDS"));
  for (const c of s.codes) out.push(bullet(c));

  out.push(sectionLabel(s.supply ? "DELIVERY & RECEIPT CHECKLIST" : "INSPECTION & QUALITY CHECKLIST"));
  out.push(para([run(s.supply ? "PRE-DELIVERY — Confirm before shipping" : "PRE-WORK — Verify before starting", { bold: true, size: 20 })], { spacing: { before: 60, after: 40 } }));
  for (const p of s.prework) out.push(bullet(p));
  out.push(para([run(s.supply ? "RECEIPT — Required at delivery" : "COMPLETION — Before calling for inspection or payment", { bold: true, size: 20 })], { spacing: { before: 60, after: 40 } }));
  for (const c of s.completion) out.push(bullet(c));

  out.push(sectionLabel("J & J STANDARD REQUIREMENTS — ALL TRADES"));
  const reqs = s.supply ? STD_REQS_SUPPLY : STD_REQS;
  for (const r of reqs) out.push(bullet(r));

  out.push(para([run("Questions: ", { bold: true }), run(CONTACT, { bold: true })], { spacing: { before: 160 } }));
  out.push(new Paragraph({ children: [new PageBreak()] }));
  return out;
}

// ---------- Cover page ----------
function coverPage(scopeList) {
  const c = [];
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400, after: 0 },
    children: [run("J & J CUSTOM HOMES, LLC", { bold: true, size: 44, color: NAVY })] }));
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
    children: [run("133 West Washington Street, Suite D  |  Monticello, GA 31064  |  678-205-9383  |  www.jnjcustomhomes.com", { size: 18, color: "555555" })] }));
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 8 } }, children: [run("")] }));
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 500, after: 120 },
    children: [run("SUBCONTRACTOR BID PACKAGES", { bold: true, size: 40 })] }));
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
    children: [run(PROJ.name, { size: 32, color: NAVY })] }));

  // project info block
  const infoRow = (l, v) => new TableRow({ children: [
    new TableCell({ width: { size: 2600, type: WidthType.DXA }, borders: allBorders("DDDDDD"),
      margins: { top: 70, bottom: 70, left: 140, right: 140 }, shading: { fill: "F2F4F8", type: ShadingType.CLEAR },
      children: [new Paragraph({ children: [run(l, { bold: true, size: 18 })] })] }),
    new TableCell({ width: { size: 6760, type: WidthType.DXA }, borders: allBorders("DDDDDD"),
      margins: { top: 70, bottom: 70, left: 140, right: 140 },
      children: [new Paragraph({ children: [run(v, { size: 18 })] })] })
  ]});
  c.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [2600, 6760], rows: [
    infoRow("Project", PROJ.name),
    infoRow("Address", PROJ.address),
    infoRow("County", PROJ.county),
    infoRow("Project Type", PROJ.type),
    infoRow("Project ID", PROJ.id),
    infoRow("Est. Duration", PROJ.duration),
    infoRow("Builder", PROJ.builder),
    infoRow("Revision Date", PROJ.date)
  ]}));

  c.push(new Paragraph({ spacing: { before: 360, after: 200 }, children: [
    run(`This document contains ${scopeList.length} individual scope-of-work packages for the ${PROJ.name}. Each package defines the work, quantities, applicable codes, and quality requirements for one trade. Quantities are derived from the J & J estimate and takeoff; all subcontractors must verify field dimensions before ordering or installing.`, { size: 20 })
  ]}));

  c.push(sectionLabel("PACKAGES INCLUDED"));
  for (const s of scopeList) {
    c.push(new Paragraph({ numbering: { reference: "toc", level: 0 }, children: [
      run(`${s.num} — ${s.title}`, { size: 18 })
    ]}));
  }
  c.push(new Paragraph({ spacing: { before: 200 }, children: [run("Questions: ", { bold: true }), run(CONTACT, { bold: true })] }));
  c.push(new Paragraph({ children: [new PageBreak()] }));
  return c;
}

// ============ SCOPE DEFINITIONS ============
const scopes = require('./scopes_data.js')(PROJ);

// ---------- Assemble ----------
const children = [];
children.push(...coverPage(scopes));
for (const s of scopes) children.push(...buildScope(s));

const doc = new Document({
  styles: { default: { document: { run: { font: "Arial", size: 20 } } } },
  numbering: { config: [
    { reference: "bullets", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 260 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 920, hanging: 260 } } } }
    ]},
    { reference: "toc", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 0 } } } }
    ]}
  ]},
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  const outPath = "Guarino Residence_PR-111_BidPackages_2026-06-25.docx";
  fs.writeFileSync(outPath, buf);
  console.log("WROTE", outPath, "scopes:", scopes.length);
});
