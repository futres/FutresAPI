
import requests, zipfile, io, sys
import json
import xlrd
import pandas as pd
import urllib.request

def fetch_data():
    print("fetching data...")
    # populate proejcts array with a complete list of project IDs 
    # for the amphibianDiseaseTeam
    amphibianDiseaseTeamID = 45
    projects = []
    url="https://api.geome-db.org/projects/stats?"
    r = requests.get(url)
    for project in json.loads(r.content):
        projectConfigurationID = project["projectConfiguration"]["id"]
        if (projectConfigurationID == amphibianDiseaseTeamID):
            projects.append(project["projectId"])
    projectsString = "["+ ','.join(str(e) for e in projects) + "]"
    
    print(projectsString)
    
    # get the initial URL
    url="https://api.geome-db.org/records/Sample/excel?networkId=1&q=_projects_:" + projectsString +"+_select_:%5BEvent,Sample,Diagnostics%5D"
    r = requests.get(url)

    excel_file_url = json.loads(r.content)['url']
    urllib.request.urlretrieve(excel_file_url, filename)


def process_data():
    print("processing data...")    
    SamplesDF = pd.read_excel(filename,sheet_name='Samples')
    EventsDF = pd.read_excel(filename,sheet_name='Events')
    DiagnosticsDF = pd.read_excel(filename,sheet_name='Diagnostics')

    SamplesDF.materialSampleID = SamplesDF.materialSampleID.astype(str)
    DiagnosticsDF.materialSampleID = DiagnosticsDF.materialSampleID.astype(str)
    SamplesDF.eventID = SamplesDF.eventID.astype(str)
    EventsDF.eventID = EventsDF.eventID.astype(str)

    SamplesDF = SamplesDF.merge(DiagnosticsDF, how='outer', left_on='materialSampleID', right_on='materialSampleID')
    SamplesDF = SamplesDF.merge(EventsDF, how='outer', left_on='eventID', right_on='eventID')
    
    SamplesDF = SamplesDF[['materialSampleID','diseaseTested','diseaseDetected','genus','specificEpithet','country','yearCollected','projectId']]
    SamplesDF['diseaseTested'] = SamplesDF['diseaseTested'].str.capitalize()
    SamplesDF['scientificName'] = SamplesDF['genus'] + " " + SamplesDF['specificEpithet']
    
    SamplesDF.to_excel(processed_filename)

# function to write tuples to json from pandas group by
# using two group by statements.
def json_tuple_writer(group,name,filename,definition):
    api.write("|"+filename+"|"+definition+"|\n")
    jsonstr = '[\n'
    namevalue = ''
    for rownum,(indx,val) in enumerate(group.iteritems()):                
        
        thisnamevalue = str(indx[0])
        
        if (namevalue != thisnamevalue):
            jsonstr+="\t{"
            jsonstr+="\""+name+"\":\""+thisnamevalue+"\","
            jsonstr+="\""+str(indx[1])+"\":"+str(val)  
            jsonstr+="},\n"                   
        else:
            jsonstr = jsonstr.rstrip("},\n")
            jsonstr+=",\""+str(indx[1])+"\":"+str(val)  
            jsonstr+="},\n"                           
        
        namevalue = thisnamevalue                
        
    jsonstr = jsonstr.rstrip(',\n')

    jsonstr += '\n]'
    with open(filename,'w') as f:
        f.write(jsonstr)
        
        
# function to write tuples to json from pandas group by
# using two group by statements.
def json_tuple_writer_scientificName_projectId(group,name):
    projectId = ''
    thisprojectId = ''
    jsonstr = ''
    firsttime = True
    for rownum,(indx,val) in enumerate(group.iteritems()):  
        #print(str(indx[0]),str(indx[1]), str(val))              
        thisprojectId = str(indx[0])
        if (projectId != thisprojectId):
            # End of file
            if firsttime == False:                
                jsonstr = jsonstr.rstrip(',\n')
                jsonstr += "\n]"            
                with open('data/scientificName_projectId_' + projectId + ".json",'w') as f:
                    f.write(jsonstr)                      
            # Beginning of file
            jsonstr = "[\n"
            jsonstr += ("\t{\"scientificName\":\"" + str(indx[1]) + "\",\"value\":"+str(val) +"},\n" )

            api.write("|data/scientificName_projectId_"+thisprojectId +".json|unique scientificName count for project "+thisprojectId+"|\n")                
        else:                                    
            jsonstr += ("\t{\"scientificName\":\"" + str(indx[1]) + "\",\"value\":"+str(val) +"},\n" )

            
        projectId = thisprojectId

        
        firsttime = False            
    
    # write the last one
    jsonstr = jsonstr.rstrip(',\n')
    jsonstr += "\n]"
    with open('data/scientificName_projectID_' + thisprojectId +".json",'w') as f:
                f.write(jsonstr)        
         

# function to write JSON from pandas groupby
def json_writer(group,name,filename,definition):
    api.write("|"+filename+"|"+definition+"|\n")
    
    jsonstr = '[\n'
    for (rownum,val) in enumerate(group.iteritems()):                        
        jsonstr+="\t{"
        jsonstr+="\""+name+"\":\""+str(val[0])+"\","            
        jsonstr+="\"value\":"+str(val[1])  
        jsonstr+="},\n"                   
        
        
    jsonstr = jsonstr.rstrip(',\n')
    jsonstr += '\n]'
    with open(filename,'w') as f:
        f.write(jsonstr)

    
def run_grouped_data(df,name):
    
    bd = df.diseaseTested.str.contains('Bd')
    bd = df[bd]  
    
    bsal = df.diseaseTested.str.contains('Bsal')
    bsal = df[bsal]  
    
    # groupby, filter on Bd,Bsal,Both for name
    group = df.groupby(name)[name].size()    
    json_writer(group,name,'data/'+name+'_Both.json','Bd and Bsal counts grouped by '+name)      
    
    group = bd.groupby(name)[name].size()
    json_writer(group,name,'data/'+name+'_Bd.json','Bd counts grouped by '+name)  
    
    group = bsal.groupby(name)[name].size()
    json_writer(group,name,'data/'+name+'_Bsal.json','Bsal counts grouped by '+name)  

    # groupby, filter on Bd,Bsal,Both for name+diseaseDetected
    group = df.groupby([name,'diseaseDetected']).size()
    json_tuple_writer(group,name,'data/'+name+'_diseaseDetected_Both.json','Bd and Bsal counts grouped by presence-abscense and by '+name)
    
    group = bd.groupby([name,'diseaseDetected']).size()
    json_tuple_writer(group,name,'data/'+name+'_diseaseDetected_Bd.json','Bd counts grouped by presence-abscense and by '+name)
    
    group = bsal.groupby([name,'diseaseDetected']).size()
    json_tuple_writer(group,name,'data/'+name+'_diseaseDetected_Bsal.json','Bsal counts grouped by presence-abscense and by '+name)
    
    # groupby, filter on Bd,Bsal,Both for name+diseaseTested         
    group = df.groupby([name,'diseaseTested']).size()
    json_tuple_writer(group,name,'data/'+name+'_Both_stacked.json','Bd and Bsal counts for a stacked chart, grouped by '+name)
    
            
def group_data():  
    print("reading processed data ...")
    df = pd.read_excel(processed_filename)
    
    print("grouping results ...")    
    # genus, country, yearCollected results
    run_grouped_data(df,'genus')
    run_grouped_data(df,'scientificName')
    run_grouped_data(df,'country')
    run_grouped_data(df,'yearCollected')

    # summary tables for diseaseDetected and diseaseTested
    bd = df.diseaseTested.str.contains('Bd')
    bd = df[bd]  
    
    bsal = df.diseaseTested.str.contains('Bsal')
    bsal = df[bsal]  
    
    # diseaseDetected
    group = df.groupby('diseaseDetected')['diseaseDetected'].size()
    json_writer(group,'diseaseDetected','data/diseaseDetected_Both.json','Bd and Bsal counts grouped by presence-absence')
    
    group = bd.groupby('diseaseDetected')['diseaseDetected'].size()
    json_writer(group,'diseaseDetected','data/diseaseDetected_Bd.json','Bd counts grouped by presence-absence')
    
    group = bsal.groupby('diseaseDetected')['diseaseDetected'].size()
    json_writer(group,'diseaseDetected','data/diseaseDetected_Bsal.json','Bsal counts grouped by presence-absence')
        
    # diseaseTested
    group = df.groupby('diseaseTested')['diseaseTested'].size()
    json_writer(group,'diseaseTested','data/diseaseTested_Both.json','Bd and Bsal counts')    
    
    # scientificName by projectId
    group = df.groupby(['projectId','scientificName']).size()
    json_tuple_writer_scientificName_projectId(group,'projectId')


# global variables
api = open("api.md","w")
api.write("# API\n\n")
api.write("Amphibian Disease Portal API Documentation\n")
api.write("|filename|definition|\n")
api.write("|----|---|\n")
filename = 'data/temp_output.xlsx'
processed_filename = 'data/temp_output_processed.xlsx'


#fetch_data()
process_data()
group_data()

api.close()

