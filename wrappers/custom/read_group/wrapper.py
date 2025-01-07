import gzip
import sys

sys.stderr = open(snakemake.log[0], "w")


class NotIlluminaHeader(Exception):
    """Exception raised when the input file is not illumina header"""


class NotBGIHeader(Exception):
    """Exception raised when the input file is not BGI header"""


class EmptyFastq(Exception):
    """Exception raised when the input FASTQ is empty"""

def _load_header(in_fastq: str) -> str:
    with gzip.open(in_fastq, "rt") as fastq_file:
        header = fastq_file.readline()

        if len(header) == 0:
            raise EmptyFastq("input FASTQ %s is empty" % header)
        return header


def _parse_illumina_header(header: str) -> tuple[str, str]:
    # Example: @AP2-11:127:H53WFDMXX:1:1101:1271:1031 1:N:0:GGACTCCT+GTAAGGAG
    segments = header.split(":")
    if len(segments) >= 3:
        flowcell = segments[2]
        platform = "ILLUMINA"
        return flowcell, platform
    raise NotIlluminaHeader("input FASTQ %s is not illumina header" % header)


def _normalize_bgi_header_formats(header: str) -> str:
    segments = header.split(" ")
    if len(segments) >= 2:
        # Example: @ERR2618717.1 CL200036657L2C001R002_104504 length=150
        bgi_header = segments[1]
    else:
        # genuine BGI header, remove @
        bgi_header = segments[0][1:]
    return bgi_header.upper()


def _parse_bgi_header(bgi_header: str) -> tuple[str, str]:
    # Examples: CL200036657L2C001R002_104504 or V300038198L4C001R0010019425/1
    if bgi_header[0] == "C":
        platform = "BGISEQ-500"
        flowcell = bgi_header[:13]
        return platform, flowcell
    elif bgi_header[0] == "V":
        platform = "MGISEQ-2000"
        flowcell = bgi_header[:12]
        return platform, flowcell
    else:
        raise NotBGIHeader("input FASTQ %s is not BGI header" % bgi_header)


def _parse_flowcell_platform_info(in_fastq: str) -> tuple[str, str]:
    header = _load_header(in_fastq)
    try:
        flowcell, platform = _parse_illumina_header(header)
    except NotIlluminaHeader:
        try:
            bgi_header = _normalize_bgi_header_formats(header)
            flowcell, platform = _parse_bgi_header(bgi_header)
        except NotBGIHeader:
            flowcell, platform = "unknown", "unknown"
    except EmptyFastq:
        flowcell, platform = "unknown", "unknown"
    return flowcell, platform


def _infer_read_group(flowcell: str, platform: str, sample_id: str) -> str:
    readgroup = ""
    readgroup += "@RG\t"
    readgroup += "ID:%s.%s\t" % (flowcell, sample_id)
    readgroup += "LB:%s.%s\t" % (flowcell, sample_id)
    readgroup += "PL:%s\t" % platform
    readgroup += "SM:%s" % sample_id
    return readgroup


def save_read_group(*, in_fastq: str, out_txt: str, sample_id: str):
    flowcell, platform = _parse_flowcell_platform_info(in_fastq)
    readgroup = _infer_read_group(flowcell, platform, sample_id)

    with open(out_txt, "wt") as out_file:
        out_file.write(readgroup + "\n")


if __name__ == "__main__":
    save_read_group(
        in_fastq=snakemake.input[0], out_txt=snakemake.output.read_group, sample_id=snakemake.params.sample_id
    )
