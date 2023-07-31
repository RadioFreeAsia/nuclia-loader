from nuclia import sdk
from configuration import API_KEY
from configuration import KB
from configuration import cloud_endpoint

uri = f"{cloud_endpoint}/kb/{KB}"

res = sdk.NucliaResource()
res.create(
    url=uri,
    api_key=API_KEY,
    slug="<uuid-from-plone>",
    origin={
        "url": "<the-page-url>",
        "tags": ["<Topic 1>", "<Topic 2>"]
    },
    summary="<the-description>",
    texts={
        "body": {
            "body": "<the text body>",
            "format": "PLAIN",
        }
    },
)

# The slug is your own unique id (so the Plone uid is probably a good one in your case),
# it will allow you to access the created resource without having to store locally
# the corresponding Nuclia-specific unique id.
#
# Using "tags" to store the subjects is fine, but you also can decide to use Nuclia labels,
# like this:

usermetadata={
    "classifications": [
        {"labelset": "subjects", "label": "<Topic 1>"},
        {"labelset": "subjects", "label": "<Topic 2>"},
    ],
}