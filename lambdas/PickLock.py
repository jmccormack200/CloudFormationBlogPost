import json
import boto3
from boto3.dynamodb.conditions import Key, Attr


def lambda_handler(event, context):
    output = {}
    print(event)
    user_to_pick = event['params']['username']

    dynamo_db = boto3.resource('dynamodb')
    table = dynamo_db.Table('PickPocketDB')

    query = table.query(KeyConditionExpression=Key('UserId').eq(user_to_pick))

    if query['Count'] == 0:
        output['error'] = 'User Not Found'
        return output

    answer = query['Items'][0]['Combination']

    output['answerList'] = answer

    guess = event['body']['guess']
    guess = json.loads(guess)

    result = check_answer(guess, answer)

    return {
        'result': result
    }


def check_answer(guess, answer):
    output = {}
    correct = 0
    close = 0
    if len(guess) < len(answer):
        output['error'] = "Guess has too few digits"
        return output
    if len(guess) > len(answer):
        output['error'] = "Guess has too many digits"
        return output

    for digit in range(0, len(answer)):
        if guess[digit] == answer[digit]:
            answer[digit] = "x"
            guess[digit] = "x"
            correct += 1
    # Check Number Close
    for digit in range(0, len(answer)):
        if guess[digit] != "x" and guess[digit] in answer:
            answer[answer.index(guess[digit])] = "x"
            close += 1

    output["correct"] = correct
    output["close"] = close
    return output
