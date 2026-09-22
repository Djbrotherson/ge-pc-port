# Port profiles

A port profile is the small declarative boundary between the generic N64
porting tools and one decomp/recomp project.

The stable tool entry point is:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py audit
python3 tools/n64_port.py show-profile

# Another project/profile:
python3 tools/n64_port.py --profile path/to/project.json audit
```

`tools/n64_port_audit.py` remains the lower-level semantic-audit entry point.

## Schema v1

Required:

- `schema_version`: currently `1`.
- `project`: short project identifier.
- `source_roots`: directories scanned by generic semantic rules.

Optional:

- `exclude_path_parts`: path components excluded from scanning.
- `targets`: target profiles. Each target may describe `id`, `arch`,
  `pointer_bits`, and graphics backend.
- `contract_suite`: project-specific contract checks; empty means generic
  semantic rules only.
- `abi_contract`: machine-readable ABI/layout manifest.
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
