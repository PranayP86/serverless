# `Tagging Guardrail`
This guardrail is responsible for automatically tagging cloud resources with mandatory tags. The usage of the guardrail involves:
* Automatically attaching the mandatory tags to the resource that triggers the cloud function
* Making sure attached tags are correct and up to date as per the database

A basic explanation of the flow would be:
1. Resource create/update event triggers guardrail in function action.
2. Guardrail connects to PostgreSQL database and retrieves corresponding tag values.
3. Guardrail checks if tags are correct and uses tagging SDK to create/attach tags to resource.

Mandatory Tag examples:
Mandatory Tag|Value from Database|Example
-------------|------|----
APPID| work_load| Ex: sandbox
BILLINGCODE| billing_code| Ex: bflx20....
COUNTRY| country_code| Ex: us
ENVIRONMENT| environment| Ex: SBX
CSCLASS| data_classification| Ex: Confidential
GROUPCONTACT| admin_email_address| email associated with account

------------
------------
# `Activity Tracker Events`
The guardrail will be called anytime any of the following events are found in activity tracker:

* .create
* .update
* .detach

>Essentially, any object that is created or updated will trigger the tagging guardrail to ensure all tags are attached and correct. The guardrail is also triggered by a user tag being detached.

_______________________
# `Troubleshooting Section`
Please follow the below steps when facing issues:
1. Check if any of the above events has been streamed into the activity tracker of the account.
2. In the activation dashboard, check if any logs has been generated for the event. Note the response.
3. Check if any exception was raised by the event, if yes, note down the response and see if any exception occurred from our code side.


Refrences
- https://cloud.ibm.com/apidocs/tagging?code=python
