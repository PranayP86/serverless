#!/usr/bin/python3
import sys
import psycopg2
import requests
from ibm_platform_services import GlobalTaggingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import json
from json import JSONDecoder

service = None
# To extract JSON objects from the incoming activity tracker with LogDNA alert
def extract_json_objects(text, decoder=JSONDecoder()):
    pos = 0
    while True:
        match = text.find('{', pos)
        if match == -1:
            break
        try:
            result, index = decoder.raw_decode(text[match:])
            yield result
            pos = match + index
        except ValueError:
            pos = match + 1


def parseJson(res):
    # dataJson irepresents the _line we passed. Pull whatever you need.
    dataJson = res

    crn = dataJson["target"]["id"]
    b = crn.split('/')
    c = b[1].split(':')
    accountId = c[0]

    return accountId, crn


def retrieveApiKey(id):
    # Simple query for getting rows in guardrail status table
    sql = "<apikey query where it matches the ID> = '{}' limit 1".format(id)

    cur.execute(sql)  # Execution of query
    rows = cur.fetchall()  # If you only need 1 row use fetchone instead
    return rows[0][0]


def decider():
    # 12 Mandatory Tags
    tag_values = []

    cur.execute("""SELECT work_load FROM --- WHERE request_id = '{}'""".format(reqID))
    appID = cur.fetchall()[0][0]  # APPID
    if appID is not None:
        tag_values.append('APPID:'+appID)
    else:
        tag_values.append('APPID:NULL')

    cur.execute("""SELECT billing_code FROM --- WHERE request_id = '{}'""".format(reqID))
    billingCode = cur.fetchall()[0][0]  # BILLINGCODE
    if billingCode is not None:
        tag_values.append('BILLINGCODE:'+billingCode)
    else:
        tag_values.append('BILLINGCODE:NULL')

    cur.execute("""SELECT country_code FROM --- WHERE request_id = '{}'""".format(reqID))
    country = cur.fetchall()[0][0]  # COUNTRY
    if country is not None:
        tag_values.append('COUNTRY:'+country)
    else:
        tag_values.append('COUNTRY:NULL')

    cur.execute("""SELECT environment FROM --- WHERE request_id = '{}'""".format(reqID))
    env = cur.fetchall()[0][0]  # ENVIRONMENT
    if env is not None:
        tag_values.append('ENVIRONMENT:'+env)
    else:
        tag_values.append('ENVIRONMENT:NULL')

    cur.execute("""SELECT data_classification FROM --- WHERE request_id = '{}'""".format(reqID))
    classification = cur.fetchall()[0][0]  # CSCLASS
    if classification is not None:
        tag_values.append('CSCLASS:'+classification)
    else:
        tag_values.append('CSCLASS:NULL')

    cur.execute("""SELECT admin_email_address FROM --- WHERE request_id = '{}'""".format(reqID))
    groupcon = cur.fetchall()[0][0]  # GROUPCONTACT
    if groupcon is not None:
        if '@' in groupcon:
            groupcon = groupcon.replace('@', '-at-')
            tag_values.append('GROUPCONTACT:'+groupcon)
    else:
        tag_values.append('GROUPCONTACT:NULL')

    return tag_values


def tagSDK(crn, params):
    # Authentication for SDK
    authenticator = IAMAuthenticator(APIKey)  # Passed in as a header

    global tag_service
    tag_service = GlobalTaggingV1(authenticator=authenticator)

    global tags, remove
    tags, remove = comparer(decider())

    resource_model = {'resource_id': crn}

    # Removes tags to be replaced with new ones
    if remove:
        remove_tags = tag_service.detach_tag(
          resources=[resource_model],
          tag_names=remove,
          tag_type='user').get_result()

    # Attaches mandatory tags
    tag_results = tag_service.attach_tag(
      resources=[resource_model],
      tag_names=tags,
      tag_type='user').get_result()
    print(json.dumps(tag_results, indent=2), "NEW:", tags, "OLD:", remove)


def comparer(newtags):
    # Gets tags already attached to resource, if they exist
    new_tags = newtags
    attached_tags = tag_service.list_tags(
      tag_type='user',
      provider='ghost',
      attached_to=crn).get_result()

    existing_tags = []
    for tag in range(len(attached_tags['items'])):
        existing_tags.append(attached_tags['items'][tag]['name'])

    old_tags = []

    for newtag in new_tags:
        for tag in existing_tags:
            if ':' in tag:
                # print(tag.lower().split(':')[0], "=", newtag.lower().split(':')[0], 'and', tag.lower().split(':')[1], "!=", newtag.lower().split(':')[1])
                if ((tag.lower().split(':')[0] == newtag.lower().split(':')[0]) and (tag.lower().split(':')[1] != newtag.lower().split(':')[1])):  # To replace existing mandatory tag if updated.
                    old_tags.append(tag.lower())
                elif (tag == newtag):
                    new_tags.remove(newtag.lower())  # Removes duplicate tag if existing

    return new_tags, old_tags


def extractor(crn):
	# Strips the service and region from crn.
	vals = crn.split(':')

	serviceName = vals[4]
	region = vals[5]

	return serviceName, region


# def notify(params):
#     print("notify")
#     url = "https://24aaadb3.us-south.apigw.appdomain.cloud/bluenovaregion-api/notify"

#     payload = json.dumps({
#     "accountId": params["accountId"],
#     "crn": params["crn"],
#     "subject": "Notification of Remediation – Automated Tagging",
#     "p1": "A new resource was created, or existing resource was updated. All resources are required to be tagged with the mandatory tags.",
#     "p2": "The issue was remediated by adding or updating the required tags to the resource. Tags added: <tag dict from guardrail>. No further action is necessary.",
#     "resourceName": "Automated Tagging",
#     "eventType": params["action"],
#     "ResourceType": params["resourceType"], #typeURI
#     "ruleName": "Mandatory Tags",
#     "eventTime": params["eventTime"],
#     "description": "Tagging",
#     "violator": params["violator"]
#     })

#     headers = {
#     'Authorization': 'Bearer {}'.format(params["notifyBearer"]),
#     'Content-Type': 'application/json',
#     }

#     response = requests.request("POST", url, headers=headers, data=payload)
#     print(response.text)

def mainresponse(dict):
    id, crn = parseJson(dict)  # Needed values parsed out of logDNA

    finalResponse = [id, crn]

    return finalResponse


# Main entry function
def helper(params):
    # Parameters that are needed to connect to the db
    theusername = params["User"]
    thepassword = params["Pass"]
    thehost = params["Host"]
    theport = params["Port"]

    global conn
    global cur

    # Connects to database for pulling account info values
    try:
        conn = psycopg2.connect(host=thehost, port=theport, user=theusername, password=thepassword, sslmode="require", database="ibmclouddb")
    except Exception as ex:
        print("Unable to connect to the database:", ex)

    cur = conn.cursor()

    global crn
    global accountId
    accountId, crn = parseJson(params)
    # Executes query based on account ID (acctID) from the event and gets corresponding request ID
    cur.execute("""select account id query = '{}'""".format(accountId))
    rows = cur.fetchall()
    global reqID
    reqID = rows[0][0]

    # Retrives corresponding API Key
    global APIKey
    APIKey = retrieveApiKey(accountId)
    APIKey = params['apiKey']
    print(APIKey, file=sys.stderr)

    tagSDK(crn, params)
    global serviceName, region
    serviceName, region = extractor(crn)

    response = mainresponse(params)
    return response
