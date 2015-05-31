# coding: utf-8
#! /usr/bin/env python

########################################################################################
#
#    Program : Automated Gmail Reader
#    Description : Reads your Gmail and extracts info
# 
########################################################################################

# Reference blog post : 
# http://www.voidynullness.net/blog/2013/07/25/gmail-email-with-python-via-imap/
# https://github.com/charlierguo/gmail

# Import libraries

import os, sys
import datetime
import json
import logging
import logging.handlers
import json
import ConfigParser
import MySQLdb
import gmail

# *********************************************************
# Start Logging
# *********************************************************

# Create Log Base dir if not present

logbasedir= os.path.join(os.getcwd(), 'mailreader-log')
if not os.path.exists(logbasedir):
    os.makedirs(logbasedir)

# Instantiate Logging

LOG_FILENAME=os.path.join(logbasedir, 'gmail-reader.log')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Log rotated for every 10mb and perenially stored
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)

# Pushbullet for Mobile Notification
from pushbullet import PushBullet

apiKey = "<Enter Pushbullet Key here>"
p = PushBullet(apiKey)
devices = p.devices

def open_connection(verbose=False):
    # Read the config file
    config = ConfigParser.ConfigParser()
    config.read('./.mailsettings')

    #mysql data
    mysqldata={}
    mysqldata['hostname'] = config.get('mysql', 'hostname')
    mysqldata['username'] = config.get('mysql', 'username')
    mysqldata['password'] = config.get('mysql', 'password')
    mysqldata['database'] = config.get('mysql', 'database')
    mysqldata['port'] = int(config.get('mysql', 'port'))
 
    # Login to our account
    username = config.get('account', 'username')
    password = config.get('account', 'password')
    folders = config.get('folders', 'mailbox')
    fromdate = config.get('folders', 'fromdate')
    todate = config.get('folders', 'todate')


    if username is '':
      logger.error("Enter Username in config")
      sys.exit(1)

    if password is '':
      logger.error("Enter Password in config")
      sys.exit(1)

    if folders is '':
      logger.warn("Set of folders is none. So setting it to Inbox")

    if fromdate is '':
      logger.warn("From date is none. So setting fromdate and todate to current date")
      now = datetime.datetime.now()
      fromdate = now.strftime("%Y-%m-%d")
      todate = fromdate

    #if todate is '':
      #now = datetime.datetime.now()
      #todate = now.strftime("%Y-%m-%d")
      

    for k, v in mysqldata.iteritems():
        if v is None:
            logger.error("mysqldata Key: " + k + " is None")
            sys.exit(1)

    if verbose: logger.info('Logging in as ' + username)

    connection = gmail.login(username, password)

    logger.info("Connection: " + str(connection))
    logger.info("Folders: " + folders)
    logger.info("FromDate: " + fromdate)
    logger.info("ToDate: " + todate)
    return connection, folders, fromdate, todate, mysqldata

# *********************************************************
# Database Helper Function
# *********************************************************

def insert_report_log(reportlistdata, mysqldata): 
    
    flag = True

    try:

       # Insert log entry into maildata table
      insertdatasql = "INSERT into maildata (mdate, mfrom, recepients, subject, category, content, has_attachment) VALUES (\"" \
                             + reportlistdata['mdate'] + "\",\""  \
                             + reportlistdata['mfrom'] + "\",\"" \
                             + reportlistdata['recepients'] + "\",\"" \
                             + reportlistdata['subject'] + "\",\"" \
                             + reportlistdata['category'] + "\",\"" \
                             + reportlistdata['content'] + "\",\"" \
                             + reportlistdata['has_attachment'] \
                             + "\")"
        #logger.info(insertdatasql)

        # Connect to DB
        db = MySQLdb.connect(mysqldata['hostname'], mysqldata['username'], mysqldata['password'], mysqldata['database'], mysqldata['port'])

        # Prepare a cursor object using cursor() method
        cursor = db.cursor()

        # Execute the get rows SQL command
        cursor.execute(insertdatasql)
       
        db.commit()
        # disconnect from server
        cursor.close()
        db.close()

    except Exception as e:
        flag = False
        logger.error(str(e))

    return flag

# *********************************************************
# Helper functions
# *********************************************************

def process_mailbox(connection, mbox, fromdate, todate, mysqldata):
    data = None
    if todate is not '':
        #data = connection.mailbox(mbox).mail(after=datetime.datetime.strptime(fromdate, '%Y-%m-%d'), before=datetime.datetime.strptime(todate, '%Y-%m-%d'))
        data = connection.mailbox(mbox).mail(unread=True, after=datetime.datetime.strptime(fromdate, '%Y-%m-%d'), before=datetime.datetime.strptime(todate, '%Y-%m-%d'))
    else:
        #data = connection.mailbox(mbox).mail(after=datetime.datetime.strptime(fromdate, '%Y-%m-%d'))
        data = connection.mailbox(mbox).mail(unread=True, after=datetime.datetime.strptime(fromdate, '%Y-%m-%d'))
    if data is None or data is '':
        logger.info("No messages found!")
        return False

    for d in data:
      
      rldatadict = {}
      d.fetch()
      try:
          rldatadict['id'] = d.message_id
          rldatadict['mdate'] = d.sent_at.strftime("%Y-%m-%d %H:%M:%S")
          rldatadict['mfrom'] = d.fr.replace(',', '|').replace('\n',' ').replace('\n',' ').replace('"', "[quote]")
          if d.cc is None:
              rldatadict['recepients'] = d.to.replace(',', '|').replace('\n',' ').replace('"', "[quote]")
          else:
              rldatadict['recepients'] = d.to.replace(',', '|').replace('\n',' ').replace('"', "[quote]") + "|" + d.cc.replace(',', '|').replace('\n',' ').replace('"', "[quote]")
          rldatadict['subject'] = d.subject.decode('utf-8', 'ignore').replace('\r',' ').replace('\n',' ').replace(',', '[comma]').replace('"', "[quote]")
          if (("Re:" in rldatadict['subject']) or ("RE:" in rldatadict['subject'])) :
              rldatadict['category'] = "Replies"
          elif "Alert" in rldatadict['subject']:
              rldatadict['category'] = "Alert"
              p.push_note(rldatadict['subject'], rldatadict['subject'])
          #   p.push_sms(devices[0], <phone number>, rldatadict['subject'])
          else:
              rldatadict['category'] = "NULL"
          if d.body is None:
              rldatadict['content'] = "NULL"
          else:
              rldatadict['content'] = d.body.decode('utf-8', 'ignore').replace('\r',' ').replace('\n',' ').replace(',', '[comma]').replace('"', "[quote]")
             # print rldatadict['content']
          if d.attachments is not None:
             rldatadict['has_attachment'] = "Y"
          else:
            rldatadict['has_attachment'] = "N"
          for k, v in rldatadict.iteritems():
            if v is None:
              logger.warn("rldatadict Key: " + k + " is None")
              rldatadict[k] = "NULL"
          logger.info('MessageId: ' + str(rldatadict['id']) + "|" + ' Date: ' + rldatadict['mdate'] + '|' + ' Subject: ' + rldatadict['subject'] + '|' + ' Recepients: ' + rldatadict['recepients'])
          resp = insert_report_log(rldatadict, mysqldata)
          if resp:
              logger.info("Inserted into maildata table successfully")
          else:
              logger.error("Insert failed for:" + json.dumps(rldatadict))
          d.read()

      except Exception as e:
          logger.error("**********ERRROR*************")
          logger.error(str(e))
          logger.error("Gmail processing failed for Messageid: " + d.message_id + " | Date: " + d.sent_at.strftime("%Y-%m-%d %H:%M:%S") + "| From: " + d.fr.replace(',', '|').replace('\n',' ').replace('\n',' ').replace('"', "[quote]"))
          logger.error("**********ERRROR*************")
          continue
    return True
# Main Function

if __name__ == '__main__':
    connection, folders, fromdate, todate, mysqldata = open_connection(verbose=True)
    try:
        logger.info('List of mail box folders to be read: ' + folders)
        folder_list = folders.split(',')
        for mbox in folder_list:
          logger.info('Reading Mail box: ' + mbox)
          flag = process_mailbox(connection, mbox, fromdate, todate, mysqldata)
          if flag:
            logger.info("successfully Completed reading gmail!")
          else:
            logger.error("Reading Gmail Unsuccessful!")
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
    finally:
        connection.logout()


