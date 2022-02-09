import os
# from flask import (Flask, render_template, url_for)
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_platform_services import UserManagementV1
import jinja2
import psycopg2
import requests
import json
from json import JSONDecoder

def helper(params):
    # Parameters that are needed to connect to the db
    theusername = params["User"]
    thepassword = params["Pass"]
    thehost = params["Host"]
    theport = params["Port"]

    global accountId, crn, serviceName, region, iamID, apiKey
    apiKey = params['prodKey']
    iamID = params['violator']
    crn = params['crn']
    serviceName, region = extractor(crn)

    global conn, cur  # Connects to database for pulling account info values
    try:
        conn = psycopg2.connect(host=thehost, port=theport, user=theusername, password=thepassword, sslmode="require", database="ibmclouddb")
    except Exception as ex:
        print("Unable to connect to the database:", ex)

    cur = conn.cursor()

    # Variables for HTML e-mail template (Jinja vars)
    global subject, p1, p2, resourceName, eventType, resourceType, ruleName, violator, eventTime, csbNumber, environment, cloudRegion, resourceCRN, firstName, lastName, email
    subject = params['subject'] # Subject
    p1 = params['p1'] # Paragraph 1
    p2 = params['p2'] # Paragraph 2
    # accountAdmin = params['accountAdmin'] # Account Admin
    accountId = params['accountId'] # Account Number
    eventType = params['eventType'] # Event Type
    # environment = params['environment'] # Environment
    # cloudRegion = params['region'] # Cloud Region
    ruleName = params['ruleName'] # Rule ID
    resourceType = eventType.split('.')[0] # Resource Type
    resourceName = params['resourceName'] # Resource Name
    resourceCRN = params['crn'] # Resource CRN
    eventTime = params['eventTime'] # Date Time
    csbNumber = params['csbNumber'] # CSB Number
    firstName, lastName, email = userDetails(accountId, iamID) # User Details
    
    sendViolatorEmail()


def extractor(crn):
	# Strips the service and region from crn.
	vals = crn.split(':')

	serviceName = vals[4]
	region = vals[5]

	return serviceName, region


def retrieveAdmin():
    sql = "select email query from db = '{}'".format(accountId)
    cur.execute(sql)  # Execution of query
    rows = cur.fetchall()  # If you only need 1 row use fetchone instead
    return rows[0][0]  # All rows from our query

def retrieveEnv():
    sql = "select environment query from db = '{}'".format(accountId)
    cur.execute(sql)  # Execution of query
    rows = cur.fetchall()  # If you only need 1 row use fetchone instead
    return rows[0][0]  # All rows from our query

# Returns email and first/last name of user
def userDetails(accountId, iamId):
    # Using User Management API to get user profile
    userService = UserManagementV1(authenticator=IAMAuthenticator(apikey=apiKey))
    userProfile = userService.get_user_profile(
        account_id = accountId,
        iam_id = iamId,
        ).get_result()
    
    # Unpacking variables
    firstName = userProfile['firstname']
    lastName = userProfile['lastname']
    email = userProfile['email']
    # state = userProfile['state'] # e.g. 'ACTIVE', 'DISABLED_CLASSIC_INFRASTRUCTURE'
    # photo = userProfile['photo'] # URL for profile picture
    # print("First Name: {}\nLast Name: {}\nEmail: {}".format(firstName, lastName, email))
    
    return firstName, lastName, email

def sendViolatorEmail():
    # Sets up the email template using Jinja2
    jinjaEnv = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
    template = jinjaEnv.get_template('remediationTemplate.html')
    # Sends the variables that are used by the template
    jinjaVars = {
        'Subject': subject,
        'firstName': firstName,
        'lastName': lastName,
        'firstParagraph': p1, # Paragraph 1
        'secondParagraph': p2, # Paragraph 2
        'AccountAdmin': retrieveAdmin(), # Account Admin
        'AccountId': accountId, # Account Number
        'EventType': eventType, # Event Type
        'WorkLoad': retrieveEnv(), # Environment
        'ViolatorUserName': email, # Violator User Name
        'CloudRegion': region, # Cloud Region
        'ViolatedGovernanceRuleName': ruleName, # Rule ID
        'ResourceType': resourceType, # Resource Type
        'ResourceName': resourceName, # Resource Name
        'ResourceCRN': resourceCRN, # Resource CRN
        'DateTime': eventTime, # Date Time
        'CSBNumber': csbNumber # CSB Number
    }
    print("Jinja2 Variables: ",jinjaVars)
    # print(template.render(jinjaVars))
    url = "<notification API URL>"

    payload = json.dumps({
      "fromEmail": "< platform email address>",
      "toEmails": [email],
      "subject": "Notification of Guardrail Remediation",
      "bodyText": "",
      "bodyHtml": template.render(jinjaVars)
    })
    headers = {
      'Content-Type': 'application/json',
      'x-api-key': apiKey
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    # print(response.text)

    if not response.ok:
        print("Status Code of Notify Action: ", response.status_code)
        print("Reason for Code of Notify Action: ", response.reason)
        print("Notify Action Full Text: ", response.text)
    else:
        print("Notify Action Status OK?: ", response.ok)
