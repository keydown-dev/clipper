#!/usr/bin/env node
import { cpSync, existsSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const packageRoot = resolve(scriptDir, '..');
const repoRoot = resolve(packageRoot, '..', '..');
const source = resolve(repoRoot, 'skills', 'clipper');
const destination = resolve(packageRoot, 'skills', 'clipper');

if (!existsSync(resolve(source, 'SKILL.md'))) {
  console.error(`Cannot sync Clipper skill: missing ${resolve(source, 'SKILL.md')}`);
  process.exit(1);
}

rmSync(destination, { recursive: true, force: true });
cpSync(source, destination, { recursive: true });
console.log(`Synced ${source} -> ${destination}`);
