import json
import boto3
import os
import requests
from requests_aws4auth import AWS4Auth
from datetime import *

def lambda_handler(event, context):
    print("EVENT ---- {}".format(json.dumps(event)))
    #TESTING PIPELINE
    headers = {"Content-Type": "application/json"}
    
    s3 = boto3.client('s3')
    rek = boto3.client('rekognition')
    
    #Getting Image information from S3
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        size = record['s3']['object']['size']
        metadata = s3.head_object(Bucket=bucket, Key=key)
        
        print("-----meta-----", metadata)
        
        #print("-----KEY-----", key)
        #Detecting the label of the current image
        labels = rek.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': str(key)
                }
            },
            MaxLabels=10,
            MinConfidence=50
        )
        
        print("IMAGE LABELS---- {}".format(labels['Labels']))
        print("META DATA---- {}".format(metadata))
        
        if metadata["Metadata"]:
            customlabels = (metadata["Metadata"]["customlabels"]).split(",")
        
        #Prepare JSON object
        obj = {}
        obj['objectKey'] = key
        obj['bucket'] = bucket
        obj['createdTimestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obj['labels'] = []
        
        for label in labels['Labels']:
            obj['labels'].append(label['Name'])
            
        if metadata["Metadata"]:
            for c_labels in customlabels:
                c_labels = c_labels.strip()
                c_labels = c_labels.lower()
                if c_labels not in obj['labels']:
                    obj['labels'].append(c_labels)
                    
        print("FINAL LABELS -> ", obj['labels'])  #appends custom labels to final labels
            
        print("JSON OBJECT --- {}".format(obj))
        
        #Posting the JSON object into ElasticSearch, _id is automatically increased
        region = "us-east-1"
        service = "es"
        endpoint = 'https://search-photos-xhuxv4qwyxacqlbu7v3fpxkqky.us-east-1.es.amazonaws.com'
        credentials = boto3.Session(aws_access_key_id="",
                          aws_secret_access_key="", 
                          region_name="us-east-1").get_credentials()
        awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
        
        #OpenSearch domain endpoint with https://
        index = 'photos'
        type = 'photos'
        url = endpoint + '/' + index + '/' + type
        print("URL --- {}".format(url))
        
        obj = json.dumps(obj).encode("utf-8")
        req = requests.post(url, auth=awsauth, headers=headers, data=obj)
        print(req.text)
        print("Success: ", req)
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, PUT, OPTIONS'
            },
            'body': json.dumps("Image labels have been detected successfully!")
        }