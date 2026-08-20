#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

const DEFAULT_APP = "/Applications/ChatGPT.app";
const PLIST_BUDDY = "/usr/libexec/PlistBuddy";
const TARGET_MULTIPLIER = 1;
const DEFAULT_NON_IDLE_PLAYBACK = "if(e===`idle`)return{frames:R,loopStartIndex:0};let r=[...n,...n,...n];return{frames:[...r,...R],loopStartIndex:r.length}";
const LEGACY_RUNNING_PLAYBACK = "if(e===`idle`)return{frames:R,loopStartIndex:0};let r=[...n,...n,...n];return e===`running`?{frames:n,loopStartIndex:0}:{frames:[...r,...R],loopStartIndex:r.length}";
const PERSISTENT_NON_IDLE_PLAYBACK = "if(e===`idle`)return{frames:R,loopStartIndex:0};return{frames:n,loopStartIndex:0}";

function sha256(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

function readAsar(asarPath) {
  const bytes = fs.readFileSync(asarPath);
  if (bytes.length < 16) throw new Error("app.asar is too small");

  const headerPickleSize = bytes.readUInt32LE(4);
  const headerJsonSize = bytes.readUInt32LE(12);
  const headerStart = 16;
  const headerEnd = headerStart + headerJsonSize;
  const dataStart = 8 + headerPickleSize;
  if (headerEnd > bytes.length || dataStart > bytes.length) {
    throw new Error("app.asar header is malformed");
  }

  const headerText = bytes.subarray(headerStart, headerEnd).toString("utf8");
  return {
    bytes,
    dataStart,
    header: JSON.parse(headerText),
    headerEnd,
    headerJsonSize,
    headerStart,
  };
}

function walkFiles(node, prefix = "", files = []) {
  for (const [name, entry] of Object.entries(node.files ?? {})) {
    const filePath = prefix ? `${prefix}/${name}` : name;
    if (entry.files) walkFiles(entry, filePath, files);
    else files.push({ entry, filePath });
  }
  return files;
}

function findRenderer(asar) {
  const candidates = walkFiles(asar.header).filter(({ entry, filePath }) =>
    entry.offset != null &&
    /^webview\/assets\/codex-avatar-[^/]+\.js$/.test(filePath)
  );

  const matches = [];
  for (const candidate of candidates) {
    const { entry, filePath } = candidate;
    const start = asar.dataStart + Number(entry.offset);
    const end = start + Number(entry.size);
    const source = asar.bytes.subarray(start, end).toString("utf8");
    if (
      source.includes("frameDurationMs:280") &&
      source.includes("frameDurationMs:320") &&
      source.includes("e.frameDurationMs*")
    ) {
      matches.push({ ...candidate, end, source, start });
    }
  }

  if (matches.length !== 1) {
    throw new Error(`Expected one Codex avatar renderer, found ${matches.length}`);
  }
  return matches[0];
}

function inspectRenderer(source) {
  const declaration = source.match(
    /([A-Za-z_$][\w$]*)=(\d+),([A-Za-z_$][\w$]*)=\[\{rowIndex:0,columnIndex:0,frameDurationMs:280\}/,
  );
  if (!declaration) throw new Error("Idle cadence declaration was not found");

  const multiplierVariable = declaration[1];
  const multiplier = Number(declaration[2]);
  const idleFramesVariable = declaration[3];
  const multiplierUse = `frameDurationMs:e.frameDurationMs*${multiplierVariable}`;
  if (!source.includes(multiplierUse)) {
    throw new Error("Idle cadence multiplier use was not found");
  }

  return {
    declaration,
    idleFramesVariable,
    multiplier,
    multiplierVariable,
  };
}

function readPlistHash(plistPath) {
  return execFileSync(
    PLIST_BUDDY,
    ["-c", "Print :ElectronAsarIntegrity:Resources/app.asar:hash", plistPath],
    { encoding: "utf8" },
  ).trim();
}

function verify(appPath) {
  const asarPath = path.join(appPath, "Contents", "Resources", "app.asar");
  const plistPath = path.join(appPath, "Contents", "Info.plist");
  const asar = readAsar(asarPath);
  const renderer = findRenderer(asar);
  const cadence = inspectRenderer(renderer.source);
  const assetBytes = asar.bytes.subarray(renderer.start, renderer.end);
  const actualAssetHash = sha256(assetBytes);
  const actualHeaderHash = sha256(
    asar.bytes.subarray(asar.headerStart, asar.headerEnd),
  );
  const plistHeaderHash = readPlistHash(plistPath);
  const declaredAssetHash = renderer.entry.integrity?.hash ?? null;
  const declaredBlocks = renderer.entry.integrity?.blocks ?? [];
  const blockSize = renderer.entry.integrity?.blockSize ?? 4 * 1024 * 1024;
  const actualBlocks = [];
  for (let offset = 0; offset < assetBytes.length; offset += blockSize) {
    actualBlocks.push(sha256(assetBytes.subarray(offset, offset + blockSize)));
  }

  return {
    appPath,
    assetHashMatches: declaredAssetHash === actualAssetHash,
    blockHashesMatch: JSON.stringify(declaredBlocks) === JSON.stringify(actualBlocks),
    headerHashMatches: plistHeaderHash === actualHeaderHash,
    idleLoopDurationMs: 1100 * cadence.multiplier,
    multiplier: cadence.multiplier,
    nonIdleStatesPersistent: renderer.source.includes(PERSISTENT_NON_IDLE_PLAYBACK),
    renderer: renderer.filePath,
    runningPersistent:
      renderer.source.includes(PERSISTENT_NON_IDLE_PLAYBACK) ||
      renderer.source.includes(LEGACY_RUNNING_PLAYBACK),
  };
}

function patchRenderer(renderer, targetMultiplier) {
  const cadence = inspectRenderer(renderer.source);
  let patched = renderer.source;

  if (cadence.multiplier !== targetMultiplier) {
    if (String(cadence.multiplier).length !== String(targetMultiplier).length) {
      throw new Error("Multiplier replacement must preserve the digit width");
    }
    const matchedText = cadence.declaration[0];
    const replacement = matchedText.replace(
      `${cadence.multiplierVariable}=${cadence.multiplier},`,
      `${cadence.multiplierVariable}=${targetMultiplier},`,
    );
    patched = patched.replace(matchedText, replacement);
  }

  if (!patched.includes(PERSISTENT_NON_IDLE_PLAYBACK)) {
    const playbackBranch = patched.includes(LEGACY_RUNNING_PLAYBACK)
      ? LEGACY_RUNNING_PLAYBACK
      : patched.includes(DEFAULT_NON_IDLE_PLAYBACK)
        ? DEFAULT_NON_IDLE_PLAYBACK
        : null;
    if (playbackBranch == null) {
      throw new Error("Non-idle playback branch was not found");
    }
    patched = patched.replace(playbackBranch, PERSISTENT_NON_IDLE_PLAYBACK);
  }

  if (patched.length > renderer.source.length) {
    const mapComment = patched.match(/\n\/\/# sourceMappingURL=codex-avatar-[^\n]+\.js\.map\s*$/)?.[0];
    if (!mapComment) throw new Error("Source map comment is unavailable for size-neutral patching");
    patched = patched.slice(0, -mapComment.length);
  }
  if (patched.length > renderer.source.length) {
    throw new Error("Renderer patch cannot fit without changing the ASAR file size");
  }
  return patched.padEnd(renderer.source.length, " ");
}

function selfTest() {
  const buildSource = (playbackBranch) =>
    `var I=6,L=[{rowIndex:0,columnIndex:0,frameDurationMs:280}],R=L.map(e=>({...e,frameDurationMs:e.frameDurationMs*I}));function A(e,t){let n=z[e];if(t)return{frames:[n[0]],loopStartIndex:null};${playbackBranch}}\n//# sourceMappingURL=codex-avatar-test.js.map`;
  const cases = [DEFAULT_NON_IDLE_PLAYBACK, LEGACY_RUNNING_PLAYBACK];
  for (const playbackBranch of cases) {
    const source = buildSource(playbackBranch);
    const patched = patchRenderer({ source }, TARGET_MULTIPLIER);
    const cadence = inspectRenderer(patched);
    if (
      patched.length !== source.length ||
      cadence.multiplier !== TARGET_MULTIPLIER ||
      !patched.includes(PERSISTENT_NON_IDLE_PLAYBACK)
    ) {
      throw new Error("Playback patch self-test failed");
    }
  }
  return {
    ok: true,
    cases: cases.length,
    multiplier: TARGET_MULTIPLIER,
    nonIdleStatesPersistent: true,
  };
}

function makeBackup(appPath, requestedBackupRoot) {
  const plistPath = path.join(appPath, "Contents", "Info.plist");
  const asarPath = path.join(appPath, "Contents", "Resources", "app.asar");
  const version = execFileSync(
    PLIST_BUDDY,
    ["-c", "Print :CFBundleShortVersionString", plistPath],
    { encoding: "utf8" },
  ).trim();
  const build = execFileSync(
    PLIST_BUDDY,
    ["-c", "Print :CFBundleVersion", plistPath],
    { encoding: "utf8" },
  ).trim();
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const root = requestedBackupRoot ?? path.join(
    os.homedir(),
    ".codex",
    "backups",
    "chatgpt-idle-cadence",
  );
  const backupDir = path.join(root, `${version}-${build}-${stamp}`);
  fs.mkdirSync(backupDir, { recursive: true });
  fs.copyFileSync(
    asarPath,
    path.join(backupDir, "app.asar"),
    fs.constants.COPYFILE_FICLONE,
  );
  fs.copyFileSync(plistPath, path.join(backupDir, "Info.plist"));
  fs.writeFileSync(
    path.join(backupDir, "backup.json"),
    JSON.stringify({ appPath, build, createdAt: new Date().toISOString(), version }, null, 2) + "\n",
  );
  return backupDir;
}

function atomicWrite(filePath, bytes) {
  const tempPath = `${filePath}.codex-idle-cadence-${process.pid}.tmp`;
  fs.writeFileSync(tempPath, bytes, { mode: 0o644 });
  fs.renameSync(tempPath, filePath);
}

function apply(appPath, requestedBackupRoot) {
  const before = verify(appPath);
  if (!before.assetHashMatches || !before.blockHashesMatch || !before.headerHashMatches) {
    throw new Error(`Refusing to patch an ASAR that fails integrity checks: ${JSON.stringify(before)}`);
  }
  if (before.multiplier === TARGET_MULTIPLIER && before.nonIdleStatesPersistent) {
    return { alreadyPatched: true, backupDir: null, before, after: before };
  }

  const backupDir = makeBackup(appPath, requestedBackupRoot);
  const asarPath = path.join(appPath, "Contents", "Resources", "app.asar");
  const plistPath = path.join(appPath, "Contents", "Info.plist");
  const asar = readAsar(asarPath);
  const renderer = findRenderer(asar);
  const patchedSource = patchRenderer(renderer, TARGET_MULTIPLIER);
  const patchedAssetBytes = Buffer.from(patchedSource, "utf8");
  patchedAssetBytes.copy(asar.bytes, renderer.start);

  const assetHash = sha256(patchedAssetBytes);
  renderer.entry.integrity.hash = assetHash;
  const blockSize = renderer.entry.integrity.blockSize;
  renderer.entry.integrity.blocks = [];
  for (let offset = 0; offset < patchedAssetBytes.length; offset += blockSize) {
    renderer.entry.integrity.blocks.push(
      sha256(patchedAssetBytes.subarray(offset, offset + blockSize)),
    );
  }

  const newHeaderText = JSON.stringify(asar.header);
  const newHeaderBytes = Buffer.from(newHeaderText, "utf8");
  if (newHeaderBytes.length !== asar.headerJsonSize) {
    throw new Error("ASAR header size changed; refusing non-atomic format rewrite");
  }
  newHeaderBytes.copy(asar.bytes, asar.headerStart);
  const headerHash = sha256(newHeaderBytes);

  atomicWrite(asarPath, asar.bytes);
  execFileSync(
    PLIST_BUDDY,
    ["-c", `Set :ElectronAsarIntegrity:Resources/app.asar:hash ${headerHash}`, plistPath],
  );

  const after = verify(appPath);
  if (
    after.multiplier !== TARGET_MULTIPLIER ||
    !after.nonIdleStatesPersistent ||
    !after.assetHashMatches ||
    !after.blockHashesMatch ||
    !after.headerHashMatches
  ) {
    throw new Error(`Patched app failed verification: ${JSON.stringify(after)}`);
  }
  return { alreadyPatched: false, backupDir, before, after };
}

function restore(appPath, backupDir) {
  const backupAsar = path.join(backupDir, "app.asar");
  const backupPlist = path.join(backupDir, "Info.plist");
  if (!fs.existsSync(backupAsar) || !fs.existsSync(backupPlist)) {
    throw new Error("Backup is missing app.asar or Info.plist");
  }
  atomicWrite(
    path.join(appPath, "Contents", "Resources", "app.asar"),
    fs.readFileSync(backupAsar),
  );
  fs.copyFileSync(backupPlist, path.join(appPath, "Contents", "Info.plist"));
  return verify(appPath);
}

function parseArgs(argv) {
  const [mode = "--check", first, ...rest] = argv;
  if (mode === "--self-test") return { mode };
  const appPath = first && !first.startsWith("--") ? first : DEFAULT_APP;
  const backupRootIndex = rest.indexOf("--backup-root");
  const backupRoot = backupRootIndex >= 0 ? rest[backupRootIndex + 1] : null;
  if (mode === "--restore") {
    const backupDir = rest.find((value, index) => rest[index - 1] === "--backup");
    if (!backupDir) throw new Error("--restore requires --backup <directory>");
    return { appPath, backupDir, mode };
  }
  if (!["--check", "--apply"].includes(mode)) {
    throw new Error("Usage: patch_codex_idle_cadence.mjs --self-test | --check|--apply [app] [--backup-root dir] | --restore [app] --backup dir");
  }
  return { appPath, backupRoot, mode };
}

try {
  const args = parseArgs(process.argv.slice(2));
  const result = args.mode === "--self-test"
    ? selfTest()
    : args.mode === "--apply"
    ? apply(args.appPath, args.backupRoot)
    : args.mode === "--restore"
      ? restore(args.appPath, args.backupDir)
      : verify(args.appPath);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.stack : String(error)}\n`);
  process.exitCode = 1;
}
