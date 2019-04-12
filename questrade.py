import json
import requests
import logging
import pprint

#configure logging
logging.basicConfig(format='%(message)s',
                filename='questrade.log',
                filemode='w',
                level=logging.INFO)

#logs into questrade platform with token from tokens.json
#returns a dictonary containing access_token, api_server, expires_in, refresh_token, token_type
def qt_login():
    
    #get refresh token from json file
    try:
        with open("tokens.json") as read_file:
            tokens = json.load(read_file)
    #error opening file
    except:
        logging.error("Error opening tokens file. Exiting...")
        exit()
    
    #send login request
    url = "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token="+tokens["questrade_token"]
    login = requests.post(url)
    #check that login was sucessful
    if login.status_code != 200:
        logging.error("Error logging into Questrade API. Status:"+str(response.status_code)+". Exiting...")
        exit()
        
    login = json.loads(login.content)
    
    #update refresh token and write to file
    tokens["questrade_token"] = login["refresh_token"]
    with open("tokens.json", "w+") as write_file:
        json.dump(tokens, write_file)
        
    return login

def qt_call(auth, method):
        
    request_headers = {"Content-Type" : "application/json", "Authorization" : auth["token_type"]+" "+auth["access_token"]}
    url = auth["api_server"]+"v1/"+method
    response = requests.get(url, headers=request_headers)
    
    #check that api call was sucessful
    if response.status_code != 200:
        logging.error("Error with Questrade API call. Status:"+str(response.status_code)+". Exiting...")
        exit()
    
    #if sucessful return information
    return json.loads(response.content)
    

def main():
    pp = pprint.PrettyPrinter(indent=4)
    
    qt_auth = qt_login()
    accounts = qt_call(qt_auth, "accounts")
    pp.pprint(accounts)
    print("")
    
    balances = qt_call(qt_auth, "accounts/51721720/balances")
    
    #make sure balances are returned in CAD
    if balances["combinedBalances"][0]["currency"] == "CAD":
        pp.pprint(round(balances["combinedBalances"][0]["totalEquity"]))
    else:
        pp.pprint(round(balances["combinedBalances"][1]["totalEquity"]))
    
if __name__ == "__main__":
    main()