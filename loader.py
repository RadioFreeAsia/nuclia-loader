
import argparse

import ijson
from nuclia import sdk
from configuration import API_KEY
from configuration import KB
from configuration import cloud_endpoint

def process_args():
    parser = argparse.ArgumentParser(description="Load nuclia with a json file from plone export."
                                                 "Note only 'story' types are expected",
                                     usage="usage: loader.py <filename>")
    parser.add_argument("filename",
                        help="filename of json export")

    parsed_args = parser.parse_args()

    return parsed_args


def load_all(filename):
    with open(filename, 'r') as filep:

        # stream it from json into objects one item at a time
        objects = ijson.items(filep, 'item')

        for item in objects:
            load_one(item)

def load_one(item):
    import pdb; pdb.set_trace()
    # The slug is your own unique id (so the Plone uid is probably a good one in your case),
    # it will allow you to access the created resource without having to store locally
    # the corresponding Nuclia-specific unique id.
    #

    uri = f"{cloud_endpoint}/kb/{KB}"
    res = sdk.NucliaResource()
    res.create(
        url=uri,
        api_key=API_KEY,
        title=item['title'],
        slug=item['UID'],
        origin={
            "url": item['@id'],
            "tags": [tag for tag in item['subjects'] if (tag and not tag.isspace())]
        },
        summary=item['description'],
        texts={
            "body": {
                "body": "<the text body>",
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
    load_all(args.filename)
