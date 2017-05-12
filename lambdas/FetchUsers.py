import boto3

def lambda_handler(event, context):
    dynamo_db = boto3.resource('dynamodb')
    table = dynamo_db.Table('PickPocketDB')

    query = table.scan(AttributesToGet=[
        'UserId', 'CombinationLength'
    ])

    query = query['Items']

    return {
        'result': query
    }
