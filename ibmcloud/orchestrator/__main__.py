from os import error
import sys
import requests
import json
from json import JSONDecoder

actionDict = {
    # Example event and connected endpoints
    "cloud-object-storage.bucket.create": [
        "https://<region>.functions.appdomain.cloud/api/v1/web/<namespace>/<function/code>",
        "https://<region>.functions.appdomain.cloud/api/v1/web/<namespace>/<another-function/code>" 
    ],
    "is.vpc.vpc.create": "https://<region>.functions.appdomain.cloud/api/v1/web/<namespace>/<function/code>"
    } 


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
    #res is what represents our JSON object
    line = res["_line"]
    
    jsonGen = extract_json_objects(line)
    dataJson = next(jsonGen)
    a = dataJson["logSourceCRN"]
    b = a.split('/')
    c=b[1].split(':')
    accountId = c[0]
    action = dataJson["action"]
    
    return action, line, accountId
    
def guardrailHandler(dict):
    body = dict["body"]
    
    for x in range(0,len(body)):
        action, line, accountId = parseJson(body[x])
        guardrail(action, line, accountId)
  
    
def guardrail(action, line, accountId):
# Parse JSON to get action and _line variables
    # Check for associated events
    print("{}:action: {}".format(accountId, action) )
    if ".create" in action or ".update" in action or ".detach" in action or ".attach":
        guardrailJson = line
        try:
            url = " insert associated endpoint url for cloud function" # Get endpoint associated with action
            r = requests.post(url, json=guardrailJson) # Post JSON to guardrail endpoint
            print("{}: {}".format(accountId, r.text) ) # TEXT/HTML
            print("{}: {} {}".format(accountId, r.status_code, r.reason) ) # HTTP
        except Exception as e:
            print("{} Error calling Tagging Guardrail: {}".format(accountId, e)) 

    # Check if a guardrail is attached to the current action
    if action in actionDict:
        if isinstance(actionDict[action], list):
            for action2 in actionDict[action]:
                guardrailJson = line
                parm = {"accountId": accountId}
                url = action2 # Get endpoint associated with action
                r = requests.post(url, json=guardrailJson, params=parm) # Post JSON to guardrail endpoint
                print("{}: {}".format(accountId, r.text) ) # TEXT/HTML
                print("{}: {} {}".format(accountId, r.status_code, r.reason) ) # HTTP
        else:
            guardrailJson = line
            parm = {"accountId": accountId}
            url = actionDict[action] # Get endpoint associated with action
            r = requests.post(url, json=guardrailJson, params=parm) # Post JSON to guardrail endpoint
            print("{}: {}".format(accountId, r.text) ) # TEXT/HTML
            print("{}: {} {}".format(accountId, r.status_code, r.reason)) # HTTP
        
        
        return guardrailJson 
        
    else: # No guardrail is found
        print("{}: Guardrail Orchestrator: There are no guardrails attached to this action".format(accountId))
        return "There are no guardrails attached to this action"
    

def main(dict):
    guardrailHandler(dict)
    guardrailResults = "Complete" #guardrail(dict)
    
    # We return as needed to pass the respective parameters on
    return {"Guardrail": guardrailResults}
