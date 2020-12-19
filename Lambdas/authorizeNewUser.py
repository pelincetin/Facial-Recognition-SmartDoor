import json
import datetime
import boto3
import random
import time


ALPHABET = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
PASSWORD_LENGTH = 5
PASSCODE_EXPIRY_TIME = 5 ## Only last for 5 minutes.
AUTHORIZED_IMAGE_BUCKET = "b1-photos-visitors"
FRONTEND_BUCKET = "coms6998-hw2-frontend"

def getFileFromS3(bucket, imageName):
	'''
	Get photo for processing.
	'''
	s3 = boto3.client('s3', region_name='us-east-1')
	photo = s3.get_object(Bucket=bucket, Key = imageName)
	return photo

### This lambda is triggered when the owner approves a new user.
### So we save their info in our approved visitors table, and 
### can easily access their info next time.
# (6)
def saveAuthorizedUserToDB(name, phoneNum, faceID):
	##put entry into visitors db
	
	currentTime = datetime.datetime.now().strftime("%Y-%m-%d:%H-%M-%S")
	dynamodb = boto3.client('dynamodb') 
	dynamodb.put_item(
		TableName = 'visitorsDB2',
		Item = {
			'faceID': { 'S': faceID },
			'Name': { 'S': name },
			'phoneNum': { 'S': phoneNum },
			'photos': { "L": [{"M": {"objectKey": {"S": "{}_{}.jpg".format(faceID, currentTime) },
				"bucket": {"S": "b1-photos-visitors"},
				"createdTimestamp": {"S": currentTime}
							}}]
					}
			}
		)
	return

def saveImageToS3(oldFaceID, newFaceID):
	'''
	Write the original screenshotted image, to the authorized visitor bucket.
	'''	
	imageName = "images/unauthorized/{}.jpg".format(oldFaceID)
	photo = getFileFromS3(bucket = FRONTEND_BUCKET, imageName = imageName)
	print("photo from s3:", photo)
	
	currentTime = datetime.datetime.now().strftime("%Y-%m-%d:%H-%M-%S")
	imageName = "images/{}_{}.jpg".format(newFaceID, currentTime)
	s3 = boto3.client('s3', region_name='us-east-1')
	photo = s3.put_object(Bucket=AUTHORIZED_IMAGE_BUCKET, Key = imageName)
	return
	
	
##put face into auth collection
def addAuthorizedUserToCollection(oldFaceID):
	'''
	This faceID is the one from the original, unknown users collection.
	"faces" is the authorized users collection.
	'''
	client=boto3.client('rekognition')
	response=client.index_faces(CollectionId="faces",
								Image={'S3Object':{'Bucket':"coms6998-hw2-frontend",'Name':"images/unauthorized/{}.jpg".format(oldFaceID)}},
								ExternalImageId=oldFaceID,
								MaxFaces=1,
								QualityFilter="AUTO",
								DetectionAttributes=['ALL'])
	newFaceID = response['FaceRecords'][0]['Face']['FaceId']
	return newFaceID

def processAuthorizedUser(name, phoneNum, oldFaceID):
	'''
	Run a few steps.
	'''
	newFaceID = addAuthorizedUserToCollection(oldFaceID)
	saveImageToS3(oldFaceID, newFaceID)
	saveAuthorizedUserToDB(name, phoneNum, newFaceID)
	return newFaceID
	
def makeAndSaveOneTimePasscode(newFaceID):
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
			'faceID': { 'S': newFaceID },
			'used': { 'BOOL': False}
		})
	return passcode

def makeOneTimePassword():
	'''
	Generate a random sequence.
	returns:
		Random passcode.
	'''
	
	return "".join(random.choices(ALPHABET, k = PASSWORD_LENGTH))

def sendSMS(phoneNumber, text_message):
	'''
	Generic text message function.
	'''
	if phoneNumber[0] != "+":
		phoneNumber = "+" + phoneNumber
		
	sns_client = boto3.client('sns')
	response = sns_client.publish(
			PhoneNumber=phoneNumber,
		Message=text_message,
	)
	
	return
	
def textUser(phoneNumber, newFaceID, passcode):
	
	webpage2url = "http://coms6998-hw2-frontend.s3-website-us-east-1.amazonaws.com/WP2.html?faceID={f}".format(f = newFaceID)
	textMessage = "Your one time password is {}. Log in from {}.".format(passcode, webpage2url)
	print("textMessage:", textMessage)
	sendSMS(phoneNumber, textMessage)
	
def lambda_handler(event, context):
	
	### Uncommented for testing:
	print ("event:", event)
	phoneNum = event['phone_number']
	print("Retrieved phone:", phoneNum)
	name = event['name']
	print("Retrieved name:", name)
	oldFaceID = event["faceID"]
	
	### Testing with Chris Hemsworth:
	# oldFaceID = "a7be5274-9346-4ee7-9450-b00dddd1c521"
	# phoneNum = "+16097211147"
	# name = "Alex Atschinow"


	# (6) Process authorized user:
	print ("step 6")
	newFaceID = processAuthorizedUser(name, phoneNum, oldFaceID)
	
	#store OTP (7)
	print ("step 7")
	passcode = makeAndSaveOneTimePasscode(newFaceID)
		
	#Send SMS with OTP (8)
	print ("step 8")
	textUser(phoneNum, newFaceID, passcode)
	
	return {
		'statusCode': 200,
		'body': json.dumps('Hello from Lambda!')
	}


