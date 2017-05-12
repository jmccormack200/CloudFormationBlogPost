import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

"""
JSON Format:
    "userId":"JohnM",
    "displayName":"John Mack",
    "combination":"[1,2,3,4]"
"""
validDigits = [1, 2, 3, 4, 5, 6]


def lambda_handler(event, context):
    output = {}
    dynamo_db = boto3.resource('dynamodb')
    table = dynamo_db.Table('PickPocketDB')

    user_id = event['userId']
    combination = event['combination']
    combination = json.loads(combination)

    query_table = table.query(KeyConditionExpression=Key('UserId').eq(user_id))

    if query_table['Count'] != 0:
        output["response"] = "USER_EXISTS"
        return output

    if not validate_combination(combination):
        output["response"] = "INVALID_COMBINATION_FORMAT"
        return output

    if 'displayName' in event:
        displayName = event['displayName']
    else:
        displayName = user_id

    combinationLength = len(combination)

    table.put_item(
        Item={
            'UserId': user_id,
            'DisplayName': displayName,
            'Combination': combination,
            'CombinationLength': combinationLength
        }
    )

    output = {"response": "success"}
    return output


def validate_combination(combination):
    try:
        for digit in combination:
            if int(digit) not in validDigits:
                print digit
                return False
        return True
    except:
        return False
