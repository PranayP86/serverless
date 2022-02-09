#!/usr/bin/python3
import os
import sys
import time
import psycopg2
import requests
from ibm_platform_services import ResourceControllerV2
from ibm_schematics.schematics_v1 import SchematicsV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
import http.client
import jinja2
import json
from json import JSONDecoder

service = None

def parseJson(res):
    # res represents the parameters we passed. Pull whatever you need.
    userEmail = res["initiator"]["name"]
    crn = res["target"]["id"]
    b = crn.split('/')
    c = b[1].split(':')
    accountId = c[0]
    eventTime = res["eventTime"]

    return accountId, crn, userEmail, eventTime


def mainresponse(dict):
    id, crn, userEmail, timestamp = parseJson(dict)  # Needed values parsed out of logDNA

    finalResponse = [id, crn]

    return finalResponse


def deleter(crn):
    # When the region is not supported, the instances created in that region must be deleted.
    authenticator = IAMAuthenticator(APIKey)
    rescon = ResourceControllerV2(authenticator=authenticator) # Authentication for Resource Controller SDK (rescon)

    try: # When the region is not supported, the instances created in that region must be deleted.
        response = rescon.delete_resource_instance(id=crn,recursive=True)
        print("Resource with crn: {} has been deleted recursively.".format(crn))
    except ApiException as e:
        print("Delete Resource not supported through Resource Controller SDK or set up for requests.")
        # Expected error if resource is not supported for a recursive delete.
        print("RESCON-ERROR:", e.http_response.json())  # Print error in case for troubleshooting.


def extractor(crn):
	# Strips the service and region from crn.
	vals = crn.split(':')
	serviceName = vals[4]
	region = vals[5]
	return serviceName, region

def createRegionList():
    newRegionList = "["
    for regionRow in acctRegions:
        newRegionList+="\"{}\",".format(regionRow[1])
    newRegionList+="\"{}\"]".format(region)

    print("Created region list: ", newRegionList)
    return newRegionList

def updateVariables(workspaceId, templateId, bearer,location):
    # To update input variable (logdna-regions) in schematics workspace to trigger LogDNA resource deployment
    url = "<replace with Schematics URL - e.g. https://{}.schematics.cloud.ibm.com/v1/workspaces/{}/template_data/{}/values>".format(location,workspaceId, templateId)

    payload = json.dumps({
    "variablestore": [
        {
        "description": "These are the LogDNA regions",
        "name": "logdna-regions",
        "secure": False,
        "use_default": False,
        "type": "list(string)",
        "value": createRegionList()
        }
    ]
    })
    headers = {
    'Authorization': 'Bearer {}'.format(bearer),
    'Content-Type': 'application/json',
    'Cookie': 'BCSI-CS-77196e4680a1144c=1'
    }

    response = requests.request("PUT", url, headers=headers, data=payload)

    print("Update variables response: ", response.text)


def refreshToken():
    # Generate refresh token for schematics workspace call
    url = 'https://iam.cloud.ibm.com/identity/token'
    headers = {
        'Content-Type':'application/x-www-form-urlencoded'
    }
    tokendata = 'grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={}'.format(APIKey)
    output = None
    try:
        refresh_response = requests.post(url, auth=('bx', 'bx'), data=tokendata, headers=headers, timeout=180)
        output = refresh_response.json()
    except Exception as err:
        print("Refresh token retrieval error: ", err)

    refreshToken = output['refresh_token']

    return refreshToken


# Remediation notifications
# def notify(params, case, email):
    print("Guardrail Notification")
    print("Params user email: ", params["userEmail"])
    print("Email: ", email)
    url = "< for notification API integration >"

    # Depending on what has occurred, the corresponding email body is sent.
    if case == "provisioned":
        bodyText = "In account: {} : The region {} is already provisioned. No further remediation necessary.".format(accountId, region)
        bodyText2 = "Event time: {}".format(eventTime)
    elif case == "supported":
        bodyText = "In account: {} : The region {} is supported. LogDNA resources have been deployed and the database was updated with the provisioned region.".format(accountId, region)
        bodyText2 = "The region {} is now provisioned in this account. No further action is necessary. Event time: {}".format(region, eventTime)
    elif case == "delete":
        bodyText = "In account: {} : The region {} is not supported. We have remediated this issue by deleting the {} instance created in this account.".format(accountId, region, serviceName)
        bodyText2 = "Please refrain from creating resources in regions that are not currently supported. Event time: {}".format(eventTime)
    else:
        bodyText = "Error in account: {} for service: {} created in region: {}. Remediation has failed unexpectedly.".format(accountId, serviceName, region)
        bodyText2 = "Resource CRN: {}. Event time: {}".format(crn, eventTime)

    payload = json.dumps({
    "accountId": params["accountId"],
    "crn": params["crn"],
    "subject": "Notification of Remediation - Region",
    "p1": "Resources may only be provisioned in regions that are currently supported.",
    "p2": "We have remediated this issue by deleting this resource. Please only create resources in regions we support. These regions include: Dallas, Frankfurt, Sydney, London, Tokyo, and Washington DC.",
    "resourceName": "Supported Regions",
    "eventType": params["action"],
    "ResourceType": params["resourceType"], # typeURI
    "ruleName": "Unsupported Region",
    "eventTime": params["eventTime"],
    "description": "Supported/Unsupported Regions",
    "violator": params["violator"]
    })
    headers = {
    'Authorization': 'Bearer {}'.format(params["notifyBearer"]),
    'Content-Type': 'application/json',
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)


def streaming(dict):
    # Kick off chain of provisioning
    url = dict.get("streamURL")
    print("Streaming to: ", region)

    payload = json.dumps({
    "api_key": APIKey,
    "account_id": accountId,
    "region": region,
    "helper": True
    })

    print("Our payload: ", payload)
    headers = {
    'Authorization': 'Bearer {}'.format(bearer),
    'Content-Type': 'application/json',
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
    except requests.exceptions.ReadTimeout as e:
        print("Expected READ TIMEOUT to notifyUserURL, this can be ignored.")
        pass
    except Exception as error:
        print("Error: " + str(error))
        return {"statusCode":503,
                "body":{"error": {
                        "code":503,
                        "message":"We received an unusual error",
                        "status":"Failed",
                        "details":[{
                            "@stacktrace":str(error),
                            "activationId":"activationId"
                            }]}}}


def retrieveLocation(region):
    sql = "SELECT schematic_region FROM ibmcloud.region WHERE region_id = '{}'".format(region)
    cur.execute(sql)  # Execution of query
    rows = cur.fetchall()  # If you only need 1 row use fetchone instead
    return rows[0][0]  # All rows from our query

def retrieveRegion():
    sql = "SELECT region FROM ibmcloud.account WHERE account_id = '{}'".format(accountId)
    cur.execute(sql)  # Execution of query
    rows = cur.fetchall()  # If you only need 1 row use fetchone instead
    return rows[0][0]  # All rows from our query

def retrieveAdmin():
    sql = "SELECT admin_email_address FROM ibmcloud.account WHERE account_id = '{}'".format(accountId)
    cur.execute(sql)  # Execution of query
    rows = cur.fetchall()  # If you only need 1 row use fetchone instead
    return rows[0][0]  # All rows from our query

def retrieveEnv():
    sql = "SELECT environment FROM ibmcloud.account WHERE account_id = '{}'".format(accountId)
    cur.execute(sql)  # Execution of query
    rows = cur.fetchall()  # If you only need 1 row use fetchone instead
    return rows[0][0]  # All rows from our query


# Main entry function
def helper(params):
    # Parameters that are needed to connect to the db
    theusername = params["User"]
    thepassword = params["Pass"]
    thehost = params["Host"]
    theport = params["Port"]

    # Retrives API Key
    global APIKey, notifyBearer
    APIKey = params["apiKey"]
    notifyBearer = params["notifyBearer"]

    global conn, cur  # Connects to database for pulling account info values
    try:
        conn = psycopg2.connect(host=thehost, port=theport, user=theusername, password=thepassword, sslmode="require", database="ibmclouddb")
    except Exception as ex:
        print("Unable to connect to the database:", ex)

    cur = conn.cursor()

    global accountId, crn, serviceName, region, bearer, userEmail, acctRegions, eventTime
    accountId, crn, userEmail, eventTime = parseJson(params)
    serviceName, tempZone = extractor(crn)
    tempRegion = tempZone.split('-')
    region = "{}-{}".format(tempRegion[0], tempRegion[1])

    # Queries database to check what regions an account has.
    cur.execute("""SELECT * FROM ibmcloud.account_region WHERE account_id = '{}'""".format(accountId))
    acctRegions = cur.fetchall()


    # Checks if account already has region resources provisioned.
    provisionedList = []
    for row in acctRegions:
        provisionedList.append(row[1])

    # Get a Bearer token for HTTP request authentication.
    keyUrl="https://iam.cloud.ibm.com/identity/token"
    input = "grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey&apikey={}".format(APIKey)
    result = requests.post(keyUrl,headers={"content-type":"application/x-www-form-urlencoded","accept":"application/json"},data = input)
    temp = result.json()
    bearer = temp["access_token"]

    print("Before starting: ", region, "in the region list? ", provisionedList)

    if region == 'global':
        return {"Message": "This is a global region."}
    else:
        if region in provisionedList:

            return {"Message": "This region is already provisioned."}
        else:
            # Executes query to check if region appears in supported regions database table.
            cur.execute("""SELECT * FROM ibmcloud.region WHERE region_id = '{}'""".format(region))
            supported = cur.fetchall()

            if supported:
                # In the case of a supported region, LogDNA resources must be deployed for the new region.
                print("This region is supported.")
                authenticator = IAMAuthenticator(APIKey)
                schematicService = SchematicsV1(authenticator=authenticator) # Authentication for Schematics API (schematicService)
                print(region)
                original_region = retrieveRegion()
                schematicsLocation = retrieveLocation(original_region)

                print('Org: ', original_region)
                print('Sch: ', schematicsLocation)

                serviceRegions = {
                    "us-south": 'https://us-south.schematics.cloud.ibm.com',
                    "us-east": 'https://us-east.schematics.cloud.ibm.com',
                    "eu-de": 'https://eu-de.schematics.cloud.ibm.com',
                    "eu-gb": 'https://eu-gb.schematics.cloud.ibm.com',
                }

                if schematicsLocation in serviceRegions:
                    print("Schematics URL: ", serviceRegions[schematicsLocation])
                    schematicService.set_service_url(serviceRegions[schematicsLocation])
                else:
                    print("Region not found for Schematics Location URL.")

                # Uses the IBM Schematics API to retrieve details on the workspace.
                workspaces = schematicService.list_workspaces().get_result()
                time.sleep(10)
                print("Workspaces: ", workspaces)

                # Then sends a request to replace "LogDNA-Region" with new region to auto-deploy resources.
                workspaceId = workspaces['workspaces'][0]['id']
                templateId = workspaces['workspaces'][0]['template_data'][0]['id']
                print("workspaceId:", workspaceId)
                print("templateId:", templateId)
                update_result = updateVariables(workspaceId, templateId, bearer,schematicsLocation)
                time.sleep(30)

                # Updates database with new provisioned region.
                cur.execute("""INSERT INTO ibmcloud.account_region(account_id, region_id) VALUES ('{}', '{}')""".format(accountId, region))
                conn.commit()
                print("Result from update: ", update_result)

                blueprintApply = schematicService.apply_workspace_command(w_id=workspaceId, refresh_token=refreshToken()).get_result()

                # Calls function to activate streaming
                time.sleep(90)
                print("Results from the apply: ", blueprintApply)
                streaming(params)

                print("Params user email (before notify call): ", params["userEmail"])
                
                # notify(params, "supported", params["userEmail"])
                # notify(params, "supported", retrieveAdmin())
                print("Log DNA resources deployed and region {} provisioned in account {}".format(region, accountId))
            else:
                # When the region is not supported, the resource has to be deleted.
                deleter(crn)
                print("Params user email (before notify call): ", params["userEmail"])
                # notify(params, "delete", params["userEmail"])
                # notify(params, "delete", retrieveAdmin())
                print("Delete finished.")

    response = mainresponse(params)
    return response
