import gspread
import json
import requests
import logging
import pprint
import datetime
from oauth2client.service_account import ServiceAccountCredentials

#configure logging
logging.basicConfig(format='%(message)s',
                filename='questrade.log',
                filemode='w',
                level=logging.INFO)

pp = pprint.PrettyPrinter(indent=4)

#logs into questrade platform with token from qt_auth.json
#returns a dictonary containing access_token, api_server, expires_in, refresh_token, token_type
def qt_login(name):

    #get refresh token from json file
    try:
        with open("qt_auth.json") as read_file:
            tokens = json.load(read_file)
    #error opening file
    except:
        logging.error("Error opening tokens file. Exiting...")
        exit()

    #send login request
    url = "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token="+tokens["questrade_token_"+name]
    login = requests.post(url)
    #check that login was sucessful
    if login.status_code != 200:
        logging.error("Error logging into Questrade API. Status:"+str(response.status_code)+". Exiting...")
        exit()

    login = json.loads(login.content)

    #update refresh token and write to file
    tokens["questrade_token_"+name] = login["refresh_token"]
    with open("qt_auth.json", "w+") as write_file:
        json.dump(tokens, write_file)

    return login

#send api call to questrade server
#requires auth dictonary returned from qt_login()
def qt_call(auth, method, account = None, startTime = None, endTime = None):

    #if there is a specific account to run api call against change URL
    if account == None:
        url = auth["api_server"]+"v1/"+method
    elif account != None and startTime == None:
        url = auth["api_server"]+"v1/accounts/"+account+"/"+method
    else:
        url = auth["api_server"]+"v1/accounts/"+account+"/"+method+"?startTime="+startTime+"&endTime="+endTime+"&"
    request_headers = {"Content-Type" : "application/json", "Authorization" : auth["token_type"]+" "+auth["access_token"]}
    response = requests.get(url, headers=request_headers)

    #check that api call was sucessful
    if response.status_code != 200:
        logging.error("Error with Questrade API call. Status:"+str(response.status_code)+". Exiting...")
        exit()

    #if sucessful return information
    return json.loads(response.content)

def sheets_login():
    try:
        scope = ['https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('sheets_auth.json', scope)
        client = gspread.authorize(creds)
    except Exception as e:
        logging.error("Error logging into Google Sheets API. Exiting...")
        logging.error(e)
        print(e)
        exit()

    return client

def update_account(sheet, name, row):

    #dictonary for mapping names to columns
    mapping = {"jordanTFSA" : "B", "danelleTFSA" : "D", "jordanRRSP" : "F", "jasperRRSP" : "H"}
    deposits = {"jordanTFSA" : "P", "danelleTFSA" : "R", "jordanRRSP" : "T", "jasperRRSP" : "V"}
    qt_auth = qt_login(name)

    accounts = qt_call(qt_auth, "accounts")
    for account in accounts["accounts"]:

        #get total equity for the account
        equity = 0
        balances = qt_call(qt_auth, "balances", account["number"])
        #make sure equity is returned in CAD
        if balances["combinedBalances"][0]["currency"] == "CAD":
            equity = (balances["combinedBalances"][0]["totalEquity"])
        else:
            equity = (balances["combinedBalances"][1]["totalEquity"])

        #update row with total equity
        try:
            sheet.update_acell(mapping[name+account["type"]]+str(row), equity)
        except:
            continue

        #check to see if there where any deposits or withdrawals
        #assumes there will only be one desposit or withdrawal in a day #break
        datestring = str(datetime.datetime.today()).split(" ")[0]
        funds = qt_call(qt_auth, "activities", account["number"], datestring+"T00:00:00-05:00", datestring+"T17:00:00-05:00")
        if funds["activities"] == []:
            amount = 0
        else:
            for activity in funds["activities"]:
                if activity["type"] == "Deposits" or activity["type"] == "Withdrawls":
                    amount = activity["netAmount"]
                    print(activity)
                    break
                else:
                    amount = 0
        #update spreadsheet with deposit amount for the day
        sheet.update_acell(deposits[name+account["type"]]+str(row), amount)

    return

def main():

    #if day is saturday or sunday --> quit
    if datetime.datetime.today().strftime('%A') in ["Saturday","Sunday"]:
        quit()

    #qt_auth = qt_login()
    client = sheets_login()
    sheet = client.open("Investment Accounts").sheet1

    #get the next row to insert into
    values_list = sheet.col_values(1)
    row = (len(values_list)+1)

    #update date
    now = datetime.datetime.now()
    date = (str(now.year)+"-"+str(now.month)+"-"+str(now.day))
    sheet.update_acell('A'+str(row), date)

    #update equity amounts
    update_account(sheet, "jordan", row)
    update_account(sheet, "danelle", row)
    update_account(sheet, "jasper", row)


if __name__ == "__main__":
    main()
