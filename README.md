# Serverless Functions
Collection of serverless functions/guardrails per CSP.

## Prerequisites
These serverless functions have dependencies involving configurations and resources:

### For IBM Cloud:
1. Activity Tracker must be set up for LogDNA event streaming. These events will be used to trigger cloud functions through an orchestration method.
2. PostgreSQL instance must be configured. Update psycopg2 queries to use your data schema/tables.
3. Orchestrator function must be set up as an action and will be used to route these events to the appropriate guardrail endpoint, which will cause those functions to trigger. Metadata from these events will be passed to the actions for guardrail logic.
4. Copy the init.sh file to any of the guardrail folders being used and update the requirements.txt file to include any additional packages.
> Note that some packages are not part of the requirements as they are given in IBM Cloud's serverless python environment.
5. Have Docker running and `sudo sh init.sh` to create the virtualenv. This will create a function.zip file after creating a virtualenv from the given requirements.txt file.
6. Set up a namespace and a cloud function and upload the zip file with IBM Cloud CLI or OpenWhisk.
7. Update orchestration function with the Activity Tracker events and respective function endpoints.
8. Test! Do something in your account to log that event and watch it trigger the associated guardrail(s).