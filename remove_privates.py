"""Burmese and Cantonese were fully uploaded, and we didn't filter
the objects in a non-published state.

This goes through and finds those items, and deletes them.

"""
import argparse
import logging
import time
import ijson

from nuclia import sdk
from nucliadb_sdk.v2 import exceptions
from configuration import API_KEY
from configuration import KB
from configuration import cloud_endpoint
from validator import validate

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s:%(asctime)s:%(name)s:%(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger("private item deleter")


def process_args():
    parser = argparse.ArgumentParser(description="""Provide a plone export file.
    walk through all objects, and delete resources that are found to be non-published.
    """,
                                     usage="usage: remove_privates.py <filename>")
    parser.add_argument("filename",
                        help="filename of json export",
                        )

    parser.add_argument("-v", "--verbose",
                        help="turn on debug",
                        action="store_true")

    parsed_args = parser.parse_args()

    return parsed_args


def remove_privates(filename):

    logger.info(f"counting objects in {filename}")
    (total_objects, unpublished, errors) = validate(filename)
    logger.info(f"{unpublished} unpublished objects out of {total_objects} objects")

    with open(filename, 'r') as filep:
        # stream it from json into objects one item at a time
        objects = ijson.items(filep, 'item')
        uri = f"{cloud_endpoint}/kb/{KB}"
        res = sdk.NucliaResource()

        deleted = 0
        processed = 0
        not_found = 0

        tstart = time.monotonic()
        average_duration = 0.0001  # a guess
        for item in objects:
            # If the item is not public...
            if "@id" in item and item.get('review_state') != "published":
                logger.info(f"removing '{item.get('review_state')}' item {item['@id']} {item['UID']} ")

                try:
                    res.delete(url=uri,
                               api_key=API_KEY,
                               slug=item['UID'])
                    pass
                except exceptions.NotFoundError:
                    logger.warning(f"slug {item['UID']} not found.")
                    not_found += 1
                else:
                    deleted += 1

            processed += 1

            # occasional logging:
            if processed % 50 == 0:
                remaining_time = (total_objects-processed) * average_duration
                logger.info(f"{processed/total_objects:.1%} ETA: {remaining_time:.2} seconds")

            # figure out the estimated time to completion.
            tend = time.monotonic()
            duration = tend-tstart
            average_duration = average_duration + ((duration-average_duration)/processed)
            tstart = tend  # next loop iteration start time is this loop iteration end time.

        logger.info(f"complete.  Deleted {deleted} objects out of {unpublished} with {not_found} not found")

if __name__ == "__main__":
    args = process_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("debug on")

    remove_privates(args.filename)

