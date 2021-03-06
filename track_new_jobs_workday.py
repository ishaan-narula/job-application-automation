import json, requests
from urllib.request import Request, urlopen
import pprint
import pandas as pd
desired_width = 320
pd.set_option('display.width', desired_width)
pd.set_option('display.max_columns', 10)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_colwidth', None) #To display full URL in dataframe
from datetime import datetime

def get_all(myjson): #U
    ''' Recursively find the keys and associated values in all the dictionaries
        in the json object or list.
    '''
    if isinstance(myjson, dict):
        for jsonkey, jsonvalue in myjson.items():
            if not isinstance(jsonvalue, (dict, list)):
                yield jsonkey, jsonvalue
            else:
                for k, v in get_all(jsonvalue):
                    yield k, v
    elif isinstance(myjson, list):
        for element in myjson:
            if isinstance(element, (dict, list)):
                for k, v in get_all(element):
                    yield k, v

def df_column_switch(df, column1, column2):
    i = list(df.columns)
    a, b = i.index(column1), i.index(column2)
    i[b], i[a] = i[a], i[b]
    df = df[i]
    return df

def create_jobsdf_workday(company_name, url, save_to_excel = False):
    '''
    Returns a dataframe of the first 50 (or fewer) positions listed on a company's Workday website
    at the time the function is run.
    '''
    url = str(url)
    company_name = str(company_name)

    req = Request(url)
    req.add_header("Accept", "application/json,application/xml")
    req.add_header('User-agent', 'Mozilla/5.0 (Linux i686)')
    raw = urlopen(req).read().decode()
    #print('Raw', raw)
    page_dict = json.loads(raw) #Sometimes Workday needs to be scrolled all the way to the end to load more jobs. This dict does not include jobs all the way to the end. It is unable to extract postings which appear after scrolling all the way down for the first time.

    #pprint.pprint(page_dict) #The above code does not work for Arrowstreet Capital

    jobs_lst = []
    partial_urls = []
    for key, value in get_all(page_dict):
        if key == 'text':
            jobs_lst.append(value)

        elif key == 'commandLink':
            partial_urls.append(value)

    if company_name == 'Vontobel Asset Management': #for Vontobel careers site - find a more general solution later
        n = 5
        jobs_lst = [jobs_lst[i * n:(i + 1) * n] for i in range((len(jobs_lst) + n - 1) // n)]  #U

    else:
        n = 4
        jobs_lst = [jobs_lst[i * n:(i + 1) * n] for i in range((len(jobs_lst) + n - 1) // n)]  #U

    jobs_lst2 = []
    date_posted = []
    for lst in jobs_lst:
        lst2 = [x for x in lst if not x.startswith('Posted')]
        lst_dp = list(set(lst) - set(lst2))
        jobs_lst2.append(lst2)
        date_posted.append(lst_dp)

    if (company_name == 'Blackstone' or
        company_name == 'Blackstone Campus' or
        company_name == 'T. Rowe Price International'):
        jobs_df = pd.DataFrame()

    else:
        jobs_df = pd.DataFrame(pd.Series(jobs_lst2), columns = ['Role'])

    #print(jobs_lst)
    #print(date_posted)
    #print(len(date_posted), len(jobs_df.index))
    #print(partial_urls)
    #print(len(partial_urls))

    jobs_df['URL'] = pd.DataFrame(partial_urls)
    s = 'myworkdayjobs.com'
    idx_crit = url.find(s) + len(s)
    jobs_df['URL'] = url[ : idx_crit] + jobs_df['URL']

    jobs_df.insert(jobs_df.columns.get_loc('URL'), 'Date Posted', pd.Series(date_posted))

    jobs_df.insert(0, 'Company', company_name)

    #if len(date_posted) != len(jobs_df.index):
    #    diff = len(date_posted) - len(jobs_df.index)
    #    date_posted = date_posted[:-diff]

    #jobs_df['Date Posted'] = date_posted

    if save_to_excel == True:
        jobs_df['Date Viewed'] = datetime.now()
        fname = company_name + '.xlsx'
        jobs_df.to_excel('Dataframes/' + fname)

        print("First 50 jobs on the given webpage saved as a new Excel file", fname)

    #print(jobs_df)
    return jobs_df

#def first_jobsdf_toexcel(company_name, url):
#    '''
#    Saves the jobs dataframe created for the first time using the create_jobsdf_... functions as an Excel file
#    named after the company, adding a 'Date Viewed' column which specifies the date and
#    time the jobs were viewed and dataframe was saved
#    '''
#    url = str(url)
#    company_name = str(company_name)
#
#   jobs_df = create_jobsdf(company_name, url)
#    jobs_df['Date Viewed'] = datetime.now()
#
#    fname = company_name + '.xlsx'
#    jobs_df.to_excel('Dataframes/'+ fname)
#
#    print("First 50 jobs on the given webpage saved as a new Excel file", fname)

def new_jobs_workday(company_name, url, save_to_excel = False):
    '''
    Returns a dataframe with new jobs added/ existing jobs changed on the company's Workday website compared
    with the jobs in the last saved Excel file

    Drawbacks to Fix:
    - Some jobs posted earlier are often re-posted. This would not capture jobs when they are re-posted (only
    when they were posted for the first time)
    '''
    url = str(url)
    company_name = str(company_name)

    latest_jobs_df = create_jobsdf_workday(company_name, url)
    latest_jobs_df.fillna('', inplace = True)
    latestdf_DatePosted = latest_jobs_df.pop('Date Posted')
    latest_jobs_df.pop('Company')
    #print('latest jobs df')
    #print(latest_jobs_df)

    prev_jobs_df = pd.read_excel('Dataframes/' + company_name + '.xlsx', index_col = [0], dtype = object)
    prev_jobs_df = prev_jobs_df.drop(['Company', 'Date Posted', 'Date Viewed'], axis = 1)
    prev_jobs_df.fillna('', inplace = True)
    #print('previous jobs df')
    #print(prev_jobs_df)

    #df_diff = pd.concat([prev_jobs_df,latest_jobs_df]).drop_duplicates(keep = False) #Understand
    df_combined = pd.merge(prev_jobs_df, latest_jobs_df, how = 'outer', on = 'URL', indicator = True)
    #print(df_combined)
    df_diff = df_combined.loc[df_combined._merge == 'right_only'].reset_index(drop = True)
    df_diff = df_diff.drop('_merge', axis = 1)
    #print(df_diff)

    latest_jobs_df.insert(latest_jobs_df.columns.get_loc('URL'), 'Date Posted', latestdf_DatePosted)
    dfdiff_DatePosted = pd.merge(df_diff.copy(), latest_jobs_df, how = 'inner', on = 'URL')['Date Posted']
    df_diff.insert(df_diff.columns.get_loc('URL'), 'Date Posted', dfdiff_DatePosted)

    if (company_name == 'Blackstone' or
        company_name == 'Blackstone Campus' or
        company_name == 'T. Rowe Price International'):
        df_diff.insert(df_diff.columns.get_loc('Date Posted'), 'Company', company_name)

    else:
        df_diff.insert(df_diff.columns.get_loc('Role_x'), 'Company', company_name)

        df_diff = df_column_switch(df_diff, 'Role_x', 'Role_y')
        df_diff = df_diff.drop('Role_x', axis = 1)
        df_diff = df_diff.rename({'Role_y': 'Role'}, axis = 1)

    df_diff['Date Viewed'] = datetime.now()

    print("New jobs added/ existing jobs changed on " + '\033[1m' + company_name + '\033[0m' + " website compared with the jobs in the last saved Excel file")
    print(df_diff)

    if save_to_excel == True:
        prev_jobs_df2 = pd.read_excel('Dataframes/' + company_name + '.xlsx', index_col=[0])
        updated_jobs_df = pd.concat([df_diff, prev_jobs_df2]).reset_index(drop = True)
        updated_jobs_df.to_excel('Dataframes/' + company_name + '.xlsx')

        print("New jobs on the given webpage added to the existing Excel file", company_name + '.xlsx')

    return df_diff

def dfs_old20220120_tonew(file_name):
    '''
    Converts dataframes saved in old format in folder Dataframes to new format
    '''
    old_df = pd.read_excel('Dataframes (Old Format 2022 01 20)/' + file_name, index_col=[0])
    #print('\033[1m' + 'Old Dataframe for ' + file_name + '\033[0m')
    #print(old_df)
    #old_df['Job ID'] = old_df['Job ID'].astype('Int64') #Only for Vontobel

    combined = old_df[['Position', 'Division', 'Job ID', 'Location']].values.tolist()
    old_df.insert(old_df.columns.get_loc('Date Posted'), 'Role', combined)

    new_df = old_df[['Company', 'Role', 'Date Posted', 'URL', 'Date Viewed']]
    #print('\033[1m' + 'New Dataframe for ' + file_name + '\033[0m')
    #print(new_df)

    new_df.to_excel('Dataframes/' + file_name)
    print('Converted old dataframe format for file ' + '\033[1m' + file_name + '\033[0m')