
import os
import subprocess
import argparse

def get_parser():
    """ Process line arguments
    """

    ## Define parser functions and arguments
    parser = argparse.ArgumentParser(
        description="Python package to process electronic structure calculation data (e.g., continuum solvation free energy) and statistical mechanics data (e.g., NASA polynomials) from Gaussian16, Arkane and related software. "
    )
    parser.add_argument(
        "-d",
        "--docs",
        action="store_true",
        help="Open the documentation locally.",
    )
    parser.add_argument(
        "--compile-docs",
        action="store_true",
        help="Compile the documentation locally. Automatic if the documentation is not yet compiled.",
    )

    return parser

parser = get_parser()
args = parser.parse_args()
path="/".join(os.path.dirname(__file__).split("/")[:-1])
os.chmod('{}/docs/run.sh'.format(path), 0o755)
subprocess.check_call("{}/docs/run.sh {} {}".format(path,args.docs,args.compile_docs), shell=True)

