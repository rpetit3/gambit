# GAMBIT

[![Build Status](https://github.com/jlumpe/gambit/actions/workflows/ci.yml/badge.svg)](https://github.com/jlumpe/gambit/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/gambit-genomics/badge/?version=latest)](https://gambit-genomics.readthedocs.io/en/latest/?badge=latest)
[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg?style=flat)](http://bioconda.github.io/recipes/gambit/README.html)

GAMBIT (Genomic Approximation Method for Bacterial Identification and Tracking) is a tool for rapid taxonomic identification of microbial pathogens.
It uses an extremely efficient genomic distance metric along with a curated database of approximately 50,000 reference genomes (derived from NCBI
[RefSeq](https://www.ncbi.nlm.nih.gov/refseq/)) to identify unknown bacterial genomes within seconds.

Developed by Jared Lumpe in collaboration with the [Nevada State Public Health Lab](https://med.unr.edu/nsphl),
the [Alameda County Public Health Lab](https://acphd.org/public-health-lab/),
and the David Hess lab at Santa Clara University.

Preprint available [here](https://www.biorxiv.org/content/10.1101/2022.06.14.496173v1). See
[jlumpe/gambit-publication](https://github.com/jlumpe/gambit-publication) for a reproducible
workflow to generate all analyses and figures in the paper.

See the [documentation](https://gambit-genomics.readthedocs.io/en/latest) for more
detailed information on the tool and how to use it.


### Contact

Please contact Jared Lumpe at [jared@jaredlumpe.com](mailto:jared@jaredlumpe.com).


## Installation

Install the Python library from Bioconda:

```
conda install -c bioconda gambit
```

Then download the reference database files and place them in a directory of your choice:

* [gambit-refseq-curated-1.0.gdb](https://storage.googleapis.com/jlumpe-gambit/public/databases/refseq-curated/1.0/gambit-refseq-curated-1.0.gdb)
* [gambit-refseq-curated-1.0.gs](https://storage.googleapis.com/jlumpe-gambit/public/databases/refseq-curated/1.0/gambit-refseq-curated-1.0.gs)


## Usage

    gambit [-d /path/to/database/] query [-o results.csv] genome1.fasta genome2.fasta ...

Positional arguments are one or more FASTA files containing query genome assemblies. You must
provide the path to the directory containing the database files using either the `-d` option
(*before* the `query` subcommand) or by setting the `GAMBIT_DB_PATH` environment variable.

See the documentation for additional details on the command line interface and description of the output.
