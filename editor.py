import argparse
import logging
import urllib
import time
import ijson
from datetime import datetime, timedelta

from nuclia import sdk
import configuration

from validator import validate

from collections import deque
from statistics import mean
from pprint import pformat
from loader import preprocess_item

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s:%(asctime)s:%(name)s:%(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("nuclia origin editor")

#Globals
FAKE_IT = False #global override for debugging and not actually uploading.
KB = None #set during argparse
API_KEY = None #set during argparse

def process_args():
    parser = argparse.ArgumentParser(description="""Update the creation date metadata by editing existing records
                                                   to place the correct 'effective' date in""",
                                     usage="""usage: date_editor.py <knowledgebox> <filename> 
                                              [--id=<id> | --slug=<slug>] 
                                              [--max=N] [--resume_at=N]"""
                                     )
    parser.add_argument("knowledgebox",
                        help="language name for knowledgebox."
                             f"supported: {configuration.kb_config.keys()}",
                        )

    parser.add_argument("filename",
                        help="filename of json export",
                        )

    parser.add_argument("--resume_at",
                        help="resume at a specific index, skipping objects up until that point",
                        type=int,
                        required=False,
                        default=0,
                        )

    parser.add_argument("--id",
                        help="find a item by @id from input file and edit that resource's date",
                        )

    parser.add_argument("--slug", "--uid",
                        help="find a item by UID from input file and edit that resource's date"
                        )

    parser.add_argument("--max",
                        type=int,
                        help="max number to consume from file.  Program will exit after patching 'max' items",
                        default=None
                        )

    parser.add_argument("--fake-it",
                        help="do everything except posting to url.",
                        action="store_true")

    parser.add_argument("-v", "--verbose",
                        help="turn on debug",
                        action="store_true")

    parsed_args = parser.parse_args()

    return parsed_args


def load_file(filename, resume_at=0, max_uploads=None):

    logger.debug(f"counting objects in {filename}")
    (objects, unpublished, errors) = validate(filename)
    total_published = objects - unpublished
    logger.debug(f"{objects} objects | {total_published} published")
    count = 0
    average_duration = 0.0001  # a guess

    last_runtimes = deque()
    window_average = 10

    if resume_at < 0:
        resume_at = 0
    if max_uploads is not None and resume_at:
        logger.error("combining max and resume_at is not supported")
        raise ValueError

    target_uploads = total_published
    if max_uploads is not None:
        logger.info(f"Maximum number of uploads set to {max_uploads}")
        target_uploads = max_uploads

    with open(filename, 'r') as filep:

        # stream it from json into objects one item at a time
        objects = ijson.items(filep, 'item')
        logger.debug("Starting Edits")
        tstart = time.monotonic()
        for item in objects:

            logger.debug(f"processing object at {count}")
            if "unexported_paths" in item and "@id" not in item:
                # it's the error report at the end of the export - ignore it.
                continue

            # Skip unpublished content.
            if item.get('review_state') != "published":
                logger.info(f"skipping: review state '{item.get('review_state')}' for {item['@id']} ")
                continue

            # Skip objects until 'resume at' is met:
            if count < resume_at:
                logger.info(f"{item['title']} |  skipping up to {count}/{resume_at}")
                count += 1
                continue

            if max_uploads is not None and count >= max_uploads:
                logger.info("maximum uploads reached.  Exiting.")
                break

            item = preprocess_item(item)
            slug = item['UID']
            new_data = {
                'origin': {
                    "url": item['@id'],
                    "tags": item['subjects'],
                    "created": item['effective'],
                    "modified": item['modified'],
                },
                "extra": {
                    "metadata": {"thumbnail": item['thumbnail']}
                }
            }
            try:
                edit_one(slug=slug, data=new_data)
            except Exception as e:
                logger.error(e, exc_info=True)

            count += 1
            logger.info(f"{count} of {target_uploads} | {count/target_uploads:.1%} complete")

            #print running average rate:
            if len(last_runtimes) > window_average:
                last_runtimes.popleft()
                rate = mean(last_runtimes)
            else:
                rate = 9999.9


            # figure out the estimated time to completion.
            remaining_seconds = (target_uploads - count) * average_duration
            delta = timedelta(seconds=int(remaining_seconds))
            (h, m, s) = f"{delta}".split(':')
            logger.info(f"rate: {rate:.4f} items/second ETA: {h}h {m}m {s}s |" +
                        f"{(datetime.now()+timedelta(seconds=remaining_seconds)).strftime('%Y-%m-%d %X')}")

            tend = time.monotonic()
            duration = tend-tstart
            last_runtimes.append(1/duration)

            average_duration = average_duration + ((duration-average_duration)/(count-resume_at))

            # leave this as the last line of the loop - always
            tstart = tend  # next loop iteration start time is this loop iteration end time.


def edit_id(item_id=None, item_uid=None, filename=None):
    """ given a specific ID or UID from the plone export file,
        find that ID in the json export and only edit that single date.
    """
    if filename is None:
        raise FileNotFoundError("provide a filename.")

    logger.debug(f"searching for item[@id]={item_id} or item[UID]={item_uid}")
    with open(filename, 'r') as filep:

        # stream it from json into objects one item at a time
        objects = ijson.items(filep, 'item')
        found = False
        for item in objects:
            if item.get('@id') == item_id or item.get('UID') == item_uid:
                found = True
                logger.debug(f"found slug {item['UID']}:  {item['title']}")
                item = preprocess_item(item)
                slug = item['UID']
                new_data = {
                    'origin': {
                        "url": item['@id'],
                        "tags": item['subjects'],
                        "created": item['effective'],
                        "modified": item['modified'],
                    },
                    "extra": {
                        "metadata": {"thumbnail": item['thumbnail']}
                    }
                }

                try:
                    edit_one(slug, new_data)
                except Exception as e:
                    logger.error(e, exc_info=True)

                break

        if not found:
            logger.warning(f"id {item_id} / uid {item_uid} not found in {filename}")


def edit_one(slug, data):
    """edit the resource by 'slug', replacing with new data 'data'
       data must be a key-value pair of arguments & data that can be provided to 'update_resource'
       https://docs.nuclia.dev/docs/docs/nucliadb/python_nucliadb_sdk#update_resource """

    uri = f"{configuration.cloud_endpoint}/kb/{KB}"
    logger.info(f"editing resource {slug}")
    res = sdk.NucliaResource()
    logger.debug(f"""
                     slug = {slug}
                     data = {pformat(data)}
                  """)
    if not FAKE_IT:
        res.update(url=uri,
                   api_key=API_KEY,
                   slug=slug,
                   **data)
    else:
        logger.warning("Faked request - upload did not occur")


if __name__ == "__main__":
    args = process_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("debug on")

    if args.fake_it:
        FAKE_IT = True  #global

    logger.debug(f"using {args.knowledgebox} knowledgebox")
    (KB, API_KEY) = configuration.get_kb_config(args.knowledgebox)

    if args.id or args.slug is not None:
        edit_id(item_id=args.id, item_uid=args.slug, filename=args.filename)
    else:
        load_file(args.filename, args.resume_at, args.max)
