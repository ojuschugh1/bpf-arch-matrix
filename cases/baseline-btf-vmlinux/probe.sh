#!/usr/bin/env bash
# exit: 0 pass, 1 fail, 2 skip
set -u

f=/sys/kernel/btf/vmlinux
if [ -r "$f" ]; then
    size=$(stat -c %s "$f" 2>/dev/null || wc -c < "$f")
    echo "found $f ($size bytes)"
    echo "reason: kernel BTF present"
    exit 0
fi
echo "reason: $f missing or unreadable"
exit 1
