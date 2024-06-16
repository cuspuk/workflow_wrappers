import os
import tempfile

from snakemake.shell import shell

log = snakemake.log_fmt_shell(stdout=False, stderr=True)

PRESUMED_SUFFIX = "_R1.fastq.gz"
if not snakemake.input.r1.endswith(PRESUMED_SUFFIX):
    raise ValueError(f"{snakemake.input.r1} does not ends with {PRESUMED_SUFFIX}")

sample_name = os.path.basename(snakemake.input.r1).replace(PRESUMED_SUFFIX, "")

with tempfile.TemporaryDirectory() as tmpdir:
    shell(
        "("
        " R1_IN={snakemake.input.r1};"
        " R2_IN={snakemake.input.r2};"
        " for INDEX in {snakemake.params.indices}; do"
        "  REF=`basename $INDEX`;"
        "  REF_DIR={tmpdir}/$REF;"
        "  mkdir -p $REF_DIR;"
        "  BAM_OUT=$REF_DIR/{sample_name}_out.bam;"
        "  R1_OUT=$REF_DIR/{sample_name}_R1.fastq.gz;"
        "  R2_OUT=$REF_DIR/{sample_name}_R2.fastq.gz;"
        "  bwa mem "
        "   -t {snakemake.threads}"
        "   $INDEX"
        "   $R1_IN"
        "   $R2_IN"
        "  |"
        "  samtools view"
        "   -o $BAM_OUT;"
        "  samtools collate"
        "   -u -O $BAM_OUT"
        "  |"
        "  samtools fastq"
        "   -1 $R1_OUT"
        "   -2 $R2_OUT"
        "   {snakemake.params.keep_param}"
        "   -0 /dev/null"
        "   -s /dev/null"
        "   {snakemake.params.fastq_param};"
        "  R1_IN=$R1_OUT;"
        "  R2_IN=$R2_OUT;"
        " done;"
        " mv $R1_OUT {snakemake.output.r1};"
        " mv $R2_OUT {snakemake.output.r2};"
        " ) {log}"
    )
