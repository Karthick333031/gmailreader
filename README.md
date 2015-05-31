# gmailreader
Reads gmail automatically and stores it in a mysql database for analysis later
This is a very simple wrapper on top of gmail python package [ which internally wraps email package! ].
For mobile notifications, pushbullet is used.

## Use case
I had to analyze lot of feedbacks mailed. Volume of mails were high and to ensure I don't miss anything, I wrote this simple wrapper.

I intend to use NLTK on top of the subject/content/emails collected to understand the themes and sentiments associated with the feedback emails.

## References
1. http://www.voidynullness.net/blog/2013/07/25/gmail-email-with-python-via-imap/
2. https://github.com/charlierguo/gmail 

### Pre-requisites to install & configure

1. easy_install ConfigParser

2. Install gmail from the link below
>> https://github.com/charlierguo/gmail
>> Note: pygmail package is available

3. Install and configure PushBullet [ If Mobile notifications are required ]
>> pip install pushbullet.py
>> Note: push_sms function is untested. Use with care

### Job Sequence :
 0. Create a MySQL table for storing the contents read from maildata

>> create table maildata ( ind INT AUTO_INCREMENT, mdate datetime, mfrom varchar(255), recepients varchar(255), subject varchar(1024), category varchar(20), content varchar(4096), has_attachment varchar(20), PRIMARY KEY (ind) )

 1. Enter the configuration details in .mailsettings 

 2. Run python gmailreader.py

 3. Logs are automatically stored in mailreader-log/gmail-reader.log

 4. Configure the gmail reader as a cron job for automated reads!

