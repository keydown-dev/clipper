# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

## Commands

```bash
cd packages/pi-clipper && npm run sync:skill && npm pack --dry-run --json > /tmp/pi-clipper-pack.json
node -e "const fs=require('fs'); const p=require('./package.json'); if(!p.keywords.includes('pi-package')) throw new Error('missing pi-package keyword'); if(!p.pi?.skills?.includes('./skills')) throw new Error('missing pi skills manifest'); if(!p.clipper?.requiresCli || !p.clipper?.installSeparately) throw new Error('missing separate Clipper Core metadata'); const pack=fs.readFileSync('/tmp/pi-clipper-pack.json','utf8'); for (const required of ['skills/clipper/SKILL.md','skills/clipper/references/install.md']) if(!pack.includes(required)) throw new Error('pack missing '+required);"
cd ../..
diff -qr skills/clipper packages/pi-clipper/skills/clipper
```

## Results

- `npm run sync:skill` completed and regenerated `packages/pi-clipper/skills/clipper` from root `skills/clipper`.
- `npm pack --dry-run --json` completed and included the packaged skill plus reference docs.
- Package metadata checks passed for `pi-package`, `pi.skills`, and separate Clipper Core install metadata.
- `diff -qr` produced no output, confirming the packaged skill copy matches the root source of truth.
