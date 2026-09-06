#!/usr/bin/env bash
# exit: 0 pass, 1 fail, 2 skip
set -u

command -v bpftrace >/dev/null 2>&1 || { echo "reason: bpftrace not installed"; exit 2; }

out=$(timeout 60 bpftrace -e 'rawtracepoint:sys_enter { @calls = count(); }' -c /bin/true 2>&1)
rc=$?
echo "$out"
case $rc in
    0)   echo "reason: raw tracepoint attached to sys_enter"; exit 0 ;;
    124) echo "reason: bpftrace did not exit within 60s"; exit 1 ;;
    *)   echo "reason: attach failed (bpftrace rc=$rc)"; exit 1 ;;
esac
