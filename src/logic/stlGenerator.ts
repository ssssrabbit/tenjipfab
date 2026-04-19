import JSZip from 'jszip';
import { BRAILLE_MAP, NUM_INDICATOR, SPACE_MARK, BrailleCell } from './brailleLogic';

type Vec3 = [number, number, number];
type Triangle = [Vec3, Vec3, Vec3, Vec3]; // [normal, v1, v2, v3]

// ---- BSE ASCII マップ ----
const BSE_MAP: Record<number, string> = {
  0x00: ' ', 0x01: 'a', 0x03: 'b', 0x09: 'c', 0x19: 'd', 0x11: 'e',
  0x0B: 'f', 0x1B: 'g', 0x13: 'h', 0x0A: 'i', 0x1A: 'j', 0x05: 'k',
  0x07: 'l', 0x0D: 'm', 0x1D: 'n', 0x15: 'o', 0x0F: 'p', 0x1F: 'q',
  0x17: 'r', 0x0E: 's', 0x1E: 't', 0x25: 'u', 0x27: 'v', 0x3A: 'w',
  0x2D: 'x', 0x3D: 'y', 0x35: 'z',
  0x3C: '#', 0x30: ';', 0x10: '"', 0x20: ',', 0x08: '@', 0x18: '^', 0x28: '_',
  0x02: '1', 0x06: '2', 0x12: '3', 0x32: '4', 0x22: '5', 0x16: '6',
  0x36: '7', 0x26: '8', 0x14: '9', 0x34: '0',
  0x04: "'", 0x0C: '/', 0x1C: '>', 0x24: '-', 0x2C: '%', 0x3E: '=',
  0x21: '*', 0x23: '<', 0x29: '[', 0x2B: '$', 0x2F: '+', 0x31: ']',
  0x33: ':', 0x37: '?', 0x38: '!', 0x39: '(', 0x3B: ')', 0x3F: '|',
};

// ---- ユーティリティ ----

function dotsToUnicode(dots: number[]): string {
  let code = 0x2800;
  if (dots[0]) code += 0x01;
  if (dots[1]) code += 0x02;
  if (dots[2]) code += 0x04;
  if (dots[3]) code += 0x08;
  if (dots[4]) code += 0x10;
  if (dots[5]) code += 0x20;
  return String.fromCodePoint(code);
}

function intToBrailleDots(n: number): number[][] {
  const s = String(n);
  const dots: number[][] = [NUM_INDICATOR];
  for (const ch of s) {
    dots.push(BRAILLE_MAP[ch] ?? SPACE_MARK);
  }
  return dots;
}

// ---- STL バイナリ生成ヘルパー ----

function writeFloat32LE(view: DataView, offset: number, value: number): void {
  view.setFloat32(offset, value, true);
}

function writeUint32LE(view: DataView, offset: number, value: number): void {
  view.setUint32(offset, value, true);
}

function writeUint16LE(view: DataView, offset: number, value: number): void {
  view.setUint16(offset, value, true);
}

function buildStlBinary(triangles: Triangle[]): ArrayBuffer {
  const HEADER_SIZE = 80;
  const NUM_TRIS_SIZE = 4;
  const TRI_SIZE = 50; // 4*3 normal + 4*3*3 verts + 2 attr

  const numTris = triangles.length;
  const totalSize = HEADER_SIZE + NUM_TRIS_SIZE + numTris * TRI_SIZE;
  const buf = new ArrayBuffer(totalSize);
  const view = new DataView(buf);

  // Header: "Tenji P-Fab Generated STL" + zero-padding
  const headerStr = 'Tenji P-Fab Generated STL';
  for (let i = 0; i < headerStr.length; i++) {
    view.setUint8(i, headerStr.charCodeAt(i));
  }

  writeUint32LE(view, 80, numTris);

  let offset = 84;
  for (const [, v1, v2, v3] of triangles) {
    // normal (always 0,0,0)
    writeFloat32LE(view, offset, 0); offset += 4;
    writeFloat32LE(view, offset, 0); offset += 4;
    writeFloat32LE(view, offset, 0); offset += 4;
    // v1
    writeFloat32LE(view, offset, v1[0]); offset += 4;
    writeFloat32LE(view, offset, v1[1]); offset += 4;
    writeFloat32LE(view, offset, v1[2]); offset += 4;
    // v2
    writeFloat32LE(view, offset, v2[0]); offset += 4;
    writeFloat32LE(view, offset, v2[1]); offset += 4;
    writeFloat32LE(view, offset, v2[2]); offset += 4;
    // v3
    writeFloat32LE(view, offset, v3[0]); offset += 4;
    writeFloat32LE(view, offset, v3[1]); offset += 4;
    writeFloat32LE(view, offset, v3[2]); offset += 4;
    // attribute
    writeUint16LE(view, offset, 0); offset += 2;
  }
  return buf;
}

// ---- ジオメトリ生成 ----

function generateRoundedRectPath(w: number, h: number, r: number, segmentsPerCorner = 8): [number, number][] {
  const points: [number, number][] = [];
  const corners: [number, number, number][] = [
    [w - r, h - r, 0],
    [r,     h - r, Math.PI / 2],
    [r,     r,     Math.PI],
    [w - r, r,     3 * Math.PI / 2],
  ];
  for (const [cx, cy, startAngle] of corners) {
    for (let i = 0; i <= segmentsPerCorner; i++) {
      const ang = startAngle + (Math.PI / 2) * (i / segmentsPerCorner);
      points.push([cx + r * Math.cos(ang), cy + r * Math.sin(ang)]);
    }
  }
  return points;
}

function addPlateWithHole(
  triangles: Triangle[],
  width: number, height: number, depth: number,
  cornerRadius: number,
  holeCx: number, holeCy: number, holeR: number,
): void {
  const outerPoints = generateRoundedRectPath(width, height, cornerRadius);
  const holePoints: [number, number][] = outerPoints.map(([px, py]) => {
    const vx = px - holeCx;
    const vy = py - holeCy;
    let dist = Math.sqrt(vx * vx + vy * vy);
    if (dist === 0) dist = 0.001;
    return [holeCx + (vx / dist) * holeR, holeCy + (vy / dist) * holeR];
  });

  const n = outerPoints.length;
  for (let i = 0; i < n; i++) {
    const ni = (i + 1) % n;
    const o1: Vec3 = [outerPoints[i][0],  outerPoints[i][1],  depth];
    const o2: Vec3 = [outerPoints[ni][0], outerPoints[ni][1], depth];
    const i1: Vec3 = [holePoints[i][0],   holePoints[i][1],   depth];
    const i2: Vec3 = [holePoints[ni][0],  holePoints[ni][1],  depth];
    triangles.push([[0,0,1], o1, o2, i1]);
    triangles.push([[0,0,1], i1, o2, i2]);

    const o1b: Vec3 = [outerPoints[i][0],  outerPoints[i][1],  0];
    const o2b: Vec3 = [outerPoints[ni][0], outerPoints[ni][1], 0];
    const i1b: Vec3 = [holePoints[i][0],   holePoints[i][1],   0];
    const i2b: Vec3 = [holePoints[ni][0],  holePoints[ni][1],  0];
    triangles.push([[0,0,-1], o1b, i1b, o2b]);
    triangles.push([[0,0,-1], i1b, i2b, o2b]);
    triangles.push([[0,0,0],  o1b, o2b, o2]);
    triangles.push([[0,0,0],  o1b, o2,  o1]);
    triangles.push([[0,0,0],  i1b, i1,  i2b]);
    triangles.push([[0,0,0],  i2b, i1,  i2]);
  }
}

function addTube(
  triangles: Triangle[],
  cx: number, cy: number, zBase: number,
  rInner: number, rOuter: number, height: number,
): void {
  const segments = 32;
  const topZ = zBase + height;
  for (let i = 0; i < segments; i++) {
    const ang1 = 2 * Math.PI * i / segments;
    const ang2 = 2 * Math.PI * (i + 1) / segments;
    const idx1 = cx + rInner * Math.cos(ang1); const idy1 = cy + rInner * Math.sin(ang1);
    const idx2 = cx + rInner * Math.cos(ang2); const idy2 = cy + rInner * Math.sin(ang2);
    const odx1 = cx + rOuter * Math.cos(ang1); const ody1 = cy + rOuter * Math.sin(ang1);
    const odx2 = cx + rOuter * Math.cos(ang2); const ody2 = cy + rOuter * Math.sin(ang2);
    const pI1: Vec3 = [idx1, idy1, topZ]; const pI2: Vec3 = [idx2, idy2, topZ];
    const pO1: Vec3 = [odx1, ody1, topZ]; const pO2: Vec3 = [odx2, ody2, topZ];
    triangles.push([[0,0,1], pO1, pO2, pI1]);
    triangles.push([[0,0,1], pI1, pO2, pI2]);
    const bO1: Vec3 = [odx1, ody1, zBase]; const bO2: Vec3 = [odx2, ody2, zBase];
    triangles.push([[0,0,0], bO1, bO2, pO2]);
    triangles.push([[0,0,0], bO1, pO2, pO1]);
    const bI1: Vec3 = [idx1, idy1, zBase]; const bI2: Vec3 = [idx2, idy2, zBase];
    triangles.push([[0,0,0], bI1, pI1, bI2]);
    triangles.push([[0,0,0], bI2, pI1, pI2]);
  }
}

function addDotMesh(triangles: Triangle[], cx: number, cy: number, cz: number, r: number, h: number): void {
  const segments = 24;
  const rings = 6;
  const flatRatio = 0.75;
  const thetaLimit = (Math.PI / 2) * flatRatio;
  const sinLimit = Math.sin(thetaLimit);
  const zScale = 1.0 / sinLimit;

  let prevRing: Vec3[] = [];
  for (let i = 0; i < segments; i++) {
    const angle = 2 * Math.PI * i / segments;
    prevRing.push([cx + r * Math.cos(angle), cy + r * Math.sin(angle), cz]);
  }

  for (let j = 1; j <= rings; j++) {
    const theta = thetaLimit * (j / rings);
    const zCurr = j === rings ? cz + h : cz + h * Math.sin(theta) * zScale;
    const rCurr = r * Math.cos(theta);
    const currRing: Vec3[] = [];

    for (let i = 0; i < segments; i++) {
      const angle = 2 * Math.PI * i / segments;
      currRing.push([cx + rCurr * Math.cos(angle), cy + rCurr * Math.sin(angle), zCurr]);
    }

    for (let i = 0; i < segments; i++) {
      const ni = (i + 1) % segments;
      triangles.push([[0,0,1], prevRing[i], prevRing[ni], currRing[i]]);
      triangles.push([[0,0,1], currRing[i], prevRing[ni], currRing[ni]]);
    }

    if (j === rings) {
      const topCenter: Vec3 = [cx, cy, zCurr];
      for (let i = 0; i < segments; i++) {
        triangles.push([[0,0,1], currRing[i], currRing[(i + 1) % segments], topCenter]);
      }
    }

    prevRing = currRing;
  }
}

function addBrailleChar(
  triangles: Triangle[],
  dots: number[], x: number, y: number, zBase: number,
  dia: number, height: number, px: number, py: number,
): void {
  const offsets: [number, number][] = [
    [0, 2*py], [0, py], [0, 0],
    [px, 2*py], [px, py], [px, 0],
  ];
  dots.forEach((isOn, i) => {
    if (isOn) {
      const [dx, dy] = offsets[i];
      addDotMesh(triangles, x + dx + dia / 2, y + dy + dia / 2, zBase, dia / 2, height);
    }
  });
}

// ---- OBJ テキスト生成 ----

function buildObjText(plateTriangles: Triangle[], dotTriangles: Triangle[]): string {
  const parts: string[] = ['# Tenji P-Fab Generated OBJ'];
  let vOffset = 1;

  const writeObject = (name: string, tris: Triangle[]) => {
    parts.push(`o ${name}`);
    for (const [, v1, v2, v3] of tris) {
      parts.push(`v ${v1[0].toFixed(4)} ${v1[1].toFixed(4)} ${v1[2].toFixed(4)}`);
      parts.push(`v ${v2[0].toFixed(4)} ${v2[1].toFixed(4)} ${v2[2].toFixed(4)}`);
      parts.push(`v ${v3[0].toFixed(4)} ${v3[1].toFixed(4)} ${v3[2].toFixed(4)}`);
    }
    for (let i = 0; i < tris.length; i++) {
      const b = vOffset + i * 3;
      parts.push(`f ${b} ${b + 1} ${b + 2}`);
    }
    vOffset += tris.length * 3;
  };

  writeObject('plate', plateTriangles);
  writeObject('dots', dotTriangles);

  return parts.join('\n');
}

// ---- プレート ジオメトリ生成 ----

interface PlateGeometry {
  plateTriangles: Triangle[];
  dotTriangles: Triangle[];
}

function createPlateGeometry(bodyLinesDots: number[][][], pageNumDots: number[][], baseThickness: number, dotHeight = 0.4): PlateGeometry {
  const DOT_BASE_DIA = 1.6;
  const DOT_HEIGHT   = dotHeight;
  const DOT_PITCH_X  = 2.2;
  const DOT_PITCH_Y  = 2.4;
  const CHAR_PITCH   = 6.0;
  const LINE_HEIGHT  = 10.0;
  const LINE_PITCH   = 12.0;
  const MARGIN_TOP    = 4.0;
  const MARGIN_BOTTOM = 4.0;
  const MARGIN_RIGHT  = 4.0;
  const MARGIN_LEFT   = 4.0;
  const HOLE_DIA         = 5.0;
  const HOLE_RADIUS      = HOLE_DIA / 2;
  const HOLE_RING_WIDTH  = 1.5;

  let leftSideWidth = Math.max(HOLE_DIA + HOLE_RING_WIDTH * 2 + 4.0, pageNumDots.length * CHAR_PITCH);
  if (leftSideWidth < 15.0) leftSideWidth = 15.0;

  const numLines = bodyLinesDots.length;
  const maxLineChars = bodyLinesDots.reduce((m, l) => Math.max(m, l.length), 0);
  const bodyWidth = maxLineChars * CHAR_PITCH;

  const totalWidth = MARGIN_LEFT + leftSideWidth + bodyWidth + MARGIN_RIGHT;
  let totalHeight = MARGIN_TOP + LINE_HEIGHT + (numLines - 1) * LINE_PITCH + MARGIN_BOTTOM;
  const minHeightForHole = (HOLE_RADIUS + HOLE_RING_WIDTH) * 2 + 4.0;
  if (totalHeight < minHeightForHole) totalHeight = minHeightForHole;

  const plateTriangles: Triangle[] = [];
  const dotTriangles: Triangle[] = [];

  const holeCx = MARGIN_LEFT + HOLE_RADIUS + HOLE_RING_WIDTH;
  const holeCy = totalHeight - (MARGIN_TOP + HOLE_RADIUS + HOLE_RING_WIDTH);

  addPlateWithHole(plateTriangles, totalWidth, totalHeight, baseThickness, 3.0, holeCx, holeCy, HOLE_RADIUS);
  addTube(plateTriangles, holeCx, holeCy, baseThickness, HOLE_RADIUS, HOLE_RADIUS + HOLE_RING_WIDTH, DOT_HEIGHT);

  const dotsYOffset = DOT_PITCH_Y;
  let pageNumX = MARGIN_LEFT;
  const pageContentWidth = pageNumDots.length * CHAR_PITCH;
  if (pageContentWidth < leftSideWidth) pageNumX += (leftSideWidth - pageContentWidth) / 2;
  const pageNumY = MARGIN_BOTTOM + LINE_HEIGHT / 2 - dotsYOffset;

  let curX = pageNumX;
  for (const charDots of pageNumDots) {
    addBrailleChar(dotTriangles, charDots, curX, pageNumY, baseThickness, DOT_BASE_DIA, DOT_HEIGHT, DOT_PITCH_X, DOT_PITCH_Y);
    curX += CHAR_PITCH;
  }

  const bodyStartX = MARGIN_LEFT + leftSideWidth;
  const firstLineCenterY = totalHeight - MARGIN_TOP - LINE_HEIGHT / 2;

  for (let i = 0; i < bodyLinesDots.length; i++) {
    const lineCenterY = firstLineCenterY - i * LINE_PITCH;
    const lineY = lineCenterY - dotsYOffset;
    let lineX = bodyStartX;
    for (const charDots of bodyLinesDots[i]) {
      addBrailleChar(dotTriangles, charDots, lineX, lineY, baseThickness, DOT_BASE_DIA, DOT_HEIGHT, DOT_PITCH_X, DOT_PITCH_Y);
      lineX += CHAR_PITCH;
    }
  }

  return { plateTriangles, dotTriangles };
}

function createPlateStl(bodyLinesDots: number[][][], pageNumDots: number[][], baseThickness: number, dotHeight?: number): ArrayBuffer {
  const { plateTriangles, dotTriangles } = createPlateGeometry(bodyLinesDots, pageNumDots, baseThickness, dotHeight);
  return buildStlBinary([...plateTriangles, ...dotTriangles]);
}

function createPlateObj(bodyLinesDots: number[][][], pageNumDots: number[][], baseThickness: number, dotHeight?: number): string {
  const { plateTriangles, dotTriangles } = createPlateGeometry(bodyLinesDots, pageNumDots, baseThickness, dotHeight);
  return buildObjText(plateTriangles, dotTriangles);
}

// ---- BSE / HTML 生成 ----

function generateBseContent(platesData: BrailleCell[][][]): string {
  const lines: string[] = [];
  for (const plate of platesData) {
    for (const lineCells of plate) {
      let lineStr = '';
      for (const cell of lineCells) {
        const d = cell.dots;
        const val = (d[0] ? 1 : 0) | (d[1] ? 2 : 0) | (d[2] ? 4 : 0) |
                    (d[3] ? 8 : 0) | (d[4] ? 16 : 0) | (d[5] ? 32 : 0);
        lineStr += BSE_MAP[val] ?? '?';
      }
      lines.push(lineStr);
    }
    lines.push('');
  }
  return lines.join('\r\n');
}

function generateGuideHtml(pagesInfo: PageInfo[]): string {
  let rows = '';
  for (const info of pagesInfo) {
    const pageBrailleStr = info.pageDots.map(dotsToUnicode).join('');
    rows += `<div class='plate-block'><h2>Plate ${String(info.pageNum).padStart(2, '0')} <span class='page-braille'>(${pageBrailleStr})</span></h2>`;
    rows += "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse: collapse; width: 100%;'>";
    rows += "<tr style='background-color: #f0f0f0;'><th>Line</th><th>Content</th></tr>";

    info.plateLines.forEach((lineCells, lineIdx) => {
      let lineHtml = '';
      for (const cell of lineCells) {
        const uni = dotsToUnicode(cell.dots);
        lineHtml += `<div style='display:inline-block; text-align:center; margin:2px; border:1px solid #eee; padding:2px;'><div style='font-size:20px;'>${uni}</div><div style='font-size:12px;'>${cell.char}</div></div>`;
      }
      rows += `<tr><td align='center' width='50'>L${lineIdx + 1}</td><td>${lineHtml}</td></tr>`;
    });
    rows += '</table></div><br>';
  }

  return `<html><head><meta charset="UTF-8">
<style>
  body { font-family: "Noto Sans JP", sans-serif; padding: 20px; color: #333; }
  h2 { border-bottom: 2px solid #007AFF; margin-top: 30px; }
  .page-braille { font-size: 1.5em; color: #555; vertical-align: middle; }
  .plate-block { page-break-inside: avoid; margin-bottom: 40px; }
  table { width: 100%; border: 1px solid #ddd; }
  th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
</style>
</head><body>
  <h1>Tenji P-Fab Export Guide</h1>
  ${rows}
</body></html>`;
}

// ---- パブリックAPI ----

interface PageInfo {
  pageNum: number;
  plateLines: BrailleCell[][];
  pageDots: number[][];
  bodyLinesDots: number[][][];
}

export interface GenerateOptions {
  maxCharsPerLine?: number;
  maxLinesPerPlate?: number;
  baseThickness?: number;
  dotHeight?: number;
  originalText?: string;
}

export async function generatePackageZip(
  flatCells: BrailleCell[],
  options: GenerateOptions = {},
): Promise<string> {
  const {
    maxCharsPerLine = 10,
    maxLinesPerPlate = 1,
    baseThickness = 1.0,
    originalText = '',
  } = options;

  const lines: BrailleCell[][] = [];
  for (let i = 0; i < flatCells.length; i += maxCharsPerLine) {
    lines.push(flatCells.slice(i, i + maxCharsPerLine));
  }
  const plates: BrailleCell[][][] = [];
  for (let i = 0; i < lines.length; i += maxLinesPerPlate) {
    plates.push(lines.slice(i, i + maxLinesPerPlate));
  }
  return generatePackageFromPlates(plates, { baseThickness, originalText });
}

export async function generatePackageFromPlates(
  platesData: BrailleCell[][][],
  options: Pick<GenerateOptions, 'baseThickness' | 'dotHeight' | 'originalText'> = {},
): Promise<string> {
  const { baseThickness = 1.0, dotHeight = 0.4, originalText = '' } = options;

  const zip = new JSZip();
  zip.file('original_text.txt', originalText);
  zip.file('braille.bse', generateBseContent(platesData));

  const pagesInfo: PageInfo[] = platesData.map((plateLines, idx) => ({
    pageNum: idx + 1,
    plateLines,
    pageDots: intToBrailleDots(idx + 1),
    bodyLinesDots: plateLines.map((line) => line.map((c) => c.dots)),
  }));

  zip.file('guide_sheet.html', generateGuideHtml(pagesInfo));

  for (const info of pagesInfo) {
    const prefix = `plate_${String(info.pageNum).padStart(2, '0')}`;
    const stlBuf = createPlateStl(info.bodyLinesDots, info.pageDots, baseThickness, dotHeight);
    zip.file(`${prefix}.stl`, stlBuf);
    const objText = createPlateObj(info.bodyLinesDots, info.pageDots, baseThickness, dotHeight);
    zip.file(`${prefix}.obj`, objText);
  }

  return zip.generateAsync({ type: 'base64' });
}
