"""
This loads a json data file exported from plone and:
counts the number of json items  - to manually validate a good export.
"""
import argparse
import ijson


def process_args():
    parser = argparse.ArgumentParser(description="Validate a plone export."
                                                 "Note only 'story' types are expected",
                                     usage="usage: validator.py <filename>")
    parser.add_argument("filename",
                        help="filename of json export")

    parser.add_argument("-v", "--verbose",
                        help="turn on debug")

    parsed_args = parser.parse_args()

    return parsed_args


def validate(filename):
    with open(filename, 'r') as filep:

        # stream it from json into objects one item at a time
        items = ijson.items(filep, 'item')
        objects = 0
        errors = 0
        unpublished = 0

        for item in items:
            if '@id' in item:
                objects += 1
                if item.get('review_state') != "published":
                    unpublished += 1
            else:
                errors = len(item['unexported_paths'])

    return (objects, unpublished, errors)


if __name__ == "__main__":
    args = process_args()

    (objects, unpublished, errors) = validate(args.filename)

    print(f"{args.filename}:  {objects} objects | {objects - unpublished} published | {errors} errors")