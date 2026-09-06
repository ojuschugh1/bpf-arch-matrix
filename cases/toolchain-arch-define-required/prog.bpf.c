#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

SEC("kprobe/vfs_read")
int BPF_KPROBE(probe_vfs_read, struct file *file)
{
	return 0;
}

char LICENSE[] SEC("license") = "GPL";
