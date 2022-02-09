# echo ">>> Pulling Docker Python image"
# docker pull ibmfunctions/action-python-v3.7

# echo ">>> Install dependencies and create a virtual environment using Docker..."
# docker run --rm -v "$PWD:/tmp" ibmfunctions/action-python-v3.7 bash -c "cd /tmp && virtualenv virtualenv && source virtualenv/bin/activate && pip3 install -r requirements.txt"
# # "cd /tmp && virtualenv virtualenv && source virtualenv/bin/activate && pip3 install psycopg2 ibm-platform-services ibm-secrets-manager-sdk"

# echo ">>> Zip the actions and the virtualenv..."
# zip -ry function.zip virtualenv __main__.py helper.py templates/*
echo ">>> Creating and activating virtualenv..."
virtualenv virtualenv
source virtualenv/bin/activate

echo ">>> Python Version and pip3 Location:"
python --version
which pip3

echo ">>> Installing dependencies..."
pip3 install --upgrade ibm-platform-services

echo ">>> Deactivating virtualenv..."
deactivate

echo ">>> Zipping actions and the virtualenv..."
zip -ry function.zip virtualenv __main__.py helper.py templates/*

#ibmcloud fn action update /aa6e49e6-3d09-4120-a778-f3036e230d48/notifyDevAction --kind python:3.7 function.zip --web true