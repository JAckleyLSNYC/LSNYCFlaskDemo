from flask import request, send_from_directory, render_template, render_template_string
from app import app
import pandas as pd
import os


@app.route("/Hyperlinker", methods=['GET', 'POST'])
def upload_hyperlink():
    #upload file from computer
    if request.method == 'POST':
        print(request.files['file'])
        f = request.files['file']
        
        #turn the excel file into a dataframe, but skip the top 2 rows if they are blank
        test = pd.read_excel(f)
        test.fillna('',inplace=True)
        if test.iloc[0][0] == '':
            df = pd.read_excel(f,skiprows=2,na_filter=False)
        else:
            df = pd.read_excel(f,na_filter=False)
        
        
        #apply hyperlink methodology with splicing and concatenation
      
        def NoIDDelete(CaseID):
            if CaseID == '':
                return 'No Case ID'
            else:
                return str(CaseID)
        df['Matter/Case ID#'] = df.apply(lambda x: NoIDDelete(x['Matter/Case ID#']), axis=1)
        
        last7 = df['Matter/Case ID#'].apply(lambda x: x[3:])
        CaseNum = df['Matter/Case ID#']
        df['Temp Hyperlinked Case #']='=HYPERLINK("https://lsnyc.legalserver.org/matter/dynamic-profile/view/'+last7+'",'+ '"' + CaseNum +'"' +')'
        del df['Matter/Case ID#']
        move=df['Temp Hyperlinked Case #']
        df.insert(0,'Hyperlinked Case #', move)           
        del df['Temp Hyperlinked Case #']
        
        
        #bounce worksheets back to excel
        output_filename = os.path.basename(f.filename)  
        writer = pd.ExcelWriter("app\\sheets\\"+output_filename, engine = 'xlsxwriter')
        df.to_excel(writer, sheet_name='Sheet1',index=False)
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        #create format that will make case #s look like links
        link_format = workbook.add_format({'font_color':'blue', 'bold':True, 'underline':True})
        
        #assign new format to column A
        worksheet.set_column('A:A',20,link_format)
        
        writer.close()
        
        #send file back to user
        return send_from_directory('sheets',output_filename, as_attachment = True, download_name = "Hyperlinked " + f.filename)

    return render_template_string("""
            {% extends "base.html" %}
            {% block content %}
            <!doctype html>
            <title>Hyperlinks</title>
            <h1>Add Hyperlinks to Report:</h1>
            <form action="" method=post data-turbo="false" enctype=multipart/form-data>
            <p><input type=file name=file><input type=submit value=Hyperlink!>
            </form>
            <h3>Instructions:</h3>
            <ul type="disc">
            <li>Browse your computer using the field above to find the LegalServer excel document that you want to add case hyperlinks to.</li> 
            <li>Once you have identified this file, click ‘Hyperlink!’ and you should shortly be given a prompt to either open the file directly or save the file to your computer.</li> 
            <li>When you first open the file, all case numbers will display as ‘0’ until you click “Enable Editing” in excel, this will populate the fields.</li> 
            <li>Note, the column with your case ID numbers in it must be titled "Matter/Case ID#" or "id" for this to work.</li>
            </ul>
            </br>
            <a href="/">Home</a>
            {% endblock %} """)
    
    
