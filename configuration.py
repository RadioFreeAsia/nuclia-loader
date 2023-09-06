

# you must create your own 'keys_config.py" and add these strings
# but do not add 'keys_config.py' to a public repo - it's privileged information
import keys_confg as keys_config
from keys_confg import API_KEY, Account_UID


# these configuration options are public knowledge, and can be added to source control
cloud_endpoint = "https://europe-1.nuclia.cloud/api/v1"
REGION = "europe-1"

RadioFreeAsia_KB = "1194b6c4-fc68-4dcf-b969-49b96380bfe9"
Burmese_KB = "ab767fdf-280f-419f-88c3-ea3b95c2c944"
Uyghur_KB = "02e6b210-079c-496f-b5ed-e01a24ba5d1e"

KB = RadioFreeAsia_KB
VALID_KNOWLEDGEBOXES = ("RadioFreeAsia", "Burmese", "Uyghur")


def get_kb_config(knowledgebox):
    if knowledgebox not in VALID_KNOWLEDGEBOXES:
        logger.error(f"only {VALID_KNOWLEDGEBOXES} are supported")
        raise ValueError
    if knowledgebox == "RadioFreeAsia":
        KB = RadioFreeAsia_KB
        API_KEY = keys_config.McFadden_Owner_key
    if knowledgebox == "Burmese":
        KB = Burmese_KB
        API_KEY = keys_config.Burmese_Key
    if knowledgebox == "Uyghur":
        KB = Uyghur_KB
        API_KEY = keys_config.McFadden_Uyghur_Key

    return (KB, API_KEY)