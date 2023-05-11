from snakemake.shell import shell

log = snakemake.log_fmt_shell()

reduce_memory = snakemake.params.get("reduce_memory", True)
reduce_memory_mode = "-2" if reduce_memory else ""

shell(
    "("
    " seqtk sample"
    " -s {snakemake.params.seed}"
    " {reduce_memory_mode}"
    " {snakemake.input.read}"
    " {snakemake.params.n_reads}"
    " |"
    " pigz -9"
    " -p {snakemake.threads}"
    " > {snakemake.output.read}"
    ") {log}"
)
