#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

ROOTS=("src","include","port")
EXTS={".c",".h",".cc",".cpp",".cxx",".hpp"}
DESKTOP_GL={
 "glPolygonMode","glDrawBuffer","glGetTexImage","glTexImage1D","glTexSubImage1D",
 "glCopyTexImage1D","glCopyTexSubImage1D","glCompressedTexImage1D","glClearDepth",
 "glDepthRange","glGetDoublev","glPixelStoref"
}

findings=[]

def add(sev,kind,path,line,code,why):
    findings.append((sev,kind,str(path),line,code.strip()[:300],why))

def iter_files():
    for root in ROOTS:
        p=Path(root)
        if not p.exists(): continue
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in EXTS and "third_party" not in f.parts:
                yield f

def _strip_comments(line:str, in_block:bool):
    out=[]
    i=0
    while i < len(line):
        if in_block:
            j=line.find("*/", i)
            if j < 0:
                return "", True
            i=j+2
            in_block=False
            continue
        j=line.find("/*", i)
        k=line.find("//", i)
        if k >= 0 and (j < 0 or k < j):
            out.append(line[i:k])
            return "".join(out), False
        if j < 0:
            out.append(line[i:])
            return "".join(out), False
        out.append(line[i:j])
        i=j+2
        in_block=True
    return "".join(out), in_block

def scan_file(path:Path):
    raw_lines=path.read_text(errors="replace").splitlines()
    pp=[]
    in_block_comment=False

    # Deliberately conservative: direct pointer narrowing is fatal. An
    # explicit uintptr_t/intptr_t boundary is already a reviewed host/token
    # conversion and remains visible as P1 for manual semantic review.
    direct_ptr_name = re.compile(
        r"\((?:s32|u32|int|unsigned\s+int)\)\s*"
        r"([A-Za-z_]\w*(?:ptr|Ptr|pointer|Pointer|addr|Addr|address|Address))"
        r"(?!\s*(?:->|\.|\(|\[))"
    )
    member_ptr_name = re.compile(
        r"\((?:s32|u32|int|unsigned\s+int)\)\s*"
        r"[^;\n]+->\s*([A-Za-z_]\w*(?:ptr|Ptr|pointer|Pointer|addr|Addr|address|Address))\b"
    )
    explicit_width_boundary = re.compile(
        r"\((?:s32|u32|int|unsigned\s+int)\)\s*"
        r"(?:\(\s*u32\s*\)\s*)?\(\s*(?:u?intptr_t)\s*\)"
    )

    for i,raw in enumerate(raw_lines,1):
        line,in_block_comment=_strip_comments(raw,in_block_comment)
        s=line.strip()
        if not s:
            continue

        # Track enough preprocessing state to identify PORT / USE_GLES
        # branches, including the #if defined(X) spelling used by this repo.
        if s.startswith("#ifdef PORT") or re.match(r"#\s*if\s+defined\s*\(\s*PORT\s*\)", s):
            pp.append(("PORT",True))
        elif s.startswith("#ifndef PORT") or re.match(r"#\s*if\s+!\s*defined\s*\(\s*PORT\s*\)", s):
            pp.append(("PORT",False))
        elif s.startswith("#ifdef USE_GLES") or re.match(r"#\s*if\s+defined\s*\(\s*USE_GLES\s*\)", s):
            pp.append(("USE_GLES",True))
        elif s.startswith("#ifndef USE_GLES") or re.match(r"#\s*if\s+!\s*defined\s*\(\s*USE_GLES\s*\)", s):
            pp.append(("USE_GLES",False))
        elif s.startswith("#if") and "__x86_64__" in s and "__aarch64__" not in s:
            # Architecture dispatch is not a missing AArch64 LP64 fix:
            # platform.h intentionally distinguishes x86-64 from ARM, and
            # x86/i386 branches select x86-only intrinsics such as _mm_pause.
            arch_dispatch = (
                path.as_posix() == "port/include/platform.h"
                or "__i386__" in s or "_M_IX86" in s
            )
            if not arch_dispatch:
                add("P0","x86-only-64bit-guard",path,i,raw,
                    "64-bit host fix is enabled on x86_64 but not AArch64.")
            pp.append(("OTHER",None))
        elif s.startswith("#if"):
            pp.append(("OTHER",None))
        elif s.startswith("#else") and pp:
            k,v=pp[-1]
            if k in ("PORT","USE_GLES"):
                pp[-1]=(k,not v)
        elif s.startswith("#endif") and pp:
            pp.pop()

        port_state=next((v for k,v in reversed(pp) if k=="PORT"),None)
        in_port = port_state is True
        host_active = port_state is not False

        # Exact semantic regression class: synthetic animation symbols are
        # offsets. Comments have already been stripped above.
        if re.search(r"\(uintptr_t\)\s*&ANIM_DATA_", line) or re.search(r"\+\s*&ANIM_DATA_",line):
            add("P0","animation-token-as-host-pointer",path,i,raw,
                "ANIM_DATA_* is a synthetic N64 offset token on 64-bit hosts; use PTR_ANIM_* / low-32 offset semantics.")

        if host_active and re.search(r"\((?:s32|u32|int|unsigned\s+int)\)\s*&ANIM_DATA_", line):
            add("P0","animation-offset-legacy-cast",path,i,raw,
                "ANIM_DATA_* is an N64 animation offset token; use the generated PTR_ANIM_* constant on the host path.")

        # Explicit pointer-width integer conversion is a semantic boundary,
        # not proof of truncation. Keep it in the report as P1 so it remains
        # auditable, but reserve P0 for unreviewed direct narrowing.
        if host_active and explicit_width_boundary.search(line):
            add("P1","explicit-32bit-token-boundary",path,i,raw,
                "Explicit uintptr_t/intptr_t to 32-bit conversion; verify this is an intentional N64 token/serialized ABI boundary.")

        # Address-of narrowed directly without a pointer-width boundary.
        if host_active and re.search(r"\((?:s32|u32|int|unsigned\s+int)\)\s*&\s*[A-Za-z_]", line):
            if not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|PTR_ANIM|CART_BASE)", line):
                add("P0","host-address-narrowing",path,i,raw,
                    "Native address is explicitly narrowed to 32 bits without a pointer-width/token boundary.")

        # Direct pointer-looking variables/fields narrowed without uintptr_t.
        if host_active and "uintptr_t" not in line and "intptr_t" not in line:
            if direct_ptr_name.search(line) or member_ptr_name.search(line):
                # Known non-pointer/token false positives:
                # - audi.c DMABuffer.startAddr is an N64/sample address token (s32), not a host pointer.
                # - gunfire.c MagSize is a scalar field reached through a pointer expression.
                known_token_or_scalar = (
                    (path.as_posix() == "src/audi.c" and "dmaPtr->startAddr" in line)
                    or (path.as_posix() == "src/game/gunfire.c" and "MagSize" in line)
                )
                if not known_token_or_scalar and not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|PTR_ANIM|CART_BASE|SegmentRom)",line):
                    add("P0","host-pointer-variable-narrowing",path,i,raw,
                        "Pointer-looking value is directly narrowed to 32 bits; classify as native pointer vs N64 token.")

        # Host pointer plus linker/ROM token is suspicious unless explicitly
        # narrowed/tokenized.
        if re.search(r"\b(?:ptr|pointer|base|buf|buffer|data|addr|address)\w*\s*\+\s*\(uintptr_t\)\s*&\w*(?:SegmentRom|SegmentStart|SegmentEnd)", line, re.I):
            add("P0","linker-token-host-add",path,i,raw,
                "Linker/ROM symbols are address tokens; full-width host addition changes N64 semantics.")

        # PORT direct narrowing: exclude explicit uintptr_t review boundaries,
        # scalar GBI command words, and well-defined physical/token helpers.
        if in_port and "uintptr_t" not in line and "intptr_t" not in line:
            if re.search(r"\((?:s32|u32|int|unsigned\s+int)\)\s*&\w+", line) or direct_ptr_name.search(line) or member_ptr_name.search(line):
                if not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|SegmentRom|PTR_ANIM|CART_BASE|\.words\.w[01])",line):
                    add("P0","port-pointer-narrowing",path,i,raw,
                        "PORT path directly narrows a host pointer without an explicit N64/token conversion boundary.")

        # Pointer alignment/math after direct 32-bit narrowing. Require an
        # address-of or pointer-looking operand; ordinary scalar/GBI math is
        # not an address hazard.
        if in_port and re.search(r"(?:\((?:s32|u32)\)\s*&\w+|\((?:s32|u32)\)\s*[A-Za-z_]\w*(?:ptr|Ptr|pointer|Pointer|addr|Addr|address|Address))[^;]+(?:\+|\-|&|\|)",line):
            if not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|SegmentRom|PTR_ANIM|CART_BASE|\.words\.w[01])",line):
                add("P0","port-32bit-address-math",path,i,raw,
                    "PORT path performs address arithmetic after direct 32-bit pointer narrowing.")

        # Bitmask/comparison precedence is a real host/runtime hazard.
        # Expressions such as `flags & MASK > 0` parse as
        # `flags & (MASK > 0)`, while `avail & MASK == 0` can become a
        # constant-zero mask. Require the intended mask operation explicitly.
        if re.search(
            r"\b(?:if|while)\s*\([^\n;]*(?:(?<!&)\&(?!&)|(?<!\|)\|(?!\|))"
            r"\s*[A-Za-z_]\w*\s*(?:==|!=|>|<)",
            line,
        ):
            add("P0","bitmask-comparison-precedence",path,i,raw,
                "Bitmask is compared without grouping; use (flags & MASK) comparison semantics.")

        # A logical-not is 0/1 before a following bitwise AND. This exact
        # pattern caused controller-state checks to fail for controller bits
        # above bit 0.
        if re.search(r"!\s*\([^\n;]+\)\s*&", line):
            add("P0","logical-not-bitmask",path,i,raw,
                "Logical-not result is bitwise-ANDed; likely intended !(flags & MASK).")

        # GoldenEye's Indy transport carries 32-bit wire tokens. On LP64 a
        # response must never be written through a host pointer object: that
        # overwrites only half of an 8-byte pointer and leaves garbage high
        # bits. Keep this exact regression class visible.
        if path.as_posix() == "src/game/indy_comms.c":
            window="\n".join(raw_lines[max(0,i-8):min(len(raw_lines),i+8)])
            m=re.search(r"u8\s*\*\s*([A-Za-z_]\w*)", window)
            if m and re.search(r"indycmdAck\w*\s*\(\s*&\s*"+re.escape(m.group(1))+r"\b", window):
                add("P0","wire-token-written-through-host-pointer",path,i,raw,
                    "Indy response is a 32-bit wire token; receive into u32 then convert through uintptr_t.")

        # Desktop-only GL calls must not compile in a USE_GLES-positive branch.
        gles_state=next((v for k,v in reversed(pp) if k=="USE_GLES"),None)
        for fn in DESKTOP_GL:
            if re.search(r"\b"+re.escape(fn)+r"\s*\(",line) and gles_state is not False:
                add("P0","desktop-gl-on-gles-path",path,i,raw,
                    f"{fn} is desktop GL only and is not proven excluded from USE_GLES.")

        if re.search(r"\b(?:Gfx|Vtx|Mtx)\s*\*",line):
            window=" ".join(raw_lines[max(0,i-3):min(len(raw_lines),i+3)])
            if re.search(r"(?:\+=|-=|Alloc\w*\()\s*0x(?:40|80|100|180|200|400|800)\b",window):
                add("P1","fixed-n64-typed-reserve",path,i,raw,
                    "Typed graphics object is near a fixed byte reserve; verify sizeof/stride on LP64.")

def main():
    for f in iter_files(): scan_file(f)
    findings.sort(key=lambda x:(0 if x[0]=="P0" else 1,x[2],x[3],x[1]))
    out=Path("semantic-audit-out"); out.mkdir(exist_ok=True)
    with (out/"semantic-findings.tsv").open("w") as fp:
        fp.write("severity\tkind\tpath\tline\twhy\tcode\n")
        for sev,kind,path,line,code,why in findings:
            fp.write(f"{sev}\t{kind}\t{path}\t{line}\t{why}\t{code.replace(chr(9),' ')}\n")
    p0=[x for x in findings if x[0]=="P0"]
    with (out/"semantic-report.md").open("w") as fp:
        fp.write("# R36S semantic host-port audit\n\n")
        fp.write(f"- P0 known-bad semantic patterns: **{len(p0)}**\n")
        fp.write(f"- P1 manual ABI/layout reviews: **{len(findings)-len(p0)}**\n\n")
        for sev,kind,path,line,code,why in findings:
            fp.write(f"- **{sev} {kind}** \`{path}:{line}\` — {why}\n  - \`{code.replace(chr(96),chr(39))}\`\n")
    print(f"semantic audit: P0={len(p0)} P1={len(findings)-len(p0)} total={len(findings)}")
    if p0:
        for x in p0[:100]:
            print(f"{x[0]} {x[1]} {x[2]}:{x[3]}: {x[4]}")
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
