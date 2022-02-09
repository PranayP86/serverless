# `Supported Regions Guardrail`
This guardrail is responsible for handling resources created in regions that are, at the moment, not supported for provisioning, as well as deploying LogDNA resources for regions that are. The usage of the guardrail involves:
* Deleting the resource if it's created in an unsupported region.
* If the region is supported in an account, schematics workspace input variables are changed to trigger automatic provisioning of LogDNA resources for the region.

A basic explanation of the flow would be:
1. Resource create event triggers guardrail in function action.
2. Guardrail parses resource CRN for region and checks database (PostgreSQL Instance) to see if account has the region set up with LogDNA resources.
3. If region is already provisioned, guardrail finishes. If not, checks database to see if requested region is supported.
4. If supported, updates Schematics Workspace input variable with added region using constructed bearer token. This will continue to trigger LogDNA resource configuration. Also, this will update database account regions.
5. If not supported, uses Resource Controller SDK to recursively delete resource instance. Guardrail finishes.

------------
------------
## `Activity Tracker Events`
The guardrail will be called anytime this event is captured in activity tracker:

*.create

>Essentially, any object that is created will trigger the supported regions guardrail to ensure nothing is provisioned in unsupported regions and set up LogDNA resources for supported regions.

_______________________
## `Troubleshooting Section`
Please follow the below steps when facing issues:
1. Check if any of the above events has been streamed into the activity tracker of the account.
2. In the activation dashboard, check if any logs has been generated for the event. Note the response.
3. Check if any exception was raised by the event, if yes, note down the response and see if any exception occurred from our code side.


## `References`
- https://cloud.ibm.com/apidocs/resource-controller/resource-controller
- https://cloud.ibm.com/apidocs/functions?code=python
- https://cloud.ibm.com/apidocs/schematics/schematics?code=python
