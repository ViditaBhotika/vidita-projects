import secrets
from secrets import get_fabman_secret
from fabman import Fabman
import json
import requests
import time
import boto3
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    print(event)

    ddb = boto3.resource('dynamodb')
    table = ddb.Table('SessionTracker')

    machine_id = {
        "FAKE_TEST_EQUIPMENT": 5350
    }

    machine_type = event['queryStringParameters']['machine'] # MUST BE CAPS

    keys = event['queryStringParameters'].keys()

    print(keys)

    if 'action' in keys:
        if event['queryStringParameters']['action'] == 'status':
            print(f"Returning status of {machine_type}")
            response = table.scan(
                FilterExpression=Attr(machine_type).ne(0) & Attr(machine_type).exists()
            )
            print(response)

            if len(response['Items']) == 0:
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'idle'
                    })
                }

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'active', 
                    'eid': response['Items'][0]['eid']
                })
            }
    
    # Get eid and machine
    eid = event['queryStringParameters']['eid']
    
    # Validate inputs
    if not eid:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Missing required parameters',
                'message': 'Incorrect eid input'
            })
        }
    elif not (machine_type == "FAKE_TEST_EQUIPMENT"):
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                #'error': 'Missing required parameters',
                'message': 'Incorrect machine input (ensure all caps)'
            })
        }
    
    # Your logic here using eid and machine
    print(f"Processing request - eid: {eid} and machine: {machine_type}")

    machine_id = machine_id[machine_type]
    
    # this is how we initialize a fabman connection object using the API key we get in secrets.py
    FABMAN_API_KEY = secrets.secret[machine_type] # TESTING this
    fabman = Fabman(get_fabman_secret())
    member = fabman.get_members(q={eid})

    if not member:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Member not registered with Fabman'
            })
        }

    member_id = member[0].id

    response = table.get_item(
        Key = {
            'eid': eid
        }
    )

    if 'Item' in response:
        session_id = response['Item'][machine_type]
    else:
        item = {
            'eid': eid,
            'memberID': member_id,
            'FAKE_TEST_EQUIPMENT': 0
        }

        table.put_item(Item = item)
        session_id = 0
    
    # We are now guaranteed that student is part of database - just need to either start or stop session
    if (session_id == 0):  #check if that eid is allowed in the fake test equipment thingy, and if so, start session
        FABMAN_API_URL = "https://fabman.io/api/v1/bridge/access" #the "fabman.io/api.v1 part can be found at the top of the API documentation"
        headers = {
            "Authorization": f"Bearer {FABMAN_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "member": member_id,
            "currentSession": { "id": 0 },
            "previousSession": { "id": 0 },
            "configVersion": 4294967295
        }

        try:
            response = requests.post(FABMAN_API_URL, json=payload, headers=headers)
            response.raise_for_status() # indicates an error if the HTTP status code is not between 200-299
            result = response.json() # turns the json response into a python dict

            # Output results
            if result['type'] == "allowed":
                print(f"Access granted — Session ID: {result['sessionId']}")
            else: 
                print(f"Failed to start session, not authorized to use {machine_type}")
                return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Failed to start session, member not authorized'
                })
            }

        except requests.exceptions.RequestException as e:
            print(f"HTTP error: {e}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Failed to start session (exception)'
                })
            }

        session_id = result['sessionId']

        table.update_item(
            Key={'eid': eid},
            UpdateExpression=f'SET {machine_type} = :val',
            ExpressionAttributeValues={':val': session_id}
        )

        return {
        'statusCode': 200,
        'body': json.dumps('Session started'),
        'session_id': session_id
    }

    #stop the bridge thingy
    else:
        FABMAN_API_URL = "https://fabman.io/api/v1/bridge/stop"
        
        headers = {
            "Authorization": f"Bearer {FABMAN_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "stopType": "normal",
            "currentSession": {"id": session_id},
            "previousSession": {"id": 0}
        }

        try:
            response = requests.post(FABMAN_API_URL, json=payload, headers=headers)
            response.raise_for_status() # indicates an error if the HTTP status code is not between 200-299
            
            if response.status_code == 204:
                print(f"Session stopped")
            else: 
                print("failed")

        except requests.exceptions.RequestException as e:
            print(f"HTTP error: {e}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Could not stop session'
                })
            }

        table.update_item(
            Key={'eid': eid},
            UpdateExpression=f'SET {machine_type} = :val',
            ExpressionAttributeValues={':val': 0}
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success, stopped machine'})
        }
    
    # # response data that will be returned to the MCU over HTTPS
    # response_data = {
    #     'message': 'Request processed successfully',
    #     'eid': eid,
    #     'machine': machine,
    #     'status': 'success'
    # }
    
    # return {
    #     'statusCode': 200,
    #     'headers': {
    #         'Content-Type': 'application/json',
    #         'Access-Control-Allow-Origin': '*'
    #     },
    #     'body': json.dumps(response_data)
    # }
