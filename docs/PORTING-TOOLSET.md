# Porting Toolset

The canonical reusable architecture lives in:

- [../portkit/README.md](../portkit/README.md)
- [../portkit/ARCHITECTURE.md](../portkit/ARCHITECTURE.md)

Repository-specific integration and CI remain under `tools/`.

GoldenEye-specific converters and verification utilities remain under
`tools_pc/`.

## Development rules

1. classify the semantic class before patching an instance,
2. batch the whole class where practical,
3. pair runtime fixes with reusable invariants,
4. spend cheap proof before target builds,
5. keep project-specific knowledge out of generic Portkit code,
6. keep the working tree focused on living tools and current documentation.

## Validation order

```
profile/target validation
→ Portkit/selftests
→ semantic/ABI audit
→ host verification
→ AArch64 proof
→ R36S device validation
```

## Current integration

The repository CI wrapper remains:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
```

The reusable product entry point is:

```sh
python3 portkit/portkit.py analyze ...
python3 portkit/portkit.py scaffold ...
```
