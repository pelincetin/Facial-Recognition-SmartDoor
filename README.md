# COMS 6998 Cloud Computing Homework 2: Smart Door
### Alex Atschinow, Pelin Cetin, Myles Ingram, and Joseph Hostyk

Website that accesses a livestream to give access to approved users.

The admin has activated a Kinesis Video Stream and is livestreaming from their camera.

### Unknown User Protocol

A visitor steps into view. This triggers our first Lambda, which takes a screenshot and processes the user's face using Rekognition.
If they're a first-time visitor, they're added temporarily to a bucket for unauthorized users, and the admin is texted a link to a webpage to approve them:

<img src="https://github.com/pelincetin/Facial-Recognition-SmartDoor/blob/main/Demo/authorizeUser.png" alt="Your image title" width="400"/>

If the admin recognizes the visitor, they can enter the person's name and number, which will add them to a list of authorized users.

Now the visitor is approved, and can access the Known User Protocol.

### Known User Protocol

The livestream continues checking for faces. If Rekognition confirms that the person on camera is an approved user, their phone number is retrieved and they are texted both a link to a webpage, and a one-time passcode to ask for access:

<img src="https://github.com/pelincetin/Facial-Recognition-SmartDoor/blob/main/Demo/allowAccess.png" alt="Your image title" width="400"/>

If they correctly enter the passcode, they're given access:

<img src="https://github.com/pelincetin/Facial-Recognition-SmartDoor/blob/main/Demo/accessApproved.png" alt="Your image title" width="400"/>

If they try to use the same passcode again, or enter an incorrect one, they are denied.


