#!/usr/bin/env python3
from __future__ import annotations
import ast, re, sys
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
        if (host_active and explicit_width_boundary.search(line)
                and "N64_PTR_TO_U32_TOKEN" not in line
                and "N64_PTR_TO_S32_TOKEN" not in line):
            add("P1","explicit-32bit-token-boundary",path,i,raw,
                "Raw uintptr_t/intptr_t to 32-bit conversion; classify it and replace proven N64 ABI/token boundaries with N64_PTR_TO_*_TOKEN.")

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

        # Decompiler artifact: testing the address of a member through a
        # possibly-null base does not test the base pointer. On modern hosts
        # this is undefined behavior and compilers are free to fold the
        # condition unexpectedly. Test the owning pointer directly instead.
        if re.search(
            r"\b(?:if|while)\s*\(\s*!\s*&\s*"
            r"[A-Za-z_]\w*(?:(?:->|\.)[A-Za-z_]\w*|\[[^\]]+\])*"
            r"\s*->\s*[A-Za-z_]\w*\s*\)",
            line,
        ):
            add("P0","member-address-null-check",path,i,raw,
                "Address-of a member is used as a NULL test; test the owning pointer before dereferencing it.")

        # Bitmask/comparison precedence is a real host/runtime hazard.
        # Expressions such as `flags & MASK > 0` parse as
        # `flags & (MASK > 0)`, while `avail & MASK == 0` can become a
        # constant-zero mask. Require the intended mask operation explicitly.
        value = r"[A-Za-z_]\w*(?:(?:->|\.)[A-Za-z_]\w*)*"
        if re.search(
            r"\b(?:if|while)\s*\([^\n;]*" + value +
            r"\s*(?:(?<!&)\&(?!&)|(?<!\|)\|(?!\|))\s*[A-Za-z_]\w*\s*(?:==|!=|>|<)",
            line,
        ):
            add("P0","bitmask-comparison-precedence",path,i,raw,
                "Bitmask is compared without grouping; use (flags & MASK) comparison semantics.")

        # A logical-not is 0/1 before a following bitwise AND. This exact
        # pattern caused controller-state checks to fail for controller bits
        # above bit 0.
        simple_value = r"[A-Za-z_]\w*(?:(?:->|\.)[A-Za-z_]\w*)*"
        if re.search(
            r"!\s*\(\s*" + simple_value + r"\s*\)\s*(?<!&)\&(?!&)",
            line,
        ):
            add("P0","logical-not-bitmask",path,i,raw,
                "Logical-not of a value is bitwise-ANDed separately; likely intended !(flags & MASK).")

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

        # N64 pointer arrays have 4-byte elements; native LP64 pointer arrays
        # have 8-byte elements. A decomp pattern that computes an offset with
        # `<< 2` / `* 4` and then byte-indexes a T** is a portability
        # hazard unless the PORT path explicitly uses sizeof(T *). Keep this
        # as P1 because some arrays intentionally remain serialized tokens.
        if host_active and re.search(r"(?:<<\s*2|\*\s*4\b)", line):
            window="\n".join(raw_lines[max(0,i-45):min(len(raw_lines),i+45)])
            pointer_arrays=re.findall(
                r"\b[A-Za-z_]\w*(?:\s+const)?\s*\*\s*\*\s*([A-Za-z_]\w*)\s*;",
                window,
            )
            for parr in pointer_arrays:
                if re.search(
                    r"\(\s*u8\s*\*\s*\)\s*" + re.escape(parr) +
                    r"\s*\+\s*[A-Za-z_]\w*",
                    window,
                ) and "sizeof" not in line:
                    add("P1","lp64-pointer-array-4byte-stride",path,i,raw,
                        "Pointer-array byte offset uses an N64 4-byte stride; verify PORT uses sizeof(pointer) or token-array storage.")
                    break

        if re.search(r"\b(?:Gfx|Vtx|Mtx)\s*\*",line):
            window=" ".join(raw_lines[max(0,i-3):min(len(raw_lines),i+3)])
            if re.search(r"(?:\+=|-=|Alloc\w*\()\s*0x(?:40|80|100|180|200|400|800)\b",window):
                add("P1","fixed-n64-typed-reserve",path,i,raw,
                    "Typed graphics object is near a fixed byte reserve; verify sizeof/stride on LP64.")

def check_propdef_stride_contract():
    """Cross-check offline propDef expansion against the runtime stream walk.

    A mismatch here means the converter emits one record width while
    sizepropdef() advances by another: every following polymorphic setup record
    is then decoded at the wrong address.
    """
    converter=Path("tools_pc/d88_propdefs.py")
    constants=Path("src/bondconstants.h")
    runtime=Path("src/game/loadobjectmodel.c")
    if not (converter.exists() and constants.exists() and runtime.exists()):
        return

    try:
        tree=ast.parse(converter.read_text(errors="replace"))
        pc_bytes=None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                if any(isinstance(t, ast.Name) and t.id=="PROPDEF_PC_BYTES" for t in node.targets):
                    pc_bytes=ast.literal_eval(node.value)
                    break
        if not isinstance(pc_bytes, dict):
            raise ValueError("PROPDEF_PC_BYTES not found")

        ctext=constants.read_text(errors="replace")
        m=re.search(r"typedef\s+enum\s+PROPDEF_TYPE\s*\{(.*?)\}\s*PROPDEF_TYPE\s*;", ctext, re.S)
        if not m:
            raise ValueError("PROPDEF_TYPE enum not found")
        enum_map={}
        value=-1
        for raw in m.group(1).split(","):
            item=re.sub(r"/\*.*?\*/|//.*", "", raw, flags=re.S).strip()
            if not item:
                continue
            if "=" in item:
                name,rhs=(x.strip() for x in item.split("=",1))
                value=int(rhs,0)
            else:
                name=item
                value+=1
            if name.startswith("PROPDEF_"):
                enum_map[name]=value

        rtext=runtime.read_text(errors="replace")
        fm=re.search(r"s32\s+sizepropdef\s*\([^)]*\)\s*\{(.*?)(?=\n}\s*\n)", rtext, re.S)
        if not fm:
            raise ValueError("sizepropdef() not found")
        pm=re.search(r"#ifdef\s+PORT(.*?)#endif", fm.group(1), re.S)
        if not pm:
            raise ValueError("PORT sizepropdef switch not found")

        runtime_bytes={}
        pending=[]
        for raw in pm.group(1).splitlines():
            line=re.sub(r"/\*.*?\*/|//.*", "", raw).strip()
            cm=re.match(r"case\s+(PROPDEF_[A-Za-z0-9_]+)\s*:", line)
            if cm:
                pending.append(cm.group(1))
            rm=re.search(r"\breturn\s+(\d+)\s*;", line)
            if rm and pending:
                nbytes=int(rm.group(1))*4
                for name in pending:
                    if name in enum_map:
                        runtime_bytes[enum_map[name]]=nbytes
                pending=[]

        for ptype, emitted in sorted(pc_bytes.items()):
            walked=runtime_bytes.get(ptype)
            if walked is None:
                add("P0","propdef-stride-contract",runtime,1,
                    f"type {ptype}: runtime stride missing",
                    "Offline converter emits this propDef type but PORT sizepropdef() has no matching stride.")
            elif walked != emitted:
                add("P0","propdef-stride-contract",runtime,1,
                    f"type {ptype}: converter={emitted} runtime={walked}",
                    "Offline propDef byte size and runtime walk stride disagree; following records will desynchronise.")
    except Exception as exc:
        add("P0","propdef-stride-audit-error",runtime,1,str(exc),
            "Could not prove converter/runtime propDef stride agreement.")


def main():
    for f in iter_files(): scan_file(f)
    check_propdef_stride_contract()
    findings.sort(key=lambda x:(0 if x[0]=="P0" else 1,x[2],x[3],x[1]))
    out=Path("semantic-audit-out"); out.mkdir(exist_ok=True)
    with (out/"semantic-findings.tsv").open("w") as fp:
        fp.write("severity\tkind\tpath\tline\twhy\tcode\n")
        for sev,kind,path,line,code,why in findings:
            fp.write(f"{sev}\t{kind}\t{path}\t{line}\t{why}\t{code.replace(chr(9),' ')}\n")
    p0=[x for x in findings if x[0]=="P0"]
    p1=[x for x in findings if x[0]=="P1"]
    with (out/"semantic-report.md").open("w") as fp:
        fp.write("# R36S semantic host-port audit\n\n")
        fp.write(f"- P0 known-bad semantic patterns: **{len(p0)}**\n")
        fp.write(f"- P1 manual ABI/layout reviews: **{len(p1)}**\n\n")
        for sev,kind,path,line,code,why in findings:
            fp.write(f"- **{sev} {kind}** `{path}:{line}` — {why}\n  - `{code.replace(chr(96),chr(39))}`\n")
    print(f"semantic audit: P0={len(p0)} P1={len(p1)} total={len(findings)}")
    for x in findings:
        print(f"{x[0]} {x[1]} {x[2]}:{x[3]}: {x[4]} :: {x[5]}")
    return 2 if p0 else 0

if __name__=="__main__":
    raise SystemExit(main())
