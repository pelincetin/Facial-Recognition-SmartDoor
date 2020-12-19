import os
### AWS:
import boto3
from boto3.dynamodb.conditions import Key

import json
import base64
import random
import datetime 
import time

import cv2
import numpy as np


AUTHORIZED_IMAGE_BUCKET = "b1-photos-visitors"
UNAUTHORIZED_IMAGE_BUCKET = "unauthorized-visitors"
FRONTEND_BUCKET = "coms6998-hw2-frontend"
ADMIN_PHONE_NUMBER = "+1_PutNumberHere"

###################################################################################################

### Stream/image processing.

###################################################################################################

def alreadyProcessedCurrentUnauthorizedPerson():
	'''
	Check if the current person, who is unauthorized, has already been processed.
	If so, their image is in the S3 bucket and their face is in Rekognition.
	'''
	collectionId='newVisitors'
	fileName='unauthorized.jpg'
	threshold = 90
	maxFaces=2
	client=boto3.client('rekognition')
	response=client.search_faces_by_image(CollectionId=collectionId,
								Image={'S3Object':{'Bucket':UNAUTHORIZED_IMAGE_BUCKET,'Name':fileName}},
								FaceMatchThreshold=threshold,
								MaxFaces=maxFaces)
	faceMatches=response['FaceMatches']
	### If there's anything in faceMatches, then it's pretty confident that it's a match.
	### If it's empty, then we haven't processed this new visitor before.
	return len(faceMatches) > 0
		
		
def getImageFromStream():
	### Reshma's code: extract picture.
	payload = get_byte_stream_from_kinesis()
	fileName = writePayloadToFile(payload)
	image = getImageFromFile(fileName)
	print("image:", image)
	if image is None:
		print ("No image found. Are you sure Kinesis is running?")
		return
	return image

def addUnauthorizedImageToCollection():
	
	client=boto3.client('rekognition')
	response=client.index_faces(CollectionId="newVisitors",
								Image={'S3Object':{'Bucket':"unauthorized-visitors",'Name':"unauthorized.jpg"}},
								ExternalImageId="unauthorized",
								MaxFaces=1,
								QualityFilter="AUTO",
								DetectionAttributes=['ALL'])	
	print ("rekognition response:")
	print(response)
	faceID = response["FaceRecords"][0]["Face"]["FaceId"] #response["FaceSearchResponse"][0]["MatchedFaces"][0]["Face"]["FaceId"]
	print("faceID:", faceID)
	return faceID
	
def writeImageToS3(bucket, image, fileName):
	### Save picture to S3
	# https://stackoverflow.com/a/56593242
	print("encoding image")
	image_string = cv2.imencode('.jpg', image)[1].tostring()
	print("writing to S3")
	s3 = boto3.client('s3', region_name='us-east-1')
	s3.put_object(Bucket=bucket, Key = fileName, Body=image_string)
	print("done")	
	

###################################################################################################

### New users.

###################################################################################################

## For testing; get "unauthorized.jpg"
def getTestImageFromS3():
	s3 = boto3.resource('s3', region_name='us-east-1')
	bucket = s3.Bucket(UNAUTHORIZED_IMAGE_BUCKET)
	img = bucket.Object("unauthorized.jpg").get().get('Body').read()
	nparray = cv2.imdecode(np.asarray(bytearray(img)), cv2.IMREAD_COLOR)
	photo = nparray
	return photo	
	
	
def processNewVisitor():
	'''
	When we get an unknown visitor, take a screenshot of them. Store the photo in the Rekognition collection.
	
	Contact administrator: send them photo of the person. If approved, collect their name and number.
	Then, using their faceID, send them through the normal route of OTP -> access.
	'''
	### Uncomment this part when done testing:
	print("getting image")
	image = getImageFromStream()
	print ("writing dummy image")
	writeImageToS3(UNAUTHORIZED_IMAGE_BUCKET, image, fileName = "unauthorized.jpg") # garbo write

	# For testing purposes, if kinesis isn't running:
	# image = getTestImageFromS3()

	### Check if already seen this unauthorized face, so that this isn't triggered
	### multiple times a second.
	if alreadyProcessedCurrentUnauthorizedPerson():
		return
	else:
		print ("adding unknown image to Rekognition")
		faceID = addUnauthorizedImageToCollection()
		currentTime = datetime.datetime.now().strftime("%Y-%m-%d:%H-%M-%S")
		fileName = "{}_{}.jpg".format(faceID, currentTime)
		print("writing final image to s3")
		writeImageToS3(UNAUTHORIZED_IMAGE_BUCKET, image, fileName) # real write
		frontendFileName = "images/unauthorized/{}.jpg".format(faceID)
		writeImageToS3(FRONTEND_BUCKET, image, frontendFileName)
		print ("asking owner for authorization")
		askOwnerToAuthorizeUser(faceID)
		

### Reshma code:
def get_byte_stream_from_kinesis():
	
	print("Running Reshma's code:")
	STREAM_ARN = "arn:aws:kinesisvideo:us-east-1:875021110712:stream/KVS1/1604792887592"
	kinesis_client = boto3.client('kinesisvideo', region_name='us-east-1')
	response = kinesis_client.get_data_endpoint(
		StreamARN=STREAM_ARN,
		APIName="GET_MEDIA"
		)
	print("getting kinesis")
	video_client = boto3.client(
		"kinesis-video-media", 
		endpoint_url=response['DataEndpoint'], 
		region_name="us-east-1")
	print("getting video")
	response = video_client.get_media(
		StreamARN=STREAM_ARN, 
		StartSelector={'StartSelectorType': 'NOW'}
		)
	print("getting response")
	print("response:", response.keys())
	payload=response["Payload"]
	print("payload:", payload)
	
	return payload

def writePayloadToFile(payload):
# https://stackoverflow.com/a/60984632
	print("starting to write")
	currentTime = datetime.datetime.now().strftime("%Y-%m-%d:%H-%M-%S")
	fileName = '/tmp/payload_{}.mkv'.format(currentTime)
	with open(fileName, 'wb+') as f:
		numBytes = 1024
		chunk = payload.read(1024*8)
		# while chunk:
		for byte in range(numBytes):
			f.write(chunk)
			chunk = payload.read(1024*8)
	print ("done writing")
	return fileName

def getImageFromFile(fileName):
	vidcap = cv2.VideoCapture(fileName)
	success, image = vidcap.read()
	return image

def askOwnerToAuthorizeUser(faceID):
	
	text_message = "You have a visitor! Please go to "
	text_message += "http://coms6998-hw2-frontend.s3-website-us-east-1.amazonaws.com/WP1.html?faceID={}".format(faceID)
	text_message += " to authorize them."
	sendSMS(phoneNumber = ADMIN_PHONE_NUMBER, text_message = text_message)
	
	

###################################################################################################

### Standard process for all users:

###################################################################################################	
		
def checkIfAlreadyTexted(faceID):
	
	dynamodb = boto3.resource('dynamodb')
	table = dynamodb.Table('passcodesDB1')
	try:
		response = table.get_item(Key={'faceID': faceID})
		print("OTP response:", response)
		if "Item" in response:
			print ("Already texted")
			return True
		else:
			print ("Not already texted")
			return False
	except botocore.exceptions.ClientError as e:
		print("Not already texted")
		return False
	
	
def getPhoneNumberFromFaceID(faceID):
	'''
	Query DynamoDB for user info.
	
	args:
		faceID (str): User's unique face ID.
	returns:
		phoneNumber (str): 
	'''

	dynamodb = boto3.resource('dynamodb',region_name='us-east-1') 

	table = dynamodb.Table('visitorsDB2')
	
	response = table.scan(
	FilterExpression=Key('faceID').eq(faceID)
	)
	### If not found:
	if len(response["Items"]) == 0:
		
		print("No numbers found.")
	return response['Items'][0]["phoneNum"]
	
	
ALPHABET = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
PASSWORD_LENGTH = 5
PASSCODE_EXPIRY_TIME = 5 ## Only last for 5 minutes.

def makeOneTimePassword():
	'''
	Generate a random sequence.
	returns:
		Random passcode.
	'''
	
	return "".join(random.choices(ALPHABET, k = PASSWORD_LENGTH))

def makeAndSaveOneTimePasscode(faceID):
	'''
	Create the OTP, save it to the DB, return it.
	'''
	
	passcode = makeOneTimePassword()
	### 5 minutes from now:
	expireTime = datetime.datetime.today() + datetime.timedelta(minutes=PASSCODE_EXPIRY_TIME)
	### Format:
	formattedExpireTime = str(time.mktime(expireTime.timetuple())) 
	dynamodb = boto3.client('dynamodb') 
	dynamodb.put_item(
		TableName = 'passcodesDB1',
		Item = {
			'AccessCode': { 'S': passcode },
			'ttl': { 'N': str(formattedExpireTime) },
			'faceID': { 'S': faceID },
			'used': { 'BOOL': False}
		})
	return passcode
	
def sendSMS(phoneNumber, text_message):
	'''
	Generic text message function.
	'''
	print ("texting {} this message: {}".format(phoneNumber, text_message))
	sns_client = boto3.client('sns')
	response = sns_client.publish(
			PhoneNumber=phoneNumber,
		Message=text_message,
	)
	print("text message response:", response)
	return
	
	

def sendOneTimePassword(faceID):
	
	### Get phone number.
	print("getting number")
	phoneNumber = getPhoneNumberFromFaceID(faceID)
	print ("phone number is:", phoneNumber)
	passcode = makeAndSaveOneTimePasscode(faceID)
	
	### Send them the password
	otpPageURL = "http://coms6998-hw2-frontend.s3-website-us-east-1.amazonaws.com/WP2.html?faceID={f}".format(f = faceID)
	textMessage = "Your one time password is {}. Log in from {}.".format(passcode, otpPageURL)
	print("textMessage:", textMessage)
	sendSMS(phoneNumber, textMessage)
	return

def appendImageInfoToDB(faceID, fileName, currentTime):
	dynamodb = boto3.resource('dynamodb')
	table = dynamodb.Table("visitorsDB2")
	result = table.update_item(
	    Key={
	        'faceID': faceID,
	    },
	    UpdateExpression="SET photos = list_append(photos, :i)",
	    ExpressionAttributeValues={
	        ':i': [{
	        	"objectKey": fileName,
	        	"bucket": AUTHORIZED_IMAGE_BUCKET,
	        	"createdTimestamp": currentTime
	        }],
	    },
	    ReturnValues="UPDATED_NEW"
	)
	return

def lambda_handler(event, context):
	

	data_raw = event['Records'][0]['kinesis']['data']
	### Testing:
	'''
	data_raw = {
	"Records": [
		{
		  "kinesis": {
			"kinesisSchemaVersion": "1.0",
			"partitionKey": "036be6a5-5893-4d9f-9798-b99abf03002b",
			"sequenceNumber": "49612556404849341751321948912022266895104601742911733938",
			"data": "eyJJbnB1dEluZm9ybWF0aW9uIjp7IktpbmVzaXNWaWRlbyI6eyJTdHJlYW1Bcm4iOiJhcm46YXdzOmtpbmVzaXN2aWRlbzp1cy1lYXN0LTE6ODc1MDIxMTEwNzEyOnN0cmVhbS9LVlMxLzE2MDQ3OTI4ODc1OTIiLCJGcmFnbWVudE51bWJlciI6IjkxMzQzODUyMzMzMTgxNDY3MTI5Mjc5NTY0OTgwNTUzMDk4MjgyMjE5NzM5MDAwIiwiU2VydmVyVGltZXN0YW1wIjoxLjYwNTEyODQwMjk1RTksIlByb2R1Y2VyVGltZXN0YW1wIjoxLjYwNTEyODM5OTQ2M0U5LCJGcmFtZU9mZnNldEluU2Vjb25kcyI6MS43NjE5OTk5NjQ3MTQwNTAzfX0sIlN0cmVhbVByb2Nlc3NvckluZm9ybWF0aW9uIjp7IlN0YXR1cyI6IlJVTk5JTkcifSwiRmFjZVNlYXJjaFJlc3BvbnNlIjpbeyJEZXRlY3RlZEZhY2UiOnsiQm91bmRpbmdCb3giOnsiSGVpZ2h0IjowLjQyNDg3NjQ4LCJXaWR0aCI6MC4xOTgxOTE3MywiTGVmdCI6MC40MTMxNDE1NSwiVG9wIjowLjU5OTE5NzJ9LCJDb25maWRlbmNlIjo5OS45OTg1MSwiTGFuZG1hcmtzIjpbeyJYIjowLjQ3MTU4MjIzLCJZIjowLjc1Nzk4NjEsIlR5cGUiOiJleWVMZWZ0In0seyJYIjowLjU2MDA5MDEsIlkiOjAuNzYxMzc4OCwiVHlwZSI6ImV5ZVJpZ2h0In0seyJYIjowLjQ3ODM3Nzg4LCJZIjowLjk1MjUwNzEsIlR5cGUiOiJtb3V0aExlZnQifSx7IlgiOjAuNTUyMTk4NSwiWSI6MC45NTUyOTEsIlR5cGUiOiJtb3V0aFJpZ2h0In0seyJYIjowLjUxMzg4MTU2LCJZIjowLjg2NDQxNzk3LCJUeXBlIjoibm9zZSJ9XSwiUG9zZSI6eyJQaXRjaCI6MS4xNTA0NDE1LCJSb2xsIjowLjg4NjQ4NzUsIllhdyI6LTAuNDUwNTc3NH0sIlF1YWxpdHkiOnsiQnJpZ2h0bmVzcyI6NzAuNDQ3OCwiU2hhcnBuZXNzIjo4Ni44NjAxOX19LCJNYXRjaGVkRmFjZXMiOlt7IlNpbWlsYXJpdHkiOjk5Ljg5NjIzLCJGYWNlIjp7IkJvdW5kaW5nQm94Ijp7IkhlaWdodCI6MC4zMjY4MDYsIldpZHRoIjowLjI5OTA0LCJMZWZ0IjowLjM3MDkyLCJUb3AiOjAuMjI1ODU3fSwiRmFjZUlkIjoiM2VhMzg4NjItMzA3OS00MWZhLTk4ODktMGE0MzE3M2U4YjBhIiwiQ29uZmlkZW5jZSI6OTkuOTk3OSwiSW1hZ2VJZCI6ImQ1Zjg0MmRmLTU3OGYtMzEzMC1hZDFjLWY5Y2FkODJjOGU4ZSIsIkV4dGVybmFsSW1hZ2VJZCI6ImFsZXhzLWZhbmN5LXBob3RvIn19LHsiU2ltaWxhcml0eSI6OTguNzY2MTA2LCJGYWNlIjp7IkJvdW5kaW5nQm94Ijp7IkhlaWdodCI6MC43NzM2NDgsIldpZHRoIjowLjUwMzExMywiTGVmdCI6MC4yNjE1ODUsIlRvcCI6MC4xMjQ0MzV9LCJGYWNlSWQiOiI4YzkxNjkzZi1lNTlmLTRhZmYtOTA1Ny1kZTZlMmM3NmY2YzIiLCJDb25maWRlbmNlIjo5OS45OTk3OTQsIkltYWdlSWQiOiI1MWJjYzM3Yi02MGYxLTM2ZTctOTg4ZS1lZjU0MmI0NjI3YzAiLCJFeHRlcm5hbEltYWdlSWQiOiJhbGV4cy1mYi1waG90byJ9fV19XX0=",
			"approximateArrivalTimestamp": 1605128405.381
		  },
		  "eventSource": "aws:kinesis",
		  "eventVersion": "1.0",
		  "eventID": "shardId-000000000011:49612556404849341751321948912022266895104601742911733938",
		  "eventName": "aws:kinesis:record",
		  "invokeIdentityArn": "arn:aws:iam::875021110712:role/service-role/analyzeFace-role-sab4636m",
		  "awsRegion": "us-east-1",
		  "eventSourceARN": "arn:aws:kinesis:us-east-1:875021110712:stream/facesSeen"
		}
	  ]
	}
	'''
	data_str = base64.b64decode(data_raw).decode('ASCII')
	data = json.loads(data_str)
	print("data: ", str(data))
	matchedFaces = data["FaceSearchResponse"][0]["MatchedFaces"]
	
	### if not in collection (unknown user):
	if len(matchedFaces) == 0:
	
		print("unknown user")
		processNewVisitor()
		
	### If known/authorized user:
	else:
		### Take most similar face:
		print("known user")
		faceID = matchedFaces[0]["Face"]["FaceId"]

		# Check if the faceID is in the OTP DynamoDB table.
		# If so, do nothing - we've already texted the user.
		alreadyTexted = checkIfAlreadyTexted(faceID)
		if alreadyTexted:
			pass
		# Otherwise, create OTP for them, add (OTP, faceID, timestamp) to table, and text them.
		else:
			print("Making and saving OTP")
			passcode = makeAndSaveOneTimePasscode(faceID)
			phoneNum = getPhoneNumberFromFaceID(faceID)
			sendOneTimePassword(faceID)
			
			### commented for testing:
			image = getImageFromStream()
			### testing:
			# image = getTestImageFromS3()
			
			print("start image:")
			print("done image")
			currentTime = datetime.datetime.now().strftime("%Y-%m-%d:%H-%M-%S")
			fileName = "{}_{}.jpg".format(faceID, currentTime)
			writeImageToS3(AUTHORIZED_IMAGE_BUCKET, image, fileName)
			# TODO add the info to the photos column
			appendImageInfoToDB(faceID, fileName, currentTime)
	
	return {
		'statusCode': 200,
		'body': json.dumps('Hello from Lambda!')
	}
