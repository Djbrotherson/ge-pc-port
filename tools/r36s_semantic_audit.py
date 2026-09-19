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

def scan_file(path:Path):
    lines=path.read_text(errors="replace").splitlines()
    pp=[]
    in_port=False
    for i,line in enumerate(lines,1):
        s=line.strip()

        # Track enough preprocessing state to identify PORT / USE_GLES guards.
        if s.startswith("#ifdef PORT"):
            pp.append(("PORT",True)); in_port=True
        elif s.startswith("#ifndef PORT"):
            pp.append(("PORT",False)); in_port=False
        elif s.startswith("#ifdef USE_GLES") or s.startswith("#if defined(USE_GLES)"):
            pp.append(("USE_GLES",True))
        elif s.startswith("#ifndef USE_GLES") or ("#if" in s and "!defined(USE_GLES)" in s):
            pp.append(("USE_GLES",False))
        elif s.startswith("#if") and "__x86_64__" in s and "__aarch64__" not in s:
            add("P0","x86-only-64bit-guard",path,i,line,
                "64-bit host fix is enabled on x86_64 but not AArch64.")
            pp.append(("OTHER",None))
        elif s.startswith("#if"):
            pp.append(("OTHER",None))
        elif s.startswith("#else") and pp:
            k,v=pp[-1]
            if k in ("PORT","USE_GLES"):
                pp[-1]=(k,not v)
                if k=="PORT": in_port=not v
        elif s.startswith("#endif") and pp:
            k,v=pp.pop()
            if k=="PORT":
                in_port=next((vv for kk,vv in reversed(pp) if kk=="PORT"),False)

        # Exact semantic regression class: synthetic animation symbols are offsets.
        if re.search(r"\(uintptr_t\)\s*&ANIM_DATA_", line) or re.search(r"\+\s*&ANIM_DATA_",line):
            add("P0","animation-token-as-host-pointer",path,i,line,
                "ANIM_DATA_* is a synthetic N64 offset token on 64-bit hosts; use PTR_ANIM_* / low-32 offset semantics.")

        # Shared source is host-active unless an enclosing PORT conditional proves
        # this line belongs only to the preserved N64 branch.
        port_state=next((v for k,v in reversed(pp) if k=="PORT"),None)
        host_active = port_state is not False

        # ANIM_DATA_* names are intentional 32-bit animation offsets.  Report them
        # separately so they can be converted mechanically to PTR_ANIM_* constants.
        if host_active and re.search(r"\((?:s32|u32|int|unsigned\s+int)\)\s*&ANIM_DATA_", line):
            add("P0","animation-offset-legacy-cast",path,i,line,
                "ANIM_DATA_* is an N64 animation offset token; use the generated PTR_ANIM_* constant on the host path.")

        # Real host object addresses must never pass through a 32-bit integer.
        # Skip explicit N64-only branches and the separately classified ANIM_DATA namespace.
        if host_active and "ANIM_DATA_" not in line and not s.startswith(("//", "/*", "*")) and re.search(
                r"\((?:s32|u32|int|unsigned\s+int)\)\s*&\s*[A-Za-z_]", line):
            if not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|PTR_ANIM|CART_BASE)", line):
                add("P0","host-address-narrowing",path,i,line,
                    "Native address is explicitly narrowed to 32 bits; classify as host pointer vs N64 token/offset before preserving.")

        if host_active and "ANIM_DATA_" not in line and not s.startswith(("//", "/*", "*")) and re.search(
                r"\((?:s32|u32|int|unsigned\s+int)\)\s*\(?\s*[A-Za-z_]\w*(?:ptr|pointer|addr|address|buf|buffer)\w*\s*\)?", line, re.I):
            if not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|PTR_ANIM|CART_BASE)", line):
                add("P0","host-pointer-variable-narrowing",path,i,line,
                    "Pointer-looking value is explicitly narrowed to 32 bits; classify before preserving legacy N64 arithmetic.")

        # Host pointer plus linker/ROM token is suspicious unless explicitly narrowed/tokenized.
        if re.search(r"\b(?:ptr|pointer|base|buf|buffer|data|addr|address)\w*\s*\+\s*\(uintptr_t\)\s*&\w*(?:SegmentRom|SegmentStart|SegmentEnd)", line, re.I):
            add("P0","linker-token-host-add",path,i,line,
                "Linker/ROM symbols are address tokens; full-width host addition changes N64 semantics.")

        # In PORT code, explicit host pointer narrowing is almost always wrong unless the line
        # is clearly converting a mapped/tokenized N64 address via a named helper.
        if in_port and re.search(r"\((?:s32|u32|int|unsigned\s+int)\)\s*(?:\([^\n;]*\*\)|&\w+|\w*(?:ptr|pointer|addr|address|buf|buffer)\w*)", line, re.I):
            if not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|SegmentRom|PTR_ANIM|CART_BASE)",line):
                add("P0","port-pointer-narrowing",path,i,line,
                    "PORT path narrows a host pointer to 32 bits without an explicit N64/token conversion helper.")

        # Pointer alignment/math through 32-bit casts in PORT code.
        if in_port and re.search(r"\((?:s32|u32)\)\s*[^;]+(?:\+|\-|&|\|)\s*(?:0x|\d)",line):
            if not re.search(r"(OS_K0_TO_PHYSICAL|osVirtualToPhysical|romptr|SegmentRom|PTR_ANIM)",line):
                add("P0","port-32bit-address-math",path,i,line,
                    "PORT path performs address arithmetic after 32-bit narrowing.")

        # Desktop-only GL calls must not execute in a USE_GLES-positive region.
        gles_state=next((v for k,v in reversed(pp) if k=="USE_GLES"),None)
        for fn in DESKTOP_GL:
            if re.search(r"\b"+re.escape(fn)+r"\s*\(",line):
                if gles_state is not False:
                    add("P0","desktop-gl-on-gles-path",path,i,line,
                        f"{fn} is desktop GL only and is not proven excluded from USE_GLES.")

        # Fixed byte reserves adjacent to typed Gfx/Vtx/Mtx allocations are ABI-sensitive.
        if re.search(r"\b(?:Gfx|Vtx|Mtx)\s*\*",line):
            window=" ".join(lines[max(0,i-3):min(len(lines),i+3)])
            if re.search(r"(?:\+=|-=|Alloc\w*\()\s*0x(?:40|80|100|180|200|400|800)\b",window):
                add("P1","fixed-n64-typed-reserve",path,i,line,
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
