from snakemake.shell import shell

log = snakemake.log_fmt_shell(stdout=False, stderr=True)

extra = snakemake.params.get("extra", "")
exclude_flag = snakemake.params.get("exclude", True)
if exclude_flag:
    extra += " --exclude"

temp_r1 = snakemake.output.r1.removesuffix(".gz")
temp_r2 = snakemake.output.r2.removesuffix(".gz")

shell(
    "("
    " extract_kraken_reads.py"
    " -k {snakemake.input.kraken_output} -r {snakemake.input.kraken_report}"
    " -s {snakemake.input.r1} -s2 {snakemake.input.r2} -o {temp_r1} -o2 {temp_r2}"
    " -t {snakemake.params.taxid} {extra} --fastq-output > {snakemake.output.std_out}"
    " &&"
    " pigz {temp_r1} -9 -c -p {snakemake.threads} > {snakemake.output.r1}"
    " && "
    " pigz {temp_r2} -9 -c -p {snakemake.threads} > {snakemake.output.r2}"
    " ) {log}"
)
