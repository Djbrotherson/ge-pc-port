## Summary

What changed and what problem does it solve?

## Semantic class

For portability/runtime changes, classify the change:

- [ ] native host pointer / LP64
- [ ] N64 address/token semantics
- [ ] serialized/binary layout
- [ ] endian conversion
- [ ] graphics/GLES
- [ ] audio/input/platform runtime
- [ ] Portkit/tooling
- [ ] documentation/CI/maintenance
- [ ] other

## Scope

- [ ] The whole relevant failure class was searched, not only one crash site.
- [ ] Project-specific knowledge remains outside generic Portkit code where practical.
- [ ] Existing source/license notices were preserved.
- [ ] No ROM or extracted proprietary game assets are included.

## Invariant

What prevents this class from regressing?

- [ ] semantic-audit rule
- [ ] compile-time assertion
- [ ] ABI/profile contract
- [ ] unit/selftest
- [ ] converter/runtime cross-check
- [ ] lifecycle invariant
- [ ] not applicable; explain below

## Verification

Run the cheapest applicable tiers first:

- [ ] `python3 tools/n64_port.py doctor`
- [ ] `python3 tools/n64_port.py selftest`
- [ ] `python3 tools/n64_port.py audit`
- [ ] host-specific regression test
- [ ] AArch64 proof build
- [ ] R36S real-device test

## Notes

Risks, unresolved questions, or follow-up work.
