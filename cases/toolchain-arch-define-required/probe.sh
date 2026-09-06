#!/usr/bin/env bash
# exit: 0 pass, 1 fail, 2 skip
set -u

here=$(cd "$(dirname "$0")" && pwd)

command -v clang >/dev/null 2>&1 || { echo "reason: clang not installed"; exit 2; }
[ -r /sys/kernel/btf/vmlinux ] || { echo "reason: no kernel BTF to generate vmlinux.h from"; exit 2; }

bpftool_bin=""
if command -v bpftool >/dev/null 2>&1 && bpftool version >/dev/null 2>&1; then
    bpftool_bin=bpftool
else
    for c in /usr/lib/linux-tools/*/bpftool; do
        [ -x "$c" ] && bpftool_bin="$c"
    done
fi
[ -n "$bpftool_bin" ] || { echo "reason: bpftool not available"; exit 2; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

"$bpftool_bin" btf dump file /sys/kernel/btf/vmlinux format c > "$work/vmlinux.h" 2>/dev/null \
    || { echo "reason: could not generate vmlinux.h from kernel BTF"; exit 2; }

case "$(uname -m)" in
    x86_64)  arch=x86 ;;
    aarch64) arch=arm64 ;;
    *) echo "reason: unmapped architecture $(uname -m)"; exit 2 ;;
esac

if clang -O2 -g -target bpf -I"$work" -c "$here/prog.bpf.c" -o "$work/no_arch.o" 2>"$work/no_arch.err"; then
    echo "unexpected: compiled without any __TARGET_ARCH_ define"
    echo "reason: bpf_tracing.h no longer requires a target arch define"
    exit 1
fi
echo "without define: $(grep -m1 -o 'Must specify a BPF target arch.*' "$work/no_arch.err" || tail -1 "$work/no_arch.err")"

if clang -O2 -g -target bpf -D__TARGET_ARCH_${arch} -I"$work" -c "$here/prog.bpf.c" -o "$work/with_arch.o" 2>"$work/with_arch.err"; then
    echo "with -D__TARGET_ARCH_${arch}: compiled cleanly"
    echo "reason: per-arch define required and sufficient on $(uname -m)"
    exit 0
fi
tail -5 "$work/with_arch.err"
echo "reason: compile failed even with -D__TARGET_ARCH_${arch}"
exit 1
