#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const key = argv[i];
    if (!key.startsWith('--')) continue;
    const name = key.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[name] = true;
    } else {
      args[name] = next;
      i++;
    }
  }
  return args;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function num(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function round4(value) {
  return Number(Number(value).toFixed(4));
}

const CJK_RE = /[\u3400-\u9fff]/;
const COMMON_SVG_RE = /\/?(\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+)\.svg\b/gi;
const COMMON_POINTER_PREFIX = '循序圖請參考：';

function parseCommonMethodName(baseName) {
  const match = String(baseName || '').match(/\.(\w+)$/);
  return match ? match[1] : '';
}

function normalizeCommonDescription(value, methodName, baseName) {
  let text = String(value || '')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text) return '';
  text = text.replace(/\.svg\b/gi, '').trim();
  if (baseName && text.startsWith(baseName)) text = text.slice(baseName.length).trim();
  if (methodName && text.startsWith(methodName)) text = text.slice(methodName.length).trim();
  text = text.replace(/^[\s:：/_-]+/, '').trim();
  text = text.replace(/\s+(包含[^（）()\s]+)\s*$/u, '（$1）');
  text = text.replace(/\s+/g, '');
  return CJK_RE.test(text) ? text : '';
}

function findProjectRoot(inputPath) {
  let current = path.dirname(path.resolve(inputPath));
  while (current && current !== path.dirname(current)) {
    if (
      fs.existsSync(path.join(current, 'v1.x Reference', '共用svg')) ||
      fs.existsSync(path.join(current, 'output'))
    ) {
      return current;
    }
    current = path.dirname(current);
  }
  return process.cwd();
}

function walkJson(value, visitor) {
  if (Array.isArray(value)) {
    visitor(value);
    for (const item of value) walkJson(item, visitor);
  } else if (value && typeof value === 'object') {
    for (const item of Object.values(value)) walkJson(item, visitor);
  } else if (typeof value === 'string') {
    visitor(value);
  }
}

function addMethodDescription(map, methodName, description) {
  const normalized = normalizeCommonDescription(description, methodName, '');
  if (methodName && normalized && !map.has(methodName)) map.set(methodName, normalized);
}

function collectMethodDescriptionFromText(map, text) {
  const source = String(text || '').trim();
  let match = source.match(/\.([A-Za-z][A-Za-z0-9_]+)\s*([^\r\n]*[\u3400-\u9fff][^\r\n]*)/u);
  if (match) {
    addMethodDescription(map, match[1], match[2]);
    return;
  }
  match = source.match(/^([A-Za-z][A-Za-z0-9_]+)\s*([^\r\n]*[\u3400-\u9fff][^\r\n]*)/u);
  if (match) addMethodDescription(map, match[1], match[2]);
}

function buildCommonSvgDisplayCatalog(inputPath) {
  const root = findProjectRoot(inputPath);
  const exact = new Map();
  const byMethod = new Map();
  const outputDir = path.join(root, 'output');
  for (const fileName of [
    'commonfunc_format_check_conservative.json',
    'commonfunc_format_check.json',
    'commonfunc_format_update_list.json',
  ]) {
    const file = path.join(outputDir, fileName);
    if (!fs.existsSync(file)) continue;
    try {
      const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
      walkJson(parsed, (item) => {
        if (typeof item === 'string') {
          collectMethodDescriptionFromText(byMethod, item);
          return;
        }
        if (!Array.isArray(item) || item.length < 7) return;
        const methodName = String(item[1] || '').trim();
        const description = String(item[2] || '').trim();
        const svgName = String(item[6] || '').trim();
        if (!methodName || !description || !/\.svg$/i.test(svgName)) return;
        const baseName = path.agentname(svgName, '.svg');
        const normalized = normalizeCommonDescription(description, methodName, baseName);
        if (normalized) {
          exact.set(baseName, normalized);
          addMethodDescription(byMethod, methodName, normalized);
        }
      });
    } catch {
      // Optional catalog only; SVG metadata and explicit spec text remain the fallback.
    }
  }

  const svgDir = path.join(root, 'v1.x Reference', '共用svg');
  if (fs.existsSync(svgDir)) {
    for (const entry of fs.readdirSync(svgDir)) {
      if (!/\.svg$/i.test(entry)) continue;
      const baseName = path.agentname(entry, '.svg');
      const methodName = parseCommonMethodName(baseName);
      try {
        const svg = fs.readFileSync(path.join(svgDir, entry), 'utf8');
        const candidates = [];
        for (const match of svg.matchAll(/<(?:title|desc)>([\s\S]*?)<\/(?:title|desc)>/gi)) {
          candidates.push(match[1]);
        }
        for (const candidate of candidates) {
          if (!String(candidate).includes(baseName) && (!methodName || !String(candidate).includes(methodName))) {
            continue;
          }
          const normalized = normalizeCommonDescription(candidate, methodName, baseName);
          if (normalized) {
            if (!exact.has(baseName)) exact.set(baseName, normalized);
            addMethodDescription(byMethod, methodName, normalized);
            break;
          }
        }
      } catch {
        // Ignore unreadable optional reference SVGs.
      }
    }
  }
  return { exact, byMethod };
}

function formatCommonSvgReferenceText(text, catalog) {
  if (!text) return text;
  let output = String(text);
  COMMON_SVG_RE.lastIndex = 0;
  output = output.replace(COMMON_SVG_RE, (_match, baseName) => {
    const methodName = parseCommonMethodName(baseName);
    const description = catalog.exact.get(baseName) || catalog.byMethod.get(methodName) || '';
    return `${baseName}${description ? ` ${description}` : ''}`;
  });
  const displayMatch = output.match(/\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+.*$/);
  if (displayMatch) {
    const displayText = displayMatch[0].trim().replace(/^循序圖請參考[:：]\s*/, '');
    return `${COMMON_POINTER_PREFIX}${displayText}`;
  }
  return output;
}

function normalizeCommonSvgReferenceTexts(spec, catalog) {
  const pages = Array.isArray(spec.pages) ? spec.pages : [spec];
  for (const page of pages) {
    for (const pointer of page.orangePointers || []) {
      pointer.text = formatCommonSvgReferenceText(pointer.text, catalog);
    }
    for (const block of page.refCommonSvgBlocks || []) {
      block.pointerText = formatCommonSvgReferenceText(block.pointerText, catalog);
    }
  }
}

function expandShortBusinessGroups(page, unit) {
  const frames = Array.isArray(page.frames) ? page.frames : [];
  if (!frames.length) return;
  const ordered = frames
    .map((frame, index) => ({ frame, index }))
    .sort((a, b) => num(a.frame.top) - num(b.frame.top) || a.index - b.index);

  for (let i = 0; i < ordered.length - 1; i++) {
    const group = ordered[i].frame;
    if (group.kind !== 'group') continue;
    const groupTop = num(group.top);
    const groupHeight = num(group.height);
    if (groupHeight > unit * 8) continue;

    const groupBottom = groupTop + groupHeight;
    const child = ordered[i + 1].frame;
    if (!child || !['alt', 'opt', 'ref', 'group', 'loop'].includes(child.kind)) continue;
    const childTop = num(child.top);
    if (childTop < groupTop || childTop - groupBottom > unit * 4) continue;

    const sidePadding = Math.max(0.08, unit * 0.5);
    const bottomPadding = Math.max(unit, unit * 1.0);
    const childLeft = num(child.left);
    const childRight = childLeft + num(child.width);
    const childBottom = childTop + num(child.height);
    const currentLeft = num(group.left);
    const currentRight = currentLeft + num(group.width);
    const left = round4(Math.min(currentLeft, childLeft - sidePadding));
    const right = round4(Math.max(currentRight, childRight + sidePadding));

    group.left = left;
    group.width = round4(right - left);
    group.height = round4(snap(childBottom + bottomPadding, unit, 'ceil') - groupTop);
    group.layoutPlanned = true;
    group.containsNextFragment = true;
  }
}

function snap(value, unit, mode = 'nearest') {
  if (!unit || unit <= 0) return round4(value);
  const scaled = value / unit;
  if (mode === 'floor') return round4(Math.floor(scaled) * unit);
  if (mode === 'ceil') return round4(Math.ceil(scaled) * unit);
  return round4(Math.round(scaled) * unit);
}

function spanForMessage(message, unit) {
  return message.kind === 'self' ? unit : 0;
}

function getBottomOfRawItem(item, unit) {
  if (item.type === 'frame') return num(item.value.top) + num(item.value.height);
  if (item.type === 'message') return num(item.value.top) + spanForMessage(item.value, unit);
  if (item.type === 'text') return num(item.value.top) + num(item.value.height, unit * 2);
  if (item.type === 'orange') return num(item.value.top) + num(item.value.height, unit);
  if (item.type === 'section') return num(item.value.top) + unit;
  return num(item.value.top);
}

function collectTops(page) {
  const values = [];
  for (const section of page.sections || []) values.push(num(section.top));
  for (const frame of page.frames || []) {
    values.push(num(frame.top));
    values.push(num(frame.top) + num(frame.height));
  }
  for (const sep of page.separators || []) values.push(num(sep.top));
  for (const msg of page.messages || []) {
    values.push(num(msg.top));
    if (msg.kind === 'self') values.push(num(msg.top) + 0.2362);
  }
  for (const text of page.texts || []) {
    values.push(num(text.top));
    values.push(num(text.top) + num(text.height, 0.25));
  }
  for (const pointer of page.orangePointers || []) {
    values.push(num(pointer.top));
    values.push(num(pointer.top) + num(pointer.height, 0.25));
  }
  return values.filter((value) => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
}

function inferUnit(page) {
  const values = collectTops(page);
  const diffs = [];
  for (let i = 1; i < values.length; i++) {
    const diff = round4(values[i] - values[i - 1]);
    if (diff >= 0.18 && diff <= 0.6) diffs.push(diff);
  }
  if (diffs.length === 0) return 0.2362;
  const counts = new Map();
  for (const diff of diffs) counts.set(diff, (counts.get(diff) || 0) + 1);
  const ranked = Array.from(counts.entries()).sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  const direct = ranked.find(([diff]) => diff >= 0.18 && diff <= 0.31);
  if (direct) return Number(direct[0]);
  const doubled = ranked.find(([diff]) => diff > 0.31 && diff <= 0.6);
  if (doubled) return round4(Number(doubled[0]) / 2);
  return 0.2362;
}

function rectOfFrame(frame) {
  return {
    left: num(frame.left),
    right: num(frame.left) + num(frame.width),
    top: num(frame.top),
    bottom: num(frame.top) + num(frame.height),
  };
}

function horizontalOverlapRatio(parentNode, childNode) {
  const parent = rectOfFrame(parentNode.value);
  const child = rectOfFrame(childNode.value);
  const childWidth = Math.max(0.01, child.right - child.left);
  const overlap = Math.min(parent.right, child.right) - Math.max(parent.left, child.left);
  return Math.max(0, overlap) / childWidth;
}

function rectContains(parent, child, tolerance) {
  return (
    child.left >= parent.left - tolerance &&
    child.right <= parent.right + tolerance &&
    child.top >= parent.top - tolerance &&
    child.bottom <= parent.bottom + tolerance
  );
}

function containsTop(frameNode, top, unit, requireInsideBody = false) {
  const start = frameNode.origTop + (requireInsideBody ? unit * 0.5 : -unit * 0.5);
  return top >= start && top <= frameNode.origBottom + unit;
}

function containsFrame(parentNode, childNode, unit) {
  if (parentNode.index === childNode.index) return false;
  const parent = rectOfFrame(parentNode.value);
  const child = rectOfFrame(childNode.value);
  return rectContains(parent, child, unit * 0.35);
}

function smallestFrameContaining(frames, top, unit, predicate = () => true, requireInsideBody = false) {
  let best = null;
  for (const frame of frames) {
    if (!predicate(frame)) continue;
    if (!containsTop(frame, top, unit, requireInsideBody)) continue;
    if (
      !best ||
      frame.origTop > best.origTop + unit * 0.25 ||
      (Math.abs(frame.origTop - best.origTop) <= unit * 0.25 && frame.origArea < best.origArea)
    ) {
      best = frame;
    }
  }
  return best;
}

function horizontalClearance(frame, page, minClearance) {
  const participants = page.participants || [];
  let left = num(frame.left);
  let right = left + num(frame.width);
  const pageWidth = num(page.page && page.page.width, right + 0.5);
  for (const p of participants) {
    const x = num(p.x, NaN);
    if (!Number.isFinite(x)) continue;
    if (Math.abs(left - x) < minClearance) {
      left = x < left ? x + minClearance : x - minClearance;
    }
    if (Math.abs(right - x) < minClearance) {
      right = x < right ? x + minClearance : x - minClearance;
    }
  }
  left = Math.max(0.25, left);
  right = Math.min(pageWidth - 0.25, Math.max(right, left + 0.6));
  frame.left = round4(left);
  frame.width = round4(right - left);
}

function applyChildFragmentInset(node, unit) {
  if (!node.parentFrame) return;
  const frame = node.value;
  const parent = node.parentFrame.value;
  const parentLeft = num(parent.left);
  const parentRight = parentLeft + num(parent.width);
  const frameLeft = num(frame.left);
  const frameRight = frameLeft + num(frame.width);
  const parentWidth = Math.max(0.01, parentRight - parentLeft);
  const frameWidth = Math.max(0.01, frameRight - frameLeft);
  const broadChild = frameWidth / parentWidth >= 0.75;
  const touchesParentEdge = (
    frameLeft <= parentLeft + unit * 0.35 ||
    frameRight >= parentRight - unit * 0.35
  );
  if (!broadChild && !touchesParentEdge) return;

  const insetLeft = parentLeft + unit;
  const insetRight = parentRight - unit;
  if (insetRight <= insetLeft + unit * 3) return;

  const left = Math.max(frameLeft, insetLeft);
  const right = Math.min(frameRight, insetRight);
  if (right <= left + unit * 3) return;
  frame.left = round4(left);
  frame.width = round4(right - left);
}

function applyChildFragmentVerticalGap(node, unit) {
  if (!node.parentFrame) return;
  const frame = node.value;
  const parent = node.parentFrame.value;
  const parentTop = num(parent.top);
  const minimumTop = snap(parentTop + unit * 2, unit, 'ceil');
  if (num(frame.top) < minimumTop) {
    frame.top = round4(minimumTop);
  }
}

function itemSortTop(item) {
  if (item.sortTop !== undefined) return item.sortTop;
  return item.origTop;
}

function itemAnchorTop(item) {
  if (item.type === 'frame') {
    return (item.origTop + item.origBottom) / 2;
  }
  return item.origTop;
}

function makeBlockItem(type, index, value, unit) {
  const top = num(value.top);
  return {
    type,
    index,
    value,
    origTop: top,
    origBottom: getBottomOfRawItem({ type, value }, unit),
    parentFrame: null,
  };
}

function buildModel(page, unit) {
  const frameNodes = (page.frames || []).map((frame, index) => {
    const bounds = rectOfFrame(frame);
    return {
      type: 'frame',
      index,
      value: frame,
      origTop: bounds.top,
      origBottom: bounds.bottom,
      origArea: Math.max(0.01, (bounds.right - bounds.left) * (bounds.bottom - bounds.top)),
      parentFrame: null,
      children: [],
      separators: [],
      orangePointers: [],
    };
  });

  for (const child of frameNodes) {
    let best = null;
    for (const parent of frameNodes) {
      if (!containsFrame(parent, child, unit)) continue;
      if (!best || parent.origArea < best.origArea) best = parent;
    }
    child.parentFrame = best;
    if (best) best.children.push(child);
  }

  const messageItems = (page.messages || []).map((message, index) => makeBlockItem('message', index, message, unit));
  for (const item of messageItems) {
    const refParent = smallestFrameContaining(
      frameNodes,
      item.origTop,
      unit,
      (frame) => {
        if (frame.value.kind !== 'ref') return false;
        if (item.value.kind !== 'self') return false;
        if (!/Common(Func|Util)\//.test(String(item.value.text || ''))) return false;
        return item.origTop >= frame.origTop - unit * 0.25 && item.origTop <= frame.origBottom + unit * 0.25;
      }
    );
    const parent = refParent || smallestFrameContaining(
      frameNodes,
      item.origTop,
      unit,
      (frame) => frame.value.kind !== 'ref' && !(frame.value.kind === 'alt' && item.origTop <= frame.origTop + unit * 0.5),
      true
    );
    item.parentFrame = parent;
    if (parent) parent.children.push(item);
  }

  const textItems = (page.texts || []).map((text, index) => makeBlockItem('text', index, text, unit));
  for (const item of textItems) {
    const parent = smallestFrameContaining(frameNodes, item.origTop, unit, (frame) => frame.value.kind !== 'ref', true);
    item.parentFrame = parent;
    if (parent) parent.children.push(item);
  }

  const sectionItems = (page.sections || []).map((section, index) => makeBlockItem('section', index, section, unit));
  for (const item of sectionItems) {
    const owningFrame = smallestFrameContaining(
      frameNodes,
      item.origTop,
      unit,
      (frame) => frame.value.kind !== 'ref' && item.origTop < frame.origBottom - unit * 0.5
    );
    if (owningFrame) item.sortTop = owningFrame.origTop - unit * 0.25;
  }

  const orangeItems = (page.orangePointers || []).map((pointer, index) => makeBlockItem('orange', index, pointer, unit));
  for (const item of orangeItems) {
    const parent = smallestFrameContaining(frameNodes, item.origTop, unit, (frame) => frame.value.kind === 'ref');
    item.parentFrame = parent;
    if (parent) parent.orangePointers.push(item);
  }

  const separatorItems = (page.separators || []).map((sep, index) => makeBlockItem('separator', index, sep, unit));
  for (const item of separatorItems) {
    const parent = smallestFrameContaining(
      frameNodes,
      item.origTop,
      unit,
      (frame) => frame.value.kind === 'alt' || frame.value.kind === 'opt'
    );
    item.parentFrame = parent;
    if (parent) parent.separators.push(item);
  }

  const topLevel = [];
  for (const frame of frameNodes) {
    if (!frame.parentFrame) topLevel.push(frame);
  }
  for (const item of messageItems) {
    if (!item.parentFrame) {
      const boundaryFrame = frameNodes.find((frame) => (
        frame.value.kind === 'alt' &&
        Math.abs(item.origTop - frame.origTop) <= unit * 0.5
      ));
      if (boundaryFrame) item.sortTop = boundaryFrame.origTop - unit * 0.25;
      topLevel.push(item);
    }
  }
  for (const item of textItems) {
    if (!item.parentFrame) topLevel.push(item);
  }
  for (const item of sectionItems) topLevel.push(item);

  return {
    frames: frameNodes,
    topLevel,
  };
}

function placeMessage(item, cursor, unit) {
  const message = item.value;
  const top = snap(cursor, unit, 'ceil');
  message.top = top;
  const height = spanForMessage(message, unit);
  return {
    top,
    bottom: top + height,
    nextCursor: top + height + (message.kind === 'self' ? unit * 3 : unit * 2),
  };
}

function placeText(item, cursor, unit) {
  const text = item.value;
  const height = Math.max(num(text.height, unit * 2), unit * 1.5);
  const top = snap(cursor, unit, 'ceil');
  text.top = top;
  text.height = round4(height);
  return {
    top,
    bottom: top + height,
    nextCursor: top + height + unit,
  };
}

function placeSection(item, cursor, unit) {
  const section = item.value;
  const top = snap(cursor, unit, 'ceil');
  section.top = top;
  return {
    top: top - unit,
    bottom: top + unit,
    nextCursor: top + unit * 3,
  };
}

function placeOrangeInRef(item, frame, unit) {
  const pointer = item.value;
  const frameLeft = num(frame.left);
  const frameWidth = num(frame.width);
  pointer.left = round4(frameLeft + unit);
  pointer.width = round4(Math.max(unit * 4, frameWidth - unit * 2));
  pointer.height = round4(unit);
  pointer.top = round4(num(frame.top) + unit * 4);
}

function placeFrame(node, cursor, page, unit) {
  const frame = node.value;
  horizontalClearance(frame, page, Math.max(0.35, unit * 1.5));
  applyChildFragmentInset(node, unit);
  frame.top = snap(cursor, unit, 'ceil');
  applyChildFragmentVerticalGap(node, unit);

  if (frame.kind === 'ref') {
    frame.height = round4(unit * 6);
    for (const child of node.children) {
      if (child.type !== 'message') continue;
      child.value.layoutRole = 'ref-self';
      child.value.top = round4(frame.top + unit * 2);
      child.value.width = child.value.width || round4(unit * 2.6);
    }
    for (const pointer of node.orangePointers) placeOrangeInRef(pointer, frame, unit);
    return {
      top: frame.top,
      bottom: frame.top + frame.height,
      nextCursor: frame.top + frame.height + unit * 2,
    };
  }

  frame.layoutPlanned = true;
  if (frame.kind === 'alt' || frame.kind === 'opt') {
    return placeAltFrame(node, page, unit);
  }
  return placeLinearFrame(node, page, unit);
}

function directRenderableChildren(node) {
  return node.children
    .filter((child) => child.type !== 'separator')
    .sort((a, b) => itemSortTop(a) - itemSortTop(b) || a.index - b.index);
}

function placeLinearItems(items, cursor, page, unit) {
  let current = cursor;
  let firstTop = null;
  let lastBottom = cursor;
  for (const item of items) {
    let placed;
    if (item.type === 'frame') {
      placed = placeFrame(item, current, page, unit);
    } else if (item.type === 'message') {
      delete item.value.layoutRole;
      placed = placeMessage(item, current, unit);
    } else if (item.type === 'text') {
      placed = placeText(item, current, unit);
    } else if (item.type === 'section') {
      placed = placeSection(item, current, unit);
    } else {
      continue;
    }
    if (firstTop === null) firstTop = placed.top;
    lastBottom = Math.max(lastBottom, placed.bottom);
    current = Math.max(current, placed.nextCursor);
  }
  return { firstTop, lastBottom, nextCursor: current };
}

function placeLinearFrame(node, page, unit) {
  const frame = node.value;
  const contentStart = frame.top + unit * 3;
  const items = directRenderableChildren(node);
  const laidOut = placeLinearItems(items, contentStart, page, unit);
  const bottom = Math.max(frame.top + unit * 4, laidOut.nextCursor + unit * 2);
  frame.height = round4(snap(bottom, unit, 'ceil') - frame.top);
  return {
    top: frame.top,
    bottom: frame.top + frame.height,
    nextCursor: frame.top + frame.height + unit * 2,
  };
}

function placeAltFrame(node, page, unit) {
  const frame = node.value;
  const separators = node.separators.sort((a, b) => a.origTop - b.origTop || a.index - b.index);
  const children = directRenderableChildren(node);
  const branches = [];
  const boundaryTops = [node.origTop, ...separators.map((sep) => sep.origTop), node.origBottom + unit * 2];
  for (let i = 0; i <= separators.length; i++) {
    branches.push({
      separatorBefore: i === 0 ? null : separators[i - 1],
      separatorAfter: i < separators.length ? separators[i] : null,
      items: [],
      startOrig: boundaryTops[i],
      endOrig: boundaryTops[i + 1],
    });
  }

  for (const child of children) {
    const anchor = itemAnchorTop(child);
    let branchIndex = 0;
    for (let i = 0; i < separators.length; i++) {
      if (anchor >= separators[i].origTop - unit * 0.5) branchIndex = i + 1;
    }
    branches[Math.min(branchIndex, branches.length - 1)].items.push(child);
  }

  let boundary = frame.top;
  let finalBottom = frame.top + unit * 4;
  for (let i = 0; i < branches.length; i++) {
    const branch = branches[i];
    const contentStart = boundary + unit * 4;
    const laidOut = placeLinearItems(
      branch.items.sort((a, b) => itemSortTop(a) - itemSortTop(b) || a.index - b.index),
      contentStart,
      page,
      unit
    );
    const branchLastBottom = Math.max(contentStart, laidOut.lastBottom);
    if (branch.separatorAfter) {
      const sepTop = snap(Math.max(branchLastBottom + unit * 3, laidOut.nextCursor + unit * 2), unit, 'ceil');
      const sep = branch.separatorAfter.value;
      sep.top = sepTop;
      sep.left = num(frame.left);
      sep.right = round4(num(frame.left) + num(frame.width));
      boundary = sepTop;
      finalBottom = Math.max(finalBottom, sepTop);
    } else {
      finalBottom = Math.max(finalBottom, Math.max(branchLastBottom + unit * 3, laidOut.nextCursor + unit * 2));
    }
  }

  frame.height = round4(snap(finalBottom, unit, 'ceil') - frame.top);
  for (const sepItem of separators) {
    sepItem.value.left = num(frame.left);
    sepItem.value.right = round4(num(frame.left) + num(frame.width));
  }
  return {
    top: frame.top,
    bottom: frame.top + frame.height,
    nextCursor: frame.top + frame.height + unit * 2,
  };
}

function normalizePage(page) {
  const unit = inferUnit(page);
  const model = buildModel(page, unit);
  const startTop = snap(Math.max(2.8, num(page.page && page.page.title && page.page.title.top, 0) + 2.2), unit, 'ceil');
  const topItems = model.topLevel.sort((a, b) => itemSortTop(a) - itemSortTop(b) || a.type.localeCompare(b.type) || a.index - b.index);
  const laidOut = placeLinearItems(topItems, startTop, page, unit);
  expandShortBusinessGroups(page, unit);
  const expandedFrameBottom = Math.max(
    0,
    ...(page.frames || []).map((frame) => num(frame.top) + num(frame.height))
  );
  const finalCursor = Math.max(laidOut.nextCursor, laidOut.lastBottom + unit * 3, expandedFrameBottom + unit * 3);
  const finalHeight = snap(finalCursor + unit * 3, unit, 'ceil');
  if (page.page) page.page.height = round4(finalHeight);
  for (const participant of page.participants || []) {
    const top = num(participant.top, 1.55);
    participant.height = round4(Math.max(unit * 12, finalHeight - top - unit * 3));
  }
  return {
    name: page.page && page.page.name,
    unit,
    height: page.page && page.page.height,
    frames: (page.frames || []).length,
    messages: (page.messages || []).length,
  };
}

function normalizeSpec(spec, inputPath) {
  const output = clone(spec);
  normalizeCommonSvgReferenceTexts(output, buildCommonSvgDisplayCatalog(inputPath));
  const pages = Array.isArray(output.pages) ? output.pages : [output];
  const reports = [];
  for (const page of pages) {
    reports.push(normalizePage(page));
  }
  output.nativeLayoutPlanner = {
    version: 'skeleton-first-v5',
    unit: 'participant-connection-point',
    policy: 'skeleton-fragments-ref-atomic-messages-last-title-autowidth-iris-alt-inside-query-group-child-inset-section-gap-common-ref-display-reference-prefix',
  };
  return { spec: output, reports };
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.input) {
    throw new Error('Missing --input <native_visio_spec.json>');
  }
  const input = path.resolve(args.input);
  const output = args.output ? path.resolve(args.output) : input;
  const raw = fs.readFileSync(input, 'utf8');
  const parsed = JSON.parse(raw);
  if (!args.force && parsed.nativeLayoutPlanner && ['skeleton-first-v1', 'skeleton-first-v2', 'skeleton-first-v3', 'skeleton-first-v4', 'skeleton-first-v5'].includes(parsed.nativeLayoutPlanner.version)) {
    const planned = clone(parsed);
    normalizeCommonSvgReferenceTexts(planned, buildCommonSvgDisplayCatalog(input));
    fs.writeFileSync(output, JSON.stringify(planned, null, 2) + '\n', 'utf8');
    process.stdout.write(JSON.stringify({ output, skipped: true, reason: 'already layout planned' }, null, 2) + '\n');
    return;
  }
  const result = normalizeSpec(parsed, input);
  fs.writeFileSync(output, JSON.stringify(result.spec, null, 2) + '\n', 'utf8');
  process.stdout.write(JSON.stringify({ output, pages: result.reports }, null, 2) + '\n');
}

try {
  main();
} catch (error) {
  process.stderr.write((error && error.stack) ? error.stack : String(error));
  process.stderr.write('\n');
  process.exit(1);
}
