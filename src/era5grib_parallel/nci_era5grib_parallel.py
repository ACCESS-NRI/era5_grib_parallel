# Copyright 2024 ACCESS-NRI (https://www.access-nri.org.au/)
# See the top-level COPYRIGHT.txt file for details.
#
# SPDX-License-Identifier: Apache-2.0
#
# Created by: Chermelle Engel <Chermelle.Engel@anu.edu.au>


"""
Use CDO commands to set up era5 grib files for use by the nesting suite

The nesting suite expects grib files to be named like
    AINITIAL="$ROSE_DATA/era5grib/ec_grib_${FDATE}.t+000"
where FDATE is in YYYYmmddHHMM format

"""

from pathlib import Path
import argparse
from multiprocessing import Pool
import os
from datetime import timedelta
import pandas

from era5grib_parallel import cdo_era5grib

boolopt = {
    "True": True,
    "False": False,
}


def create_grib(START, outdir):
    """
    Function that creates one single GRIB file per date-time from the ERA5 archive

    Parameters
    ----------
    START : string
            The requested date to be repackaged in %Y-%m-%dT%H:%M:%S format
    outdir : Path
            The path for the output file to be written to

    Returns
    -------
    int
        The process id
    """

    # Create the grib file from the netcdf archive
    cdo_era5grib.repackage_grib(START, outdir)

    return os.getpid()


def main():
    """
    The main function that creates a worker pool and generates single GRIB files
    for requested date/times in parallel.

    Parameters
    ----------
    None.  The arguments are given via the command-line

    Returns
    -------
    None.  The GRIB file are written to the output directory
    """

    # Parse the command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start", required=True, type=pandas.to_datetime)
    parser.add_argument("--count", default=1, type=int)
    parser.add_argument("--freq", default=60 * 60, type=lambda x: int(x))
    args = parser.parse_args()

    # Create a list of the requested date/times
    all_dates = []
    sd = args.start
    start_date = sd.strftime("%Y%m%d%H%M")
    for i in range(args.count):
        cd = sd + timedelta(seconds=i * args.freq)
        cd_string = cd.strftime("%Y-%m-%dT%H:%M:%S")
        all_dates.append(cd_string)
    print(all_dates)

    # Farm out the date/times to 4 worker processes at time until done.
    with Pool(processes=4) as pool:
        # Select four dates to work on, then create the GRIB files in parallel
        for offset in range(0, len(all_dates) + 1, 4):
            subset_dates = []

            for i in range(offset, offset + 4):
                try:
                    subset_dates.append(all_dates[i])
                except:
                    pass

            # launching multiple evaluations asynchronously *may* use more processes
            multiple_results = [
                pool.apply_async(
                    create_grib,
                    (
                        dt,
                        args.output,
                    ),
                )
                for dt in subset_dates
            ]
            print([res.get(timeout=600) for res in multiple_results])

        print("For the moment, the pool remains available for more work")

    # exiting the 'with'-block has stopped the pool
    print("Now the pool is closed an no longer available")


if __name__ == "__main__":
    main()
