# AEGIS release tools

These standard-library tools build and inspect deterministic, offline AEGIS
and WAEGIS ZIP archives from explicit local inputs.

```powershell
aegis-build-archive --repository C:\src\aegis --output C:\out --product aegis --platform windows-x86_64 --runtime-lock runtime_inputs.toml
aegis-inspect-archive C:\out\aegis-1.0.0-windows-x86_64-external-runtime.zip
```

Add `--with-dependencies` only after the selected platform's Python and Git
entries in `runtime_inputs.toml` contain real archive paths, versions, and
SHA-256 digests. The builder performs no download and refuses missing,
incomplete, mismatched, unsafe, or non-Python-3.12 bundled input.
