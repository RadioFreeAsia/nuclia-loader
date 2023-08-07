
import argparse
import re
import logging
import urllib

import ijson
from nuclia import sdk
from configuration import API_KEY
from configuration import KB
from configuration import cloud_endpoint

from validator import validate

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


def process_args():
    parser = argparse.ArgumentParser(description="Load nuclia with a json file from plone export."
                                                 "Note only 'story' types are expected",
                                     usage="usage: loader.py <filename>")
    parser.add_argument("filename",
                        help="filename of json export")

    parser.add_argument("-v", "--verbose",
                        help="turn on debug")

    parsed_args = parser.parse_args()

    return parsed_args


def load_all(filename):

    (objects, unpublished, errors) = validate(filename)
    total_published = objects - unpublished
    count = 0
    with open(filename, 'r') as filep:

        # stream it from json into objects one item at a time
        objects = ijson.items(filep, 'item')

        for item in objects:

            if "unexported_paths" in item and "@id" not in item:
                # it's the error report at the end of the export - ignore it.
                continue

            # Skip unpublished content.
            if item.get('review_state') != "published":
                logger.info(f"skipping: review state '{item.get('review_state')}' for {item['@id']} ")
                continue

            # fix the ID, so it points to a published resource, not a test or dev uri
            pattern = ".*\.rfaweb.org"
            item['@id'] = re.sub(pattern, "https://www.rfa.org", item['@id'])
            pattern = "https://.*\.benarnews.org"
            item['@id'] = re.sub(pattern, "https://www.benarnews.org", item['@id'])

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

            try:
                load_one(item)
            except Exception as e:
                logger.error(e, exc_info=True)

            count += 1
            logger.info(f"{count/len(total_published):.1%} complete | {count} of {total_published} ")

def load_one(item):
    # The slug is your own unique id (so the Plone uid is probably a good one in your case),
    # it will allow you to access the created resource without having to store locally
    # the corresponding Nuclia-specific unique id.
    #

    uri = f"{cloud_endpoint}/kb/{KB}"
    logger.info(f"adding resource for {item['@id']}, language {item['language']['token']}")
    res = sdk.NucliaResource()
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
        },
        summary=item['description'],
        texts={
            "body": {
                "body": item['text']['data'],
                "format": "HTML",
            }
        },
    )

    # Using "tags" to store the subjects is fine, but you also can decide to use Nuclia labels,
    # like this:

    # usermetadata={
    #     "classifications": [
    #         {"labelset": "subjects", "label": "<Topic 1>"},
    #         {"labelset": "subjects", "label": "<Topic 2>"},
    #     ],
    # }


if __name__ == "__main__":
    args = process_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("debug on")

    load_all(args.filename)
