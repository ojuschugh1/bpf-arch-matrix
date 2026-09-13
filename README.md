# bpf-arch-matrix

A cross-architecture portability test suite for eBPF. Small, single-purpose probe programs run on both x86-64 and arm64 in CI, and the results are published as a compatibility matrix where every row says how it was established.


The eBPF instruction set is architecture independent, but eBPF programs are not. Syscall arguments arrive in different registers per architecture, which is why `bpf_tracing.h` needs a `__TARGET_ARCH_*` define and per-arch object files. Attachment types became available at different times on different architectures. On an arm64 kernel, a 32-bit process makes compat syscalls that native tracepoints never see. These differences are documented in scattered blog posts and issue threads. This repository turns them into checks that run continuously and produce answers you can link to.

## How it works

Each case lives in `cases/<id>/` and consists of exactly two required files:

- `case.json` - metadata: what the case probes and how to read the result
- `probe.sh` - the check itself, self-contained

Probe contract: exit `0` = pass, `1` = fail, `2` = skip (cannot be evaluated in this environment, for example a missing tool). Anything else is an error. Probes print evidence to stdout and a final `reason: ...` line.

The runner (`runner/run.py`, Python standard library only) executes every case, records status, reason and evidence, and writes `results/results-<label>.json`. In CI this happens on each runner in the matrix, and `runner/combine.py` merges the per-environment files into `matrix.md` and `matrix.json`.

## Current cases

| id | probes |
|---|---|
| attach-fentry-vfs-read | can an fentry program attach (requires BPF trampoline support) |
| attach-kprobe-vfs-read | can a kprobe attach to a common kernel function |
| attach-rawtracepoint-sys-enter | can a raw tracepoint attach |
| attach-tracepoint-execve | can the execve syscall tracepoint attach and observe an exec |
| baseline-btf-vmlinux | does the kernel expose BTF at /sys/kernel/btf/vmlinux (CO-RE baseline) |
| toolchain-arch-define-required | does bpf_tracing.h refuse PT_REGS access without __TARGET_ARCH_*, and accept the correct define |

One expectation worth stating up front: fentry requires BPF trampoline support, which x86-64 gained in kernel 5.5 and arm64 only in 6.0. On a 5.15 kernel the fentry probe should fail on arm64 and pass on x86-64. Whether the matrix ever shows that depends on which kernels the runner images carry; today they all run 6.x, so reaching a 5.15 kernel needs the VM-based tooling on the roadmap.

## Provenance rules

Every published result is one of:

- **tested-here**: produced by this repository's CI, linked to the run that produced it
- **reported-elsewhere**: documented behaviour we cannot reproduce in these environments (for example hardened kernels that forbid kprobes), included with a citation and clearly marked

The two are never mixed in a cell. A portability reference that blurs measurement and hearsay is worse than no reference.

## CI environments

GitHub-hosted runners, all free for public repositories:

- `ubuntu-24.04` and `ubuntu-24.04-arm`
- `ubuntu-22.04` and `ubuntu-22.04-arm`

The kernel on each runner is whatever the image ships that week (recorded in every result), so the 22.04 and 24.04 images are two kernel generations only when GitHub's images happen to differ. Check the `kernel` field in the results before reading a row as a kernel difference.

Runs happen on push, on pull requests, weekly on a schedule so the matrix tracks runner kernel updates, and on demand.

## Tooling is pinned, on purpose

Every runner installs the same bpftrace and bpftool release binaries instead of the distro packages. The first run of this matrix reported fentry and raw tracepoint failures on both 22.04 runners that turned out to be Ubuntu 22.04's bpftrace 0.14 not understanding the probe syntax, on a kernel that supported both. That is a tooling difference wearing a kernel difference's clothes, and it is exactly the kind of blur this project exists to avoid. With the same tool versions everywhere, a differing cell means the kernel or the architecture differs, not the package manager.

## Running locally

Linux with a recent kernel:

```
sudo python3 runner/run.py
```

On any OS, `python3 runner/run.py --list` shows the discovered cases without running them. Probes need root because loading eBPF programs does.

## Adding a case

Copy an existing case directory, keep the probe self-contained, follow the exit-code contract, and print a `reason:` line. One behaviour per case. If the probe needs a tool that may be absent, exit 2 with a reason instead of failing.

## Roadmap

- 32-bit compat visibility case (aarch32 EL0 support varies by CPU, so this is itself a matrix entry)
- A QEMU script for running the arm64 corpus locally on an x86-64 machine
- More kernel versions via VM-based tooling (vmtest, virtme-ng) rather than only runner images
- Browsable static page generated from matrix.json
- reported-elsewhere entries with citations for behaviour outside these environments

## License

MIT
