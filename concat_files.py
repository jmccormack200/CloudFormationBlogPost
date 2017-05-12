import json
import re
from copy import deepcopy

PERMISSION = 'Permission'
RESOURCE = 'Resource'
METHOD = 'Method'

SOURCE_ARN = {"Fn::Join": ["", ["arn:aws:execute-api:", {"Ref": "AWS::Region"}, ":", {"Ref": "AWS::AccountId"}, ":",
                                {"Ref": "RestApi"}, "/*"]]}
REST_API_ID = {"Ref": "RestApi"}
LAMBDA_PERMISSION_NAME = "LambdaRole"
LAMBDA_PERMISSION_ARN = {"Fn::Join": ["", ["arn:aws:iam::", {"Ref": "AWS::AccountId"}, ":role/", {"Ref": LAMBDA_PERMISSION_NAME}]]}


class CloudFormationCreator:
    def __init__(self):
        self.json_out = {}
        self.parent_json = {}
        self.resource_paths = []
        self.resource_path_exists = False

    def create_json(self):
        with open('config.json') as configFile:
            config_json = json.load(configFile)

        for config in config_json['functions']:
            with open('templates/lambda_template.json') as templateFile:
                with open('templates/api_gateway_template.json') as apiTemplateFile:
                    function_name = config['function'].replace(".py", "") + "CLOUDFORM"

                    temp_json = json.load(templateFile)
                    api_template_json = json.load(apiTemplateFile)

                    self.json_out[function_name] = temp_json['FunctionName']

                    # Create Function
                    self.create_function(function_name, config)
                    # Add Permission
                    permission_name = self.create_permission(function_name, api_template_json)
                    # Add Resource
                    resource_name = self.create_resource(function_name, api_template_json, config)
                    # Add Method
                    self.create_method(function_name, api_template_json, config, resource_name, permission_name)

        with open("deploy.json", "a") as f:
            with open("templates/api_gateway_base.json") as baseTemplateFile:
                base_template_json = json.load(baseTemplateFile)
                # TODO pull RestApi name from config file.
                api = base_template_json['RestApi']
                api['Properties']['Name'] = config_json['ApiName']
                self.json_out['RestApi'] = api

                db = base_template_json['DB']
                db['Properties']['TableName'] = config_json['DbName']
                self.json_out['DB'] = db

                lambdaRole = base_template_json[LAMBDA_PERMISSION_NAME]
                self.json_out[LAMBDA_PERMISSION_NAME] = lambdaRole

                self.parent_json['Resources'] = self.json_out
                json.dump(self.parent_json, f, indent=4, sort_keys=True)

    def create_function(self, function_name, config):
        prop_json = self.json_out[function_name]["Properties"]
        self.json_out[function_name]['DependsOn'] = LAMBDA_PERMISSION_NAME
        code_json = prop_json["Code"]
        with open("lambdas/" + config['function']) as pythonFile:
            code_json['ZipFile'] = pythonFile.read()
            prop_json['FunctionName'] = function_name
            prop_json['Role'] = LAMBDA_PERMISSION_ARN

    def create_permission(self, function_name, api_template_json):
        permission_template = api_template_json[PERMISSION]
        permission_name = PERMISSION + function_name
        self.json_out[permission_name] = permission_template
        self.json_out[permission_name]['DependsOn'] = function_name
        self.json_out[permission_name]['Properties']['FunctionName'] = function_name
        self.json_out[permission_name]['Properties']['SourceArn'] = SOURCE_ARN
        return permission_name

    def create_resource(self, function_name, api_template_json, config):
        paths = config['api_path'].split("/")
        for path in paths:

            name_path = re.sub(r'\W+', '', path)
            resource_name = RESOURCE + name_path

            if path not in self.resource_paths:
                resource_template = api_template_json[RESOURCE]
                self.json_out[resource_name] = deepcopy(resource_template)
                self.json_out[resource_name]['DependsOn'] = function_name
                self.json_out[resource_name]['Properties']['PathPart'] = path
                self.resource_paths.append(path)
                self.resource_path_exists = False

            else:
                # If the resource path is a repeat then we don't need to make two
                self.resource_path_exists = True
            return resource_name

    def create_method(self, function_name, api_template_json, config, resource_name, permission_name):
        method_template = api_template_json[METHOD]
        method_name = METHOD + function_name
        self.json_out[method_name] = method_template
        method_uri = {"Fn::Join": ["", ["arn:aws:apigateway", ":", {"Ref": "AWS::Region"}, ":",
                                        "lambda:path/2015-03-31/functions/arn:aws:lambda", ":",
                                        {"Ref": "AWS::Region"}, ":", {"Ref": "AWS::AccountId"}, ":function:",
                                        function_name, "/invocations"]]}
        self.json_out[method_name]['Properties']['Integration']['Uri'] = method_uri
        self.json_out[method_name]['Properties']['RestApiId'] = REST_API_ID
        self.json_out[method_name]['Properties']['ResourceId'] = {"Ref": resource_name}
        if (self.resource_path_exists):
            self.json_out[method_name]['DependsOn'] = [function_name, permission_name]
        else:
            self.json_out[method_name]['DependsOn'] = [function_name, resource_name, permission_name]
        self.json_out[method_name]['Properties']['HttpMethod'] = config['method']


if __name__ == "__main__":
    cformation = CloudFormationCreator()
    cformation.create_json()
