from flask import request, send_from_directory, render_template, render_template_string
from app import app
import pandas as pd
import os
import requests
import datetime

#this is code that gets triggered from the html site at the bottom of this code, it allows you to download the template via link
@app.route('/downloadsafe')
def downloadsafe():
    path = "BatchPAUpdater Template.xlsx"
    return send_from_directory('templates', path, as_attachment=True)
    
@app.route("/BatchPAUpdaterGuardrails", methods=['GET', 'POST'])
def BatchPAUpdaterGuardrails():
    #this starts the function, what gets triggered when you click 'update'
    if request.method == 'POST':
        #pull ip address of user 
        ip_addr = request.remote_addr
        print('Your IP address is:' + ip_addr)
        
        #file that gets uploaded
        print(request.files['file'])
        f = request.files['file']
        
        #create a dictionary of uploaded values (index is case ID#)
        df = pd.read_excel(f)
        dfDict = df.set_index('LegalServer Case ID').T.to_dict('list')
        
        #assigning variables that let us access LegalServer via API - hi, Nate!
        QueryURL = "https://lsnyc.legalserver.org/api/v1/matters"
        headers = {'Authorization': "Bearer ************"}
        
        #create empty dataframe to hold archive values of fields before they get overwritten
        dfBackup = pd.DataFrame()
        dfBackup['LegalServer Case ID'] = ''
        dfBackup['OriginalPANum'] = ''
        dfBackup['User IP Address'] = ''


        for CaseID in dfDict:
            
            #Ecah case has to have an API request based on Case ID# to pull its Universally Unique ID (uuid) that lets us access custom fields and patch things later                       
            querystring = {"case_number":CaseID}
            
            #this is the part that actually implements the API request
            r = requests.request("GET", QueryURL, headers=headers, params=querystring)
            print(r)
            
            #turn the API result into a dictionary we can pull values from
            JSONDict = r.json()
            caseUUID = JSONDict['data'][0]['matter_uuid']
            print(caseUUID)
            
            #start the next API query to pull the specific variables based on UUID
            QueryURL2 = 'https://lsnyc.legalserver.org/api/v1/matters/'+caseUUID

            #this is the part of the API call that tells it we need this custom field back
            payload = {"custom_fields": ["gen_pub_assist_case_number_75"]}
            
            #implement API request
            r = requests.request("GET", QueryURL2, json=payload, headers=headers)
            
            #pull API request results into a dictionary and then extract PA number
            DataDict = r.json()
            PANum = DataDict['data']["gen_pub_assist_case_number_75"]
            print(PANum)
            
            #make a list of the values we need to archive for each case ID being modified
            CaseEntryList = (CaseID,PANum,ip_addr)
            #turn that list into a dataframe that we can append to the backup dataframe
            dfCaseEntry = pd.DataFrame([CaseEntryList],columns=['LegalServer Case ID','OriginalPANum','User IP Address'])
            #add record to the backup archive before moving onto the next Case ID
            dfBackup = pd.concat([dfBackup,dfCaseEntry],ignore_index=True)

        print(dfBackup)
        #pull current time so that each archive file has a unique name
        timeID = datetime.datetime.now().strftime("%Y%m%d%I%M%S")
        output_filename = timeID + ' PANum Backup'
        
        #send the backup dataframe to an excel file in the flask file folder
        writer = pd.ExcelWriter("app\\APIbackups\\"+output_filename + '.xlsx', engine = 'xlsxwriter')
        dfBackup.to_excel(writer, sheet_name='Sheet1',index=False)
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        worksheet.set_column('A:C',20)
        writer.close()
        print('backup sheet successful')

       

        #now that we have an backup archive made, we can start actually uploading new data
        for CaseID in dfDict:
            #same as above, look up UUID by case number via API call   
            querystring = {"case_number":CaseID}
            r = requests.request("GET", QueryURL, headers=headers, params=querystring)
            JSONDict = r.json()
            caseUUID = JSONDict['data'][0]['matter_uuid']
            print(caseUUID)
            
            #once you have the UUID, run a 'patch' API call that uploads new values based on original spreadsheet uploaded
            PatchURL = 'https://lsnyc.legalserver.org/api/v1/matters/'+caseUUID
            #this is ugly, but it's how we have to refer to 'custom' fields in LegalServer
            params = {
                      "custom_fields":
                          "{\"gen_pub_assist_case_number_75\":\""+str(dfDict[CaseID][0]) + "\"}",
                      }
            r = requests.patch(PatchURL, params = params, headers = headers)
            print(r)
            print('patch successful')
            
            #Add case notes via legacy API
            
            Noteurl = "https://lsnyc.legalserver.org/matter/api/create_case_note/"

            NoteToEnter = "Remote API Access to LegalServer was used to update the PA Number for this case. The IP address of the user of this tool was: " + ip_addr + ", the pre-existing PANumber was: " + str(dfBackup[dfBackup['LegalServer Case ID'] ==  CaseID]['OriginalPANum'].values[0]) + ", and the newly entered value is: " + str(dfDict[CaseID][0]) + "."

            NOTEquerystring = {"case_number":CaseID,"note":NoteToEnter,"type":"General Notes","subject":"Case Data Updated via API"}

            notepayload = ""
            noteheaders = {
                'Accept': "application/json",
                'Authorization': "Bearer ***********"
                }

            response = requests.request("POST", Noteurl, data=notepayload, headers=noteheaders, params=NOTEquerystring)

            print(response.text)
        
        #this gives us a confirmation page so user knows their spreadsheet has been processed
        return render_template_string("""
            {% extends "base.html" %}
            {% block content %}
            <!doctype html>
            <title>Batch PA Updater</title>
            <h1>PA Numbers Updated!</h1>
            <a href="/">Home</a>
            {% endblock %} """)


    #HTML for the landing site and file uploader
    return render_template_string("""
            {% extends "base.html" %}
            {% block content %}
            <!doctype html>
            <title>Batch PA Updater</title>
            <h1>Upload PA Numbers in Batches:</h1>
            <form action="" method=post data-turbo="false" enctype=multipart/form-data>
            <p><input type=file name=file><input type=submit value=Update!>
            </form>
            <h3>Instructions:</h3>
            <ul type="disc">
            <li>WARNING - this tool will OVERWRITE PA numbers in LegalServer for any case numbers added - do not use this tool unless you know what you're doing.</li>
            <li>Enter your LegalServer case IDs and new PA numbers into <a href="{{url_for('downloadsafe')}}">this template</a>, and then upload the template into the 'Choose File' box above.</li>
            <li>Then click 'Update!', and please wait until this site confirms that PA numbers have been updated. </li>
            </ul>
            </br>
            <a href="/">Home</a>
            {% endblock %} """)
    
    
