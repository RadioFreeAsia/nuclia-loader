import argparse
import logging
import requests

from nuclia import sdk
from nucliadb_models.search import SearchRequest
from configuration import API_KEY
from configuration import KB
from configuration import cloud_endpoint

URI = f"{cloud_endpoint}/kb/{KB}"

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s:%(asctime)s:%(name)s:%(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("nuclia label editor")

#all vietnamese up to (not including)
# https://viedevview.rfaweb.org/vietnamese/HumanRights/Vietnam_government_tight_control_over_media_p2_TMi-20070131.html
# need to have the labelset re-written.


def process_args():
    parser = argparse.ArgumentParser(description="""update all labels from labelset 'language-service' to 'Language Service'
     or set an individual resource by slug or resource id to the new label
     additionally delete the old 'label-service' label if it exists on the resource""",
                                     usage=f"usage: {__name__}.py --slug slug --rid resource_id")

    parser.add_argument("--slug",
                        help="slug of resource to change label on",
                        )

    parser.add_argument("--rid",
                        help="resource id of resource to change label on",
                        )

    parser.add_argument("-v", "--verbose",
                        help="turn on debug",
                        action="store_true")

    parsed_args = parser.parse_args()

    return parsed_args


def find_labels_with_sdk():
    kb = sdk.NucliaKB()
    filter = "/l/language-service"
    searchReq = SearchRequest(filters=[filter])
    results = kb.search.search(url=URI, api_key=API_KEY, query=searchReq)

    return [x for x in results.resources.values()]


def edit_all_labels():
    resources_to_edit = find_labels_with_sdk()
    logger.info(f"found {len(resources_to_edit)} items to edit")
    for res in resources_to_edit:
        logger.info(f"editing resource {res.id}")
        edit_label(rid=res.id)


def edit_label(rid: str = None, slug: str = None):

    """
    :param rid: the resource id of the resource
    :param slug: the slug of the resource
    :param label: the "Language Service" label.
    :return:
    """

    #get the old usermedata:
    if rid is not None:
        res = sdk.NucliaResource().get(url=URI,
                                       api_key=API_KEY,
                                       rid=rid,)
    elif slug is not None:
        res = sdk.NucliaResource().get(url=URI,
                                       api_key=API_KEY,
                                       slug=slug,)
    else:
        raise ValueError("Must provide either rid or slug")

    rid = res.id
    metadata = res.usermetadata
    for classification in metadata.classifications:
        if classification.labelset == "language-service":
            classification.labelset = "Language Service"

    logger.info(f"fixing f{rid}")
    sdk.NucliaResource().update(url=URI,
                                api_key=API_KEY,
                                rid=rid,
                                usermetadata=res.usermetadata)


if __name__ == "__main__":
    args = process_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("debug on")

    if args.slug:
        edit_label(slug=args.slug)
    elif args.rid:
        edit_label(rid=args.rid)
    else:
        edit_all_labels()
