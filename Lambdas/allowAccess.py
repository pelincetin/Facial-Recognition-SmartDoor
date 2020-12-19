import json
import boto3
import botocore

INVALID_RESPONSE = {'statusCode': 404}

def validateOTP(otpInput, faceID):
    '''
    Check that in table.
    '''
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('passcodesDB1')
    try:
        response = table.get_item(Key={'faceID': faceID})
        print("dynamo response:", response)
        if "Item" not in response:
            permission = False
        else:
            permission = (response["Item"]["AccessCode"] == otpInput) and (not response['Item']['used'])
    except botocore.exceptions.ClientError as e:
        print(e.response['Error']['Message'])
        permission = False
    if not permission:
        return INVALID_RESPONSE
    ### Otherwise, it's valid, so update the table and return a success message.
    
    #change the used variable to True
    table.update_item(
        Key={
            'faceID': faceID,
            },
            UpdateExpression="set used=:u",
            ExpressionAttributeValues={
                ':u': True,
            },
    ReturnValues="UPDATED_NEW"
    )
    
    # Retrieve visitor information (to put into the webpage)(11)
    visitorsTable = dynamodb.Table('visitorsDB2')
    visitorResponse = visitorsTable.get_item(Key={'faceID': response['Item']['faceID']})
    print("dynamo response visitorsDB2:", visitorResponse)
    nameOfVisitor = visitorResponse['Item']['Name']
    
    return {
           'statusCode': 200,
           'headers': {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTION, POST, GET",
           },
           "body": {"name": nameOfVisitor}
        }

			
def lambda_handler(event, context):
    
    print("Event:", event)
    otpInput = event['otp']
    faceID = event['faceID']
    
    #Validate OTP (10)
    validationResponse = validateOTP(otpInput, faceID)
    

    return validationResponse