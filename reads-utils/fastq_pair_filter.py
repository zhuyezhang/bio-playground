#!/usr/bin/python
"""
%prog [options] pair_1.fastq pair_2.fastq

filter reads from paired fastq so that no unmatching reads remain.
output files are pair_1.fastq.trim and pair_2.fastq.trim
see: http://hackmap.blogspot.com/2010/09/filtering-paired-end-reads-high.html
"""
from subprocess import Popen, PIPE
import sys

FASTX_CLIPPER="fastx_clipper"
FASTQ_QUALITY_TRIMMER="fastq_quality_trimmer"
def gen_pairs(fha, fhb, min_len, fastq):
    def gen_headers(fastq):
        fq = open(fastq)
        r = True
        while r:
            r = fq.readline().rstrip()[:-2]
            fq.readline()
            fq.readline()
            fq.readline()
            yield r

    aread, bread = fha.readline, fhb.readline
    get_a = lambda: [aread().rstrip("\r\n") for i in range(4)]
    get_b = lambda: [bread().rstrip("\r\n") for i in range(4)]

    ah, bh = None, None
    header_gen = gen_headers(fastq)
    for header in header_gen:
        a = get_a()
        ah = a[0][:-2]
        b = get_b()
        bh = b[0][:-2]
        if bh != header:
            while ah != bh:
                a = get_a()
                ah = a[0][:-2]
            while header != bh:
                header = header_gen.next()
        if ah != header:
            while ah != bh:
                b = get_b()
                bh = b[0][:-2]
            while header != bh:
                header = header_gen.next()

        assert ah == bh
        if len(a[1]) < min_len or len(b[1]) < min_len: continue
        yield a, b

def main(adaptors, M, t, min_len, fastqs, sanger=False):
    cmds = []
    for fastq in fastqs:
        trim_cmd = "%s -t %i -l 0" % (FASTQ_QUALITY_TRIMMER, t)
        if sanger: trim_cmd += " -Q 33"

        clip_cmds = []
        for i, a in enumerate(adaptors):
            clip_cmds.append("%s -a %s -M %i %s" \
                 % (FASTX_CLIPPER, a, M, "-Q 33" if sanger else ""))

        cmds.append(" | ".join(clip_cmds + [trim_cmd]) + " < %s " % fastq)
        print "[running]:", cmds[-1]
    procs = [Popen(cmd, stdout=PIPE, shell=True) for cmd in cmds]


    trima = open("%s.trim" % fastqs[0], 'w')
    trimb = open("%s.trim" % fastqs[1], 'w')
    print >>sys.stderr, "writing %s and %s" % (trima.name, trimb.name)

    # no temporary file, just read from stdouts.
    for ra, rb in gen_pairs(procs[0].stdout, procs[1].stdout, min_len,
            fastqs[0]):
        print >>trima, "\n".join(ra)
        print >>trimb, "\n".join(rb)

    returncode = 0
    for p in procs:
        p.wait()
        returncode |= p.returncode
    if returncode != 0:
        print >>sys.stderr, "ERROR: non-zero returncode from fastx toolkit"
        sys.exit(returncode)

if __name__ == "__main__":
    import optparse
    p = optparse.OptionParser(__doc__)
    p.add_option("-a", dest="a", help="adaptor sequence to clip seperate multiples with ','", default="")

    p.add_option("-M", dest="M", help="require minimum adapter alignment length of N."
               " If less than N nucleotides aligned with the adapter - don't clip it",
                 default=4, type='int')

    p.add_option("-t", dest="t", help="Quality threshold - nucleotides with lower"
                          " quality will be trimmed (from the end of the sequence ",
                 type='int', default=0)

    p.add_option("-l", dest="l", help="Minimum length - sequences shorter than this (after trimming)"
                                   "will be discarded. Default = 0 = no minimum length.",
                type="int", default=0)
    p.add_option("--sanger", dest="sanger", help="quality scores are ascii 33 sanger encoded (default is 64)", action="store_true")

    opts, fastqs = p.parse_args()
    fastqs[-1] = fastqs[-1].rstrip()
    if not (fastqs and len(fastqs)) == 2:
        sys.exit(p.print_help())

    adaptors = [ad.strip() for ad in opts.a.split(",") if ad.strip()]
    main(adaptors, opts.M, opts.t, opts.l, fastqs, opts.sanger)
