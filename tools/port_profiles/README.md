# Port profiles

A port profile is the small declarative boundary between the generic N64
porting tools and one decomp/recomp project.

The stable audit entry point is:

```sh
python3 tools/n64_port_audit.py --profile tools/port_profiles/goldeneye.json
```

## Schema v1

Required:

- `schema_version`: currently `1`.
- `project`: short project identifier.
- `source_roots`: directories scanned by generic semantic rules.

Optional:

- `exclude_path_parts`: path components excluded from scanning.
- `targets`: target profiles. Each target may describe `id`, `arch`,
  `pointer_bits`, and graphics backend.
- `binary_adapters`: project-specific converter entry points.
- `verification`: build/test workflow entry points.

Example:

```json
{
  "schema_version": 1,
  "project": "example",
  "source_roots": ["src", "include", "port"],
  "exclude_path_parts": ["third_party"],
  "targets": [
    {
      "id": "handheld-aarch64-gles",
      "arch": "aarch64",
      "pointer_bits": 64,
      "graphics": "gles3"
    }
  ]
}
```

Profiles must contain paths relative to the repository root. Project-specific
binary-format knowledge should live in adapters/plugins; generic source
semantics should remain in the shared audit engine.
