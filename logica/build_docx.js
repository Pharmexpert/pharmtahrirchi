const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, HeadingLevel,
  VerticalAlign
} = require('docx');
const fs = require('fs');

const data = JSON.parse(fs.readFileSync('content_data.json', 'utf8'));

const { en, ru, uz } = data;

const border = { style: BorderStyle.SINGLE, size: 4, color: '999999' };
const borders = { top: border, bottom: border, left: border, right: border };
const headerBorder = { style: BorderStyle.SINGLE, size: 6, color: '2E4057' };
const headerBorders = { top: headerBorder, bottom: headerBorder, left: headerBorder, right: headerBorder };

// Page: A4 landscape for 3 columns
// A4: 11906 x 16838 DXA. Landscape: 16838 x 11906
// margins: 720 each side
// content width: 16838 - 1440 = 15398 DXA
// 3 cols: ~5132 each
const TOTAL_WIDTH = 15398;
const COL_W = Math.floor(TOTAL_WIDTH / 3);
const COL_WIDTHS = [COL_W, COL_W, TOTAL_WIDTH - COL_W * 2];

function makeParas(text) {
  if (!text) return [new Paragraph({ children: [new TextRun('')] })];
  return [new Paragraph({
    children: [new TextRun({ text: text, size: 18 })],
    spacing: { before: 60, after: 60 }
  })];
}

function makeTableCell(item, colWidth, isHeader = false) {
  let children = [];
  
  if (item.type === 'para') {
    children = [new Paragraph({
      children: [new TextRun({
        text: item.text,
        size: isHeader ? 20 : 18,
        bold: isHeader,
        color: isHeader ? '1F3A5F' : undefined
      })],
      spacing: { before: 60, after: 60 }
    })];
  } else if (item.type === 'table') {
    // Create an inner table
    const innerRows = item.rows.map(row => {
      const numCols = row.length;
      const innerColW = Math.floor((colWidth - 200) / Math.max(numCols, 1));
      return new TableRow({
        children: row.map((cellText, ci) => {
          const w = ci === row.length - 1 ? (colWidth - 200) - innerColW * (row.length - 1) : innerColW;
          return new TableCell({
            borders,
            width: { size: w, type: WidthType.DXA },
            margins: { top: 40, bottom: 40, left: 80, right: 80 },
            children: [new Paragraph({
              children: [new TextRun({ text: cellText, size: 16 })],
              spacing: { before: 40, after: 40 }
            })]
          });
        })
      });
    });
    
    const numCols = item.rows[0] ? item.rows[0].length : 1;
    const innerColW = Math.floor((colWidth - 200) / Math.max(numCols, 1));
    const colWidths = item.rows[0] 
      ? item.rows[0].map((_, ci) => ci === item.rows[0].length - 1 
          ? (colWidth - 200) - innerColW * (item.rows[0].length - 1) 
          : innerColW)
      : [colWidth - 200];
    
    children = [new Table({
      width: { size: colWidth - 200, type: WidthType.DXA },
      columnWidths: colWidths,
      rows: innerRows
    })];
  }
  
  return new TableCell({
    borders,
    width: { size: colWidth, type: WidthType.DXA },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    verticalAlign: VerticalAlign.TOP,
    children: children
  });
}

// Build rows
const tableRows = [];

// Header row
tableRows.push(new TableRow({
  tableHeader: true,
  children: [
    new TableCell({
      borders: headerBorders,
      width: { size: COL_WIDTHS[0], type: WidthType.DXA },
      shading: { fill: '2E4057', type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 150, right: 150 },
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: 'Инглиз тилида', size: 22, bold: true, color: 'FFFFFF' })]
      })]
    }),
    new TableCell({
      borders: headerBorders,
      width: { size: COL_WIDTHS[1], type: WidthType.DXA },
      shading: { fill: '2E4057', type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 150, right: 150 },
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: 'Рус тилида', size: 22, bold: true, color: 'FFFFFF' })]
      })]
    }),
    new TableCell({
      borders: headerBorders,
      width: { size: COL_WIDTHS[2], type: WidthType.DXA },
      shading: { fill: '2E4057', type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 150, right: 150 },
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: 'Ўзбек тилида', size: 22, bold: true, color: 'FFFFFF' })]
      })]
    })
  ]
}));

// Content rows - one row per meaningful EN item
for (let i = 0; i < en.length; i++) {
  const enItem = en[i];
  const ruItem = ru[i] || { type: 'para', text: '' };
  const uzItem = uz[i] || { type: 'para', text: '' };
  
  // Alternate row shading
  const shade = i % 2 === 0 ? 'F8F9FA' : 'FFFFFF';
  
  tableRows.push(new TableRow({
    children: [
      makeTableCell(enItem, COL_WIDTHS[0]),
      makeTableCell(ruItem, COL_WIDTHS[1]),
      makeTableCell(uzItem, COL_WIDTHS[2])
    ]
  }));
}

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: 'Arial', size: 18 } }
    }
  },
  sections: [{
    properties: {
      page: {
        size: {
          width: 11906,
          height: 16838,
          orientation: 'landscape'
        },
        margin: { top: 720, right: 720, bottom: 720, left: 720 }
      }
    },
    children: [
      new Table({
        width: { size: TOTAL_WIDTH, type: WidthType.DXA },
        columnWidths: COL_WIDTHS,
        rows: tableRows
      })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('output_aligned.docx', buffer);
  console.log('Done! output_aligned.docx created');
});
