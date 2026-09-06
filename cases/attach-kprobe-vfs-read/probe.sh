#!/usr/bin/env bash
# exit: 0 pass, 1 fail, 2 skip
set -u

command -v bpftrace >/dev/null 2>&1 || { echo "reason: bpftrace not installed"; exit 2; }

out=$(timeout 60 bpftrace -e 'kprobe:vfs_read { @reads = count(); }' -c '/bin/cat /etc/os-release' 2>&1)
rc=$?
echo "$out"
case $rc in
    0)   echo "reason: kprobe attached to vfs_read"; exit 0 ;;
    124) echo "reason: bpftrace did not exit within 60s"; exit 1 ;;
    *)   echo "reason: attach failed (bpftrace rc=$rc)"; exit 1 ;;
esac
