import sys, traceback
import argparse
import re
import logging
import urllib
import time
import ijson
from datetime import datetime, timedelta

from nuclia import sdk
from nucliadb_sdk.v2.exceptions import ConflictError
import configuration

from validator import validate

from collections import deque
from statistics import mean



logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s:%(asctime)s:%(name)s:%(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("nuclia loader")

LANGUAGES = {'english': 'en',
             'korean': 'kr',
             'vietnamese': 'vi',
             'burmese': 'my',
             'tibetan': 'bo',
             'khmer': 'km',
             'uyghur': 'ug',
             'mandarin': 'zh-cn',
             'cantonese': 'zh-yue',
             'lao': 'lo',
             'indonesian': 'id',
             'bengali': 'bn',
             'malay': 'ms-zsm',
             'thai': 'th'
             }

LANGUAGE_LABELS = {'burmese': "Burmese",
                   'cantonese': "Cantonese",
                   'english': "English RFA",
                   'khmer': "Khmer",
                   'korean': "Korean",
                   'lao': "Lao",
                   'mandarin': "Mandarin",
                   'tibetan': "Tibetan",
                   'uyghur': "Uyghur",
                   'vietnamese': "Vietnamese",
                   'bengali': "Bengali",
                   'english-benar': "English BenarNews",
                   'indonesian': "Indonesian",
                   'malay': "Malay",
                   'thai': "Thai"
                   }

#Globals
FAKE_IT = False #global override for debugging and not actually uploading.
KB = None #set during argparse
API_KEY = None #set during argparse

def process_args():
    parser = argparse.ArgumentParser(description="""Load nuclia with a knowledgebox name and json file from plone export.
                                                 adding an --id argument will search the json file for a record with a
                                                 matching "@id" and only upload that record.
                                                 Note only 'story' types are expected""",
                                     usage="""usage: loader.py <knowledgebox> <filename> 
                                                     --id=<id> --resume_at=<index>
                                                     --max=number
                                                     -v"""
                                     )

    parser.add_argument("knowledgebox",
                        help="language name for knowledgebox."
                             f"supported: {VALID_KNOWLEDGEBOXES}",
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
                        help="upload only a single ID from file",
                        )
    parser.add_argument("--max",
                        type=int,
                        help="max number to upload from file.  Program will exit after uploading 'max' items",
                        )

    parser.add_argument("-v", "--verbose",
                        help="turn on debug",
                        action="store_true")

    parser.add_argument("--fake-it",
                        help="do everything except upload something.",
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
    upload_errors = {}

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
        logger.debug("starting upload")
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

            try:
                load_one(item)
            except ConflictError as e:
                logger.error(f"{item['UID']} already exists.  Maybe we should PATCH?")
                if 'ConflictError' not in upload_errors:
                    upload_errors['ConflictError'] = []
                upload_errors['ConflictError'].append(f"{item['UID']}, {item['@id']}")
            except Exception as e:
                logger.error(e, exc_info=True)
                exception_name = e.__class__.__name__
                if exception_name not in upload_errors:
                    upload_errors[exception_name] = []
                ex_type, ex, tb = sys.exc_info()
                upload_errors[exception_name].append(f"{item['UID']}, {item['@id']} : {traceback.print_tb(tb)}")

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



    # output the upload errors to stderr:
    print(f"{upload_errors}", file=sys.stderr)

def load_id(item_id, filename):
    """ given a specific ID from the plone export file,
        find that ID in the json export and only upload that specific one.
    """
    logger.debug(f"searching for item[@id]={item_id}")
    with open(filename, 'r') as filep:

        # stream it from json into objects one item at a time
        objects = ijson.items(filep, 'item')
        found = False
        for item in objects:
            if item.get('@id') == item_id:
                found = True
                item = preprocess_item(item)

                try:
                    load_one(item)
                except ConflictError as e:
                    logger.error(f"{item['UID']} already exists.  Maybe we should PATCH?")
                except Exception as e:
                    raise

                break

        if not found:
            logger.warning(f"id {item_id} not found in {filename}")


def load_one(item):
    # The slug is your own unique id (so the Plone uid is probably a good one in your case),
    # it will allow you to access the created resource without having to store locally
    # the corresponding Nuclia-specific unique id.
    #

    uri = f"{configuration.cloud_endpoint}/kb/{KB}"
    logger.info(f"adding resource for {item['@id']}, language {item['language']['token']}")
    res = sdk.NucliaResource()
    logger.debug(f"""
                     title = {item['title']}
                     slug = {item['UID']}
                     thumbnail = {item['thumbnail']}
                     created = {item['effective']}
                  """)
    if not FAKE_IT:
        res.create(
            url=uri,
            api_key=API_KEY,
            title=item['title'],
            slug=item['UID'],
            metadata={
                "language": item['language']['token'],
            },
            usermetadata={
                "classifications": [
                    {"labelset": "Language Service", "label": item['language_service']},
                ],
            },
            origin={
                "url": item['@id'],
                "tags": item['subjects'],
                "created": item['effective'],
                "modified": item['modified'],
                "metadata": {"thumbnail": item['thumbnail']}
            },
            summary=item['description'],
            texts={
                "body": {
                    "body": item['text']['data'],
                    "format": "HTML",
                }
            },
        )
    else:
        logger.warning("Faked request - upload did not occur")


def preprocess_item(item):
    # fix the ID, so it points to a published resource, not a test or dev uri
    rfa_pattern = ".*\.rfaweb.org"
    item['@id'] = re.sub(rfa_pattern, "https://www.rfa.org", item['@id'])
    benar_pattern = "https://.*\.benarnews.org"
    item['@id'] = re.sub(benar_pattern, "https://www.benarnews.org", item['@id'])

    # set description to None if it's blank:
    if not item['description'] or item['description'].isspace():
        item['description'] = None

    # clean the whitespace crap out of subjects:
    item['subjects'] = list([tag for tag in item['subjects'] if (tag and not tag.isspace())])

    # language must be inferred from URL
    parsed_url = urllib.parse.urlparse(item['@id'])
    language = parsed_url.path.split('/')[1]
    language_code = LANGUAGES.get(language, "en")

    item['language'] = {'title': language.capitalize(), 'token': language_code}

    item['language_service'] = LANGUAGE_LABELS.get(language, 'unknown')
    if language == 'english' and 'benar' in parsed_url.netloc:
        item['language_service'] = "English BenarNews"

    # Some stories have no text!
    if item['text'] is None:
        item['text'] = {"data": "",
                        "content-type": "text/html"
                        }

    #set the thumbnail URL:
    if item['featured_image'] is not None:
        item['thumbnail'] = item['featured_image']['@id'] + "/@@images/image/thumb"
        item['thumbnail'] = re.sub(rfa_pattern, "https://www.rfa.org", item['thumbnail'])
        item['thumbnail'] = re.sub(benar_pattern, "https://www.benarnews.org", item['thumbnail'])
    else:
        item['thumbnail'] = None

    return item


if __name__ == "__main__":
    args = process_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("debug on")

    logger.debug(f"using {args.knowledgebox} knowledgebox")
    (KB, API_KEY) = configuration.get_kb_config(args.knowledgebox)

    if args.fake_it:
        FAKE_IT = True  #global

    if args.id is not None:
        load_id(args.id, args.filename)
    else:
        load_file(args.filename, args.resume_at, args.max)


