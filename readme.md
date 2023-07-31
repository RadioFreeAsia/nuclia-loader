
## Install


create python virtual environment in this directory:

    python3 -m venv venv

install required python packages:

    ./venv/bin/pip install -r requirements.txt

## Configure

create a file called 'keys_config.py' in this directory, and add your api key and account id.

    API_KEY = "API Key from Nuclia"
    Account_UID = "ACCOUNT UID FROM NUCLIA"

don't check this file into source control because it's private info.


## Run
   
    /venv/bin/python loader.py <json file>

   a sample plone export is in ./data/sample.json with a few items.

    ./venv/bin/python loader.py data/sample.json