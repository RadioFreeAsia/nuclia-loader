

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
Mandarin_KB = "39faac63-5ccc-435c-aba5-16eb2f68f502"
Bengali_KB = "61aa945d-2a33-4e76-8e45-0324140762f2"
Thai_KB = "18349f06-b7b2-45a2-854b-310d8bc9170d"
Cantonese_KB = "3b59c05d-7185-4857-9d55-54861c209d39"
Khmer_KB = "53490da5-a885-40b1-a6ad-707576fc61d6"
Korean_KB = "9ea12480-e911-4b91-9629-66d452103aa0"
Lao_KB = "e54a77c7-e59b-4a26-bc46-85d387a6670d"
Tibetan_KB = "b78d9d3b-effc-4f5e-b887-a8d2b06375b8"
Vietnamese_KB = "7bcc1511-3fce-4747-91f5-dfee8d82913b"
Indonesian_KB = "013ee2f8-3247-418c-9af8-2c2ec1bacfd1"
Malay_KB = "b0407bad-2f20-482b-99c0-cb225189a827"

kb_config = {"RadioFreeAsia": (RadioFreeAsia_KB, keys_config.McFadden_Owner_key),
             "Burmese": (Burmese_KB, keys_config.Burmese_Key),
             "Uyghur": (Uyghur_KB, keys_config.Uyghur_Key),
             "Mandarin": (Mandarin_KB, keys_config.Mandarin_Key),
             "Bengali": (Bengali_KB, keys_config.Bengali_Key),
             "Cantonese": (Cantonese_KB, keys_config.Cantonese_Key),
             "Indonesian": (Indonesian_KB, keys_config.Indonesian_Key),
             "Khmer": (Khmer_KB, keys_config.Khmer_Key),
             "Lao": (Lao_KB, keys_config.Lao_Key),
             "Vietnamese": (Vietnamese_KB, keys_config.Vietnamese_Key),
             "Malay": (Malay_KB, keys_config.Malay_Key),
             "Korean": (Korean_KB, keys_config.Korean_Key),
             "Tibetan": (Tibetan_KB, keys_config.Tibetan_Key),
             "Thai": (Thai_KB, keys_config.Thai_Key),
             }

def get_kb_config(knowledgebox):
    try:
        return kb_config[knowledgebox]
    except KeyError:
        logger.error(f"unknown Knowledgebox {knowledgebox}")
        raise ValueError

