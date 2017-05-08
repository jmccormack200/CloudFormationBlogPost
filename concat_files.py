from os import listdir
import json
import re
from copy import deepcopy
import random

pythonFiles = [];
PERMISSION = 'Permission'
RESOURCE = 'Resource'
METHOD = 'Method'

SOURCE_ARN = {"Fn::Join" : ["", ["arn:aws:execute-api:", { "Ref" : "AWS::Region"}, ":", { "Ref" : "AWS::AccountId"}, ":", { "Ref" : "RestApi" }, "/*"]]}
REST_API_ID = {"Ref" : "RestApi"}
LAMBDA_PERMISSION_ARN = {"Fn::Join" : ["", ["arn:aws:iam::", { "Ref" : "AWS::AccountId"}, ":role/pickPocketWriteAndSNS"]]}

with open('config.json') as configFile:
    configJson = json.load(configFile)

parentyaml = {}
jsonOut = {}
resourcePaths = []
resourcePathExists = False

for config in configJson['functions']:
    with open('deploy_template.json') as templateFile:
        with open('api_gateway_template.json') as apiTemplateFile:
            functionName = config['function'].replace(".py", "") + "CLOUDFORM"

            tempJSON = json.load(templateFile)
            apiTemplateJSON = json.load(apiTemplateFile)

            jsonOut[functionName] = tempJSON['FunctionName']

            # Create Function
            propJson = jsonOut[functionName]["Properties"]
            codeJson = propJson["Code"]
            with open(config['function']) as pythonFile:
                codeJson['ZipFile'] = pythonFile.read()
            propJson['FunctionName'] = functionName
            propJson['Role'] = LAMBDA_PERMISSION_ARN

            # Add Permission
            permissionTemplate = apiTemplateJSON[PERMISSION]
            permissionName = PERMISSION + functionName
            jsonOut[permissionName] = permissionTemplate
            jsonOut[permissionName]['DependsOn'] = functionName
            jsonOut[permissionName]['Properties']['FunctionName'] = functionName
            jsonOut[permissionName]['Properties']['SourceArn'] = SOURCE_ARN

            # Add Resource
            paths = config['api_path'].split("/")
            for path in paths:
                if (path not in resourcePaths):
                    resourceTemplate = apiTemplateJSON[RESOURCE]
                    namePath = re.sub(r'\W+', '', path)
                    resourceName = RESOURCE + functionName + namePath
                    jsonOut[resourceName] = deepcopy(resourceTemplate)
                    jsonOut[resourceName]['DependsOn'] = functionName
                    jsonOut[resourceName]['Properties']['PathPart'] = path
                    resourcePaths.append(path)
                    resourcePathExists = False
                else:
                    # If the resource path is a repeat then we don't need to make two
                    resourcePathExists = True

            # Add Method
            methodTemplate = apiTemplateJSON[METHOD]
            methodName = METHOD + functionName
            jsonOut[methodName] = methodTemplate
            methodUri = { "Fn::Join" : ["", ["arn:aws:apigateway", ":", { "Ref" : "AWS::Region" }, ":","lambda:path/2015-03-31/functions/arn:aws:lambda", ":", { "Ref" : "AWS::Region" }, ":", { "Ref" : "AWS::AccountId" }, ":function:", functionName, "/invocations"]]}
            jsonOut[methodName]['Properties']['Integration']['Uri'] = methodUri
            jsonOut[methodName]['Properties']['RestApiId'] = REST_API_ID
            jsonOut[methodName]['Properties']['ResourceId'] = { "Ref": resourceName}
            if (resourcePathExists):
                jsonOut[methodName]['DependsOn'] = [functionName, permissionName]
            else:
                jsonOut[methodName]['DependsOn'] = [functionName, resourceName, permissionName]
            jsonOut[methodName]['Properties']['HttpMethod'] = config['method']

with open("deploy.json", "a") as f:
    with open("api_gateway_base.json") as baseTemplateFile:
        baseTemplateJSON = json.load(baseTemplateFile)
        # TODO pull RestApi name from config file.
        api = baseTemplateJSON['RestApi']
        api['Properties']['Name'] = configJson['ApiName']
        jsonOut['RestApi'] = api
        db = baseTemplateJSON['DB']
        db['Properties']['TableName'] = configJson['DbName']
        jsonOut['DB'] = db
        parentyaml['Resources'] = jsonOut
        json.dump(parentyaml, f, indent=4, sort_keys=True)
