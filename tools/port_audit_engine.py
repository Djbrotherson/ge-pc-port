#!/usr/bin/env python3
from __future__ import annotations
import ast, importlib.util, json, os, re, sys
from pathlib import Path

ROOTS=tuple(
    p for p in os.environ.get("N64_PORT_AUDIT_ROOTS", os.pathsep.join(("src","include","port"))).split(os.pathsep)
    if p
)
EXCLUDE_PARTS=set(
    p for p in os.environ.get("N64_PORT_AUDIT_EXCLUDES", "third_party").split(os.pathsep)
    if p
)
PROJECT_NAME=os.environ.get("N64_PORT_AUDIT_PROJECT", "goldeneye-r36s")
CONTRACT_SUITE=os.environ.get("N64_PORT_AUDIT_CONTRACT_SUITE", "goldeneye")
ABI_CONTRACT_PATH=os.environ.get("N64_PORT_AUDIT_ABI_CONTRACT", "")
ABI_CONTRACT={}
if ABI_CONTRACT_PATH:
    ABI_CONTRACT=json.loads(Path(ABI_CONTRACT_PATH).read_text())
EXTS={".c",".h",".cc",".cpp",".cxx",".hpp"}
DESKTOP_GL={
 "glPolygonMode","glDrawBuffer","glGetTexImage","glTexImage1D","glTexSubImage1D",
 "glCopyTexImage1D","glCopyTexSubImage1D","glCompressedTexImage1D","glClearDepth",
 "glDepthRange","glGetDoublev","glPixelStoref"
}

findings=[]
POINTER_MEMBER_NAMES=set()

def add(sev,kind,path,line,code,why):
    findings.append((sev,kind,str(path),line,code.strip()[:300],why))

def iter_files():
    for root in ROOTS:
        p=Path(root)
        if not p.exists(): continue
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in EXTS and not (set(f.parts) & EXCLUDE_PARTS):
                yield f

def collect_pointer_member_names():
    """Harvest pointer field names from project headers before scanning uses.

    This catches casts of ordinary fields such as obj->model / node->Data that
    name-based ptr/addr heuristics miss. It is intentionally P1 at use sites
    because field names can be reused by unrelated scalar structs.
    """
    global POINTER_MEMBER_NAMES
    decl=re.compile(
        r"\b(?:struct\s+\w+|union\s+\w+|[A-Za-z_]\w*)"
        r"(?:\s+const)?\s*\*+\s*([A-Za-z_]\w*)"
        r"(?:\s*\[[^\]]*\])?\s*(?:;|,)"
    )
    names=set()
    for f in iter_files():
        if f.suffix not in {".h",".hpp"}:
            continue
        text=f.read_text(errors="replace")
        text=re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        text=re.sub(r"//.*", " ", text)
        for m in decl.finditer(text):
            names.add(m.group(1))
    POINTER_MEMBER_NAMES=names


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

        # Animation offsets must cross into native pointers through the
        # audited helper. Raw base+offset expressions duplicate the exact
        # signed/unsigned LP64 boundary that previously caused animation
        # crashes and make future audits harder.
        if (host_active and path.as_posix() != "src/game/initanitable.h"
                and re.search(r"(?:\(\s*u8\s*\*\s*\)\s*)?ptr_animation_table\s*\+", line)
                and "ANIM_TABLE_OFFSET_PTR" not in line):
            add("P0","raw-animation-table-rebase",path,i,raw,
                "Use ANIM_TABLE_OFFSET_PTR for 32-bit animation offsets rebased onto the native table pointer.")

        # Exact semantic regression class: synthetic animation symbols are
        # offsets. Comments have already been stripped above.
        if re.search(r"\(uintptr_t\)\s*&ANIM_DATA_", line) or re.search(r"\+\s*&ANIM_DATA_",line):
            add("P0","animation-token-as-host-pointer",path,i,raw,
                "ANIM_DATA_* is a synthetic N64 offset token on 64-bit hosts; use PTR_ANIM_* / low-32 offset semantics.")

        if host_active and re.search(r"\((?:s32|u32|int|unsigned\s+int)\)\s*&ANIM_DATA_", line):
            add("P0","animation-offset-legacy-cast",path,i,raw,
                "ANIM_DATA_* is an N64 animation offset token; use the generated PTR_ANIM_* constant on the host path.")

        # Pointer members used as scalar/tag storage are another common
        # decomp portability boundary. Ignore ordinary NULL/zero tests, but
        # surface comparisons against other numeric constants and bitwise
        # operations for explicit classification.
        scalar_member=re.search(
            r"(?:->|\.)([A-Za-z_]\w*)\s*"
            r"(?:(?:==|!=|<=|>=|<|>)\s*(0x[0-9A-Fa-f]+|[1-9]\d*)|"
            r"(?<!&)&(?!&)\s*(0x[0-9A-Fa-f]+|[1-9]\d*)|"
            r"(?<!\|)\|(?!\|)\s*(0x[0-9A-Fa-f]+|[1-9]\d*))",
            line,
        )
        if host_active and scalar_member and scalar_member.group(1) in POINTER_MEMBER_NAMES:
            add("P1","pointer-member-used-as-scalar",path,i,raw,
                "A declared pointer member is compared/combined with a nonzero scalar; classify intentional token/tag union vs native pointer.")

        # Pointer tag/flag tests are architecture-sensitive. They may be
        # intentional tagged-pointer ABI, but ordinary heap/module pointers
        # also naturally contain these bits on modern hosts. Keep them visible
        # for manual classification rather than silently inheriting N64-era
        # assumptions.
        if host_active and re.search(
            r"\(\s*uintptr_t\s*\)\s*[^;\n]+(?:->|\.)[A-Za-z_]\w*\s*&\s*"
            r"(?:\(\s*uintptr_t\s*\)\s*)?0x[0-9A-Fa-f]+",
            line,
        ):
            add("P1","pointer-tag-bit-test",path,i,raw,
                "Native pointer bits are used as flags; prove an intentional tagged-pointer contract or move the flag to scalar state.")

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

        # Type-informed pointer-member narrowing. Header harvesting catches
        # ordinary field names (model, anim, data, next, table, ...), which
        # naming heuristics alone cannot distinguish. Keep as P1 because a
        # field name can be reused by unrelated scalar structs.
        m_member_cast=re.search(
            r"\((?:s32|u32|int|unsigned\s+int)\)\s*"
            r"[^;\n]+(?:->|\.)([A-Za-z_]\w*)\b",
            line,
        )
        if (host_active and m_member_cast
                and m_member_cast.group(1) in POINTER_MEMBER_NAMES
                and "uintptr_t" not in line and "intptr_t" not in line
                and "N64_PTR_TO_" not in line):
            add("P1","declared-pointer-member-narrowing",path,i,raw,
                "A field declared as a pointer somewhere in project headers is narrowed to 32 bits; classify native pointer vs N64 token.")

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
        if host_active and re.search(
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

        # Pointer storage type-punned through a 32-bit integer lvalue can
        # truncate or overwrite half of a native pointer without an explicit
        # cast at the write site. Surface these aliases on host-active paths.
        if (host_active and re.search(
            r"\(\s*(?:s32|u32)\s*\*\s*\)\s*&\s*"
            r"[^;\n]+(?:->|\.)([A-Za-z_]\w*)\b",
            line,
        )):
            m_alias=re.search(
                r"\(\s*(?:s32|u32)\s*\*\s*\)\s*&\s*"
                r"[^;\n]+(?:->|\.)([A-Za-z_]\w*)\b",
                line,
            )
            if m_alias and m_alias.group(1) in POINTER_MEMBER_NAMES:
                add("P1","pointer-storage-aliased-as-u32",path,i,raw,
                    "Declared pointer storage is aliased through s32*/u32*; verify this is an N64 token slot rather than native pointer storage.")

        # Native pointer-array storage must scale by sizeof(pointer), not
        # the N64 element width. These patterns are especially dangerous
        # because they often corrupt several entries before the crash site.
        window="\n".join(raw_lines[max(0,i-4):min(len(raw_lines),i+5)])
        ptr_array_names=re.findall(
            r"\b[A-Za-z_]\w*(?:\s+const)?\s*\*\s*\*\s*([A-Za-z_]\w*)",
            window,
        )
        if ptr_array_names and re.search(r"\b(?:memcpy|memmove|memset)\s*\(", line):
            if re.search(r"(?:\*\s*4\b|<<\s*2\b|\b4\s*\*)", window):
                add("P1","lp64-pointer-array-bulk-4byte-size",path,i,raw,
                    "Bulk operation near a native pointer array uses a hard-coded 4-byte element size; verify sizeof(pointer).")

        if ptr_array_names and re.search(r"\b(?:malloc|calloc|realloc|mempAlloc\w*|gfxAllocate\w*|fileAllocate\w*)\s*\(", line):
            if re.search(r"(?:\*\s*4\b|<<\s*2\b|\b4\s*\*)", window):
                add("P1","lp64-pointer-array-allocation-4byte-size",path,i,raw,
                    "Allocation near a native pointer array uses a hard-coded 4-byte element size; verify sizeof(pointer).")

        if re.search(r"\b(?:Gfx|Vtx|Mtx)\s*\*",line):
            window=" ".join(raw_lines[max(0,i-3):min(len(raw_lines),i+3)])
            if re.search(r"(?:\+=|-=|Alloc\w*\()\s*0x(?:40|80|100|180|200|400|800)\b",window):
                add("P1","fixed-n64-typed-reserve",path,i,raw,
                    "Typed graphics object is near a fixed byte reserve; verify sizeof/stride on LP64.")

def check_ai_command_endian_contract():
    """Prove packed BE AI bytecode multibyte fields are swapped at use sites."""
    header=Path("src/aicommands2.h")
    interp=Path("src/game/chrai.c")
    if not (header.exists() and interp.exists()):
        return
    try:
        htext=header.read_text(errors="replace")
        ctext=interp.read_text(errors="replace")
        multi={}
        for m in re.finditer(
            r"typedef\s+struct\s+(Ai[A-Za-z0-9_]+Record)\s*\{(.*?)\}"
            r"\s*\1\s*;",
            htext,re.S,
        ):
            fields=[]
            for fm in re.finditer(r"\b(u16|s16|u32|s32)\s+([A-Za-z_]\w*)\b",m.group(2)):
                fields.append((fm.group(1),fm.group(2)))
            if fields:
                multi[m.group(1)]=fields

        for rec,fields in sorted(multi.items()):
            decl=re.compile(re.escape(rec)+r"\s*\*\s*([A-Za-z_]\w*)")
            for dm in decl.finditer(ctext):
                var=dm.group(1)
                tail=ctext[dm.start():dm.start()+3000]
                nxt=re.search(r"\n\s*case\s+AI_[A-Za-z0-9_]+\s*:",tail)
                block=tail[:nxt.start()] if nxt else tail
                for ftype,fname in fields:
                    use=re.compile(r"\b"+re.escape(var)+r"->"+re.escape(fname)+r"\b")
                    for um in use.finditer(block):
                        ls=block.rfind("\n",0,um.start())+1
                        le=block.find("\n",um.start())
                        line=block[ls:(len(block) if le<0 else le)]
                        if "ntohs(" not in line and "ntohl(" not in line:
                            add("P0","ai-bytecode-unswapped-field",interp,1,line.strip(),
                                f"{rec}.{fname} is {ftype} in big-endian AI bytecode and is read without ntohs/ntohl.")
    except Exception as exc:
        add("P0","ai-bytecode-endian-audit-error",interp,1,str(exc),
            "Could not prove AI bytecode multibyte field endian handling.")


def check_ai_command_layout_contract():
    """Prove generated AI bytecode structs match their encoded byte lengths."""
    header=Path("src/aicommands2.h")
    if not header.exists():
        return
    try:
        text=header.read_text(errors="replace")
        if "#pragma pack(1)" not in text:
            add("P0","ai-bytecode-pack-contract",header,1,"#pragma pack(1) missing",
                "AI command records are serialized bytecode and must remain byte-packed.")
            return

        lengths={}
        for m in re.finditer(
            r"^#define\s+AI_([A-Za-z0-9_]+)_LENGTH\s+\(AICMDSIZE([^)]*)\)",
            text,re.M,
        ):
            n=1
            for sign,num in re.findall(r"([+-])\s*(\d+)",m.group(2)):
                n += int(num) if sign=="+" else -int(num)
            lengths[m.group(1)]=n

        widths={"u8":1,"s8":1,"u16":2,"s16":2,"u32":4,"s32":4,"f32":4}
        records={}
        struct_re=re.compile(
            r"typedef\s+struct\s+Ai([A-Za-z0-9_]+)Record\s*\{(.*?)\}"
            r"\s*Ai\1Record\s*;",
            re.S,
        )
        field_re=re.compile(
            r"^(u8|s8|u16|s16|u32|s32|f32)\s+[A-Za-z_]\w*"
            r"(?:\[(\d+)\])?\s*;$"
        )
        for m in struct_re.finditer(text):
            size=0
            ok=True
            body=re.sub(r"/\*.*?\*/"," ",m.group(2),flags=re.S)
            for raw in body.splitlines():
                line=re.sub(r"//.*","",raw).strip()
                if not line:
                    continue
                fm=field_re.match(line)
                if not fm:
                    ok=False
                    break
                size += widths[fm.group(1)] * (int(fm.group(2)) if fm.group(2) else 1)
            if ok:
                records[m.group(1)]=size

        if len(lengths) != len(records):
            add("P0","ai-bytecode-record-coverage",header,1,
                f"lengths={len(lengths)} records={len(records)}",
                "Generated AI length macros and bytecode record structs must have one-to-one coverage.")

        for name,encoded in sorted(lengths.items()):
            actual=records.get(name)
            if actual is None:
                add("P0","ai-bytecode-record-missing",header,1,name,
                    "AI length macro has no parseable matching packed record struct.")
            elif actual != encoded:
                add("P0","ai-bytecode-size-contract",header,1,
                    f"{name}: struct={actual} encoded={encoded}",
                    "AI command struct size disagrees with encoded command length; interpreter offsets will desynchronise.")

        interp=Path("src/game/chrai.c")
        if interp.exists():
            itext=interp.read_text(errors="replace")
            dispatch={}
            for m in re.finditer(
                r"case\s+AI_([A-Za-z0-9_]+)\s*:\s*"
                r"(?:/\*.*?\*/\s*)?"
                r"return\s+sizeof\(\s*Ai([A-Za-z0-9_]+)Record\s*\)\s*;",
                itext,re.S,
            ):
                dispatch[m.group(1)]=m.group(2)
            if len(dispatch) != len(lengths):
                add("P0","ai-bytecode-dispatch-coverage",interp,1,
                    f"dispatch={len(dispatch)} generated={len(lengths)}",
                    "chraiitemsize() must cover every fixed-size generated AI command exactly once.")
            for name in sorted(lengths):
                mapped=dispatch.get(name)
                if mapped is None:
                    add("P0","ai-bytecode-dispatch-missing",interp,1,name,
                        "Generated AI command is missing from chraiitemsize() fixed-size dispatch.")
                elif mapped != name:
                    add("P0","ai-bytecode-dispatch-record",interp,1,
                        f"{name}: maps to Ai{mapped}Record",
                        "AI command dispatch returns sizeof() for a different record type.")
    except Exception as exc:
        add("P0","ai-bytecode-audit-error",header,1,str(exc),
            "Could not prove generated AI bytecode record/length agreement.")


def check_abi_size_assertions():
    """Prove the ABI manifest is represented by matching C compile-time guards."""
    specs=ABI_CONTRACT.get("size_asserts", [])
    if not specs:
        return
    for spec in specs:
        path=Path(spec.get("path",""))
        type_name=str(spec.get("type",""))
        expected=spec.get("bytes")
        if not path.exists() or not type_name or not isinstance(expected,int):
            add("P0","abi-size-assert-spec",path or Path("."),1,str(spec),
                "ABI size assertion entry is incomplete or references a missing source file.")
            continue
        text=path.read_text(errors="replace")
        pat=re.compile(
            r"(?:GE_LAYOUT_ASSERT|static_assert|_Static_assert)\s*\(\s*"
            r"sizeof\(\s*"+re.escape(type_name)+r"\s*\)\s*==\s*"
            r"(0x[0-9A-Fa-f]+|\d+)"
        )
        values=[int(m.group(1),0) for m in pat.finditer(text)]
        if not values:
            add("P0","abi-size-assert-missing",path,1,type_name,
                f"ABI manifest requires sizeof({type_name}) == {expected}, but no matching compile-time assertion exists.")
        elif expected not in values:
            add("P0","abi-size-assert-mismatch",path,1,
                f"{type_name}: asserted={values} manifest={expected}",
                "C compile-time size guard disagrees with the machine-readable ABI manifest.")


def check_renderer_reload_contract():
    """Keep host renderer cache lifetime aligned with game texture lifetime."""
    lv=Path("src/game/lv.c")
    gfx=Path("port/fast3d/gfx_pc.cpp")
    if not (lv.exists() and gfx.exists()):
        return
    try:
        ltext=lv.read_text(errors="replace")
        gtext=gfx.read_text(errors="replace")
        if 'extern "C" void reset_texture_state()' not in gtext:
            add("P0","renderer-reset-export",gfx,1,"reset_texture_state",
                "Renderer texture/shader cache reset must remain callable from the C game lifecycle.")
        m=re.search(
            r'R36S_LV_BREADCRUMB\("lv:texReset"\);(.*?)'
            r'R36S_LV_BREADCRUMB\("lv:post-texReset"\);',
            ltext,re.S,
        )
        if not m or "texReset();" not in m.group(1) or "reset_texture_state();" not in m.group(1):
            add("P0","renderer-level-reload-reset",lv,1,
                "texReset/reset_texture_state lifecycle pair missing",
                "Level reload must clear both GoldenEye texture state and host renderer caches; recycled stage addresses otherwise permit stale texture hits.")
    except Exception as exc:
        add("P0","renderer-reload-audit-error",lv,1,str(exc),
            "Could not prove renderer/game texture reset alignment.")


def check_stage_setup_layout_contract():
    """Cross-check d88 growing-table widths against native setup structs."""
    converter=Path("tools_pc/d88_emit.py")
    if not converter.exists():
        return
    try:
        text=converter.read_text(errors="replace")
        spec=ABI_CONTRACT.get("stage_setup", {})
        expected={
            name:tuple(pair)
            for name,pair in spec.get("growth_tables", {}).items()
        }
        if not expected:
            raise ValueError("stage_setup.growth_tables missing from ABI contract")
        found={}
        for name,oldsz,newsz in re.findall(
            r"\(\s*\"([A-Za-z0-9_]+)\"\s*,[^\n]*?,\s*(\d+)\s*,\s*(\d+)\s*\)",
            text,
        ):
            if name in expected:
                found[name]=(int(oldsz),int(newsz))
        if found != expected:
            add("P0","stage-setup-growth-contract",converter,1,
                f"found={found}",
                "d88 setup-table growth sizes drifted from the compile-time ABI contract in bondtypes.h.")
        m=re.search(r"cum\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*#\s*header grows",text)
        expected_growth=int(spec.get("header_host_bytes",0))-int(spec.get("header_n64_bytes",0))
        if expected_growth <= 0:
            raise ValueError("invalid stage_setup header sizes in ABI contract")
        if not m or int(m.group(1),0) != expected_growth:
            add("P0","stage-setup-header-growth",converter,1,
                m.group(0) if m else "missing header growth seed",
                f"d88 stage header growth must match ABI contract delta {expected_growth} bytes.")
    except Exception as exc:
        add("P0","stage-setup-audit-error",converter,1,str(exc),
            "Could not prove d88 stage setup table/native ABI agreement.")


def check_model_sidecar_layout_contract():
    """Cross-check d43 model sidecar native record widths."""
    converter=Path("tools_pc/d43_emit.py")
    if not converter.exists():
        return
    try:
        tree=ast.parse(converter.read_text(errors="replace"))
        pc_node=None
        pc_rec=None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id=="PC_NODE":
                        pc_node=ast.literal_eval(node.value)
                    elif isinstance(t, ast.Name) and t.id=="PC_REC":
                        pc_rec=ast.literal_eval(node.value)
        spec=ABI_CONTRACT.get("model_sidecar", {})
        expected_node=int(spec.get("model_node_host_bytes",0))
        expected_rec={int(k):int(v) for k,v in spec.get("rodata_host_bytes",{}).items()}
        if expected_node <= 0 or not expected_rec:
            raise ValueError("model_sidecar contract missing from ABI manifest")
        if pc_node != expected_node:
            add("P0","model-sidecar-node-stride",converter,1,
                f"PC_NODE={pc_node}",
                f"Model sidecar converter must emit {expected_node}-byte native ModelNode records.")
        if pc_rec != expected_rec:
            add("P0","model-sidecar-rodata-strides",converter,1,
                f"PC_REC={pc_rec}",
                "Model sidecar converter native rodata sizes drifted from the compile-time ABI contract in bondtypes.h.")
    except Exception as exc:
        add("P0","model-sidecar-audit-error",converter,1,str(exc),
            "Could not prove model sidecar converter/native ABI agreement.")


def check_stan_layout_contract():
    """Cross-check STAN converter tile strides against runtime navigation."""
    converter=Path("tools_pc/d69_emit.py")
    runtime=Path("src/game/stan.c")
    if not (converter.exists() and runtime.exists()):
        return
    try:
        tree=ast.parse(converter.read_text(errors="replace"))
        conv_sizes=None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id=="TILESIZES" for t in node.targets
            ):
                conv_sizes=ast.literal_eval(node.value)
                break
        if not isinstance(conv_sizes, list):
            raise ValueError("TILESIZES not found in d69_emit.py")

        rtext=runtime.read_text(errors="replace")
        m=re.search(
            r"u8\s+list_of_tilesizes\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;",
            rtext,re.S,
        )
        if not m:
            raise ValueError("list_of_tilesizes[] not found in stan.c")
        vals=[]
        for tok in m.group(1).split(","):
            tok=re.sub(r"/\*.*?\*/|//.*","",tok,flags=re.S).strip()
            if tok:
                vals.append(int(tok,0))
        if vals != conv_sizes:
            add("P0","stan-tilesize-contract",runtime,1,
                f"runtime={vals} converter={conv_sizes}",
                "STAN converter and runtime tile-size tables disagree; navigation tile walks will desynchronise.")

        spec=ABI_CONTRACT.get("stan", {})
        expected=[int(x) for x in spec.get("tile_sizes_by_point_count",[])]
        if not expected:
            raise ValueError("stan.tile_sizes_by_point_count missing from ABI contract")
        if conv_sizes != expected:
            add("P0","stan-tilesize-shape",converter,1,str(conv_sizes),
                "STAN point-count stride table no longer matches the ABI manifest.")
    except Exception as exc:
        add("P0","stan-layout-audit-error",runtime,1,str(exc),
            "Could not prove STAN converter/runtime tile-size agreement.")


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
            item=re.sub(r"/\*.*?\*/|//[^\n]*", "", raw, flags=re.S).strip()
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

        # Exercise every converter branch without requiring the copyrighted ROM.
        # A synthetic record is sufficient to prove branch coverage, output
        # length, record-header preservation and whole-stream walk agreement.
        spec=importlib.util.spec_from_file_location("d88_propdefs_gate", converter)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        synthetic=bytearray()
        expected_pc=0
        for ptype in sorted(module.PROPDEF_N64_WORDS):
            if ptype == 48:
                continue
            n64w=module.PROPDEF_N64_WORDS[ptype]
            rec=bytearray(n64w * 4)
            rec[3]=ptype
            converted=module.convert_record(rec, 0, ptype)
            if len(converted) != module.PROPDEF_PC_BYTES[ptype]:
                raise ValueError(
                    f"converter type {ptype} length={len(converted)} "
                    f"expected={module.PROPDEF_PC_BYTES[ptype]}"
                )
            if converted[3] != ptype:
                raise ValueError(f"converter type {ptype} lost header type byte")
            synthetic += rec
            expected_pc += module.PROPDEF_PC_BYTES[ptype]

        end=bytearray(module.PROPDEF_N64_WORDS[48] * 4)
        end[3]=48
        synthetic += end
        expected_pc += module.PROPDEF_PC_BYTES[48]
        converted,n64len,pclen=module.convert_stream(synthetic,0,len(synthetic))
        if n64len != len(synthetic) or pclen != expected_pc or len(converted) != expected_pc:
            raise ValueError(
                f"synthetic stream mismatch n64={n64len}/{len(synthetic)} "
                f"pc={pclen}/{expected_pc} bytes={len(converted)}"
            )
    except Exception as exc:
        add("P0","propdef-stride-audit-error",runtime,1,str(exc),
            "Could not prove converter/runtime propDef stride agreement.")


def main():
    collect_pointer_member_names()
    for f in iter_files(): scan_file(f)
    check_abi_size_assertions()
    if CONTRACT_SUITE == "goldeneye":
        check_propdef_stride_contract()
        check_renderer_reload_contract()
        check_stage_setup_layout_contract()
        check_model_sidecar_layout_contract()
        check_stan_layout_contract()
        check_ai_command_layout_contract()
        check_ai_command_endian_contract()
    elif CONTRACT_SUITE:
        add("P0","unknown-contract-suite",Path("."),1,CONTRACT_SUITE,
            "Profile requested an unknown project-specific contract suite.")
    findings.sort(key=lambda x:(0 if x[0]=="P0" else 1,x[2],x[3],x[1]))
    out=Path("semantic-audit-out"); out.mkdir(exist_ok=True)
    with (out/"semantic-findings.tsv").open("w") as fp:
        fp.write("severity\tkind\tpath\tline\twhy\tcode\n")
        for sev,kind,path,line,code,why in findings:
            fp.write(f"{sev}\t{kind}\t{path}\t{line}\t{why}\t{code.replace(chr(9),' ')}\n")
    p0=[x for x in findings if x[0]=="P0"]
    p1=[x for x in findings if x[0]=="P1"]
    with (out/"semantic-report.md").open("w") as fp:
        fp.write(f"# N64 semantic host-port audit — {PROJECT_NAME}\n\n")
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
