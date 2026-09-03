# Vendored JavaScript dependencies

The standalone packages require no npm installation. The following modules were bundled into ESM targeting Node.js 22 using esbuild 0.28.2:

- `opencode-tool.mjs`: `@opencode-ai/plugin` 1.3.0 `tool` entry plus Zod 4.1.8.
- `jsonc.mjs`: the `parse` export from `jsonc-parser` 3.3.1 `lib/esm/main.js`.

Use the ESM JSONC entry; bundling its UMD main entry leaves unsupported dynamic relative requires. Runtime code imports these vendored files directly. Regenerate only when deliberately updating a dependency, then run the installer and native host checks. `LICENSES.txt` preserves the upstream licenses. Build tooling is not needed by the recipient.
