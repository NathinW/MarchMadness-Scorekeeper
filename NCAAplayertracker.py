from bs4 import BeautifulSoup
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


#URL (replace with the actual URL you're interested in)
SCOREBOARD_URL = 'https://www.cbssports.com/college-basketball/scoreboard/NCAA/20240330/'

def fetchBoxScoreLinks(url):
    response = requests.get(url)
    webpage = response.content 

    soup = BeautifulSoup(webpage, 'html.parser')

    # Find all <div> elements with the class "bottom-bar" (each game on the page)
    bottom_bar_divs = soup.find_all('div', class_='bottom-bar')

    links = []

    #for each game, find the box score link
    for div in bottom_bar_divs:
        list_items = div.find_all('li')
        # Find the <a> tag within the second <li> (ensuring the game does have a box score)
        if len(list_items) == 2:
            link = list_items[1].find('a')
            if link and link.has_attr('href') and link.text != "Watch Now":
                links.append("https://www.cbssports.com/" + link['href'])

    return links

def boxScoreScrape(url):
    response = requests.get(url)
    webpage = response.content

    # Create a BeautifulSoup object
    soup = BeautifulSoup(webpage, 'html.parser')

    playerDict = {}

    # Iterate over the table for the starting lineups
    starters_div = soup.find_all('div', class_='starters-stats')
    for div in starters_div:
        #all the player objects, with their stats
        player_div = div.find_all('tr', class_='no-hover data-row')
        for div2 in player_div:
            elmnt = div2.find('td', class_='name-element')
            name = elmnt.find('a', class_='name-truncate')
            #extract full name from the player url
            if name and name.has_attr('href'):
                name = name['href']
                name = name.split('/')[-2]
                name = name.replace('-', ' ')
            try:
                pts = int(div2.find('td', class_='number-element').text)
            except:
                pts = "N/A (what a loser he didn't play)"
            playerDict[name] = pts
    #Now do the same for the benches
    bench_div = soup.find_all('div', class_='bench-stats')
    for div in bench_div:
        player_div = div.find_all('tr', class_='no-hover data-row')
        for div2 in player_div:
            elmnt = div2.find('td', class_='name-element')
            name = elmnt.find('a', class_='name-truncate')
            if name and name.has_attr('href'):
                name = name['href']
                name = name.split('/')[-2]
                name = name.replace('-', ' ')
            try:
                pts = int(div2.find('td', class_='number-element').text)
            except:
                pts = "N/A (what a loser he didn't play)"
            playerDict[name] = pts
    return playerDict
    
    
def updateSheet(playerDict):
    # Replace these with your actual file path, spreadsheet ID, and sheet name
    SERVICE_ACCOUNT_FILE = "REDACTED"
    SPREADSHEET_ID = 'REDACTED'
    SHEET_NAME = 'mmdraft'

    scraped_player_points = playerDict

    # Authenticate and build the Google Sheets service
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()

    # Assuming there are multiple columns of player names across the spreadsheet
    range_name = 'A:Z'  # Adjust based on the actual range of your player names and scores
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    rows = result.get('values', [])
    #print(rows)
    if not rows:
        print('No data found in the spreadsheet.')
    else:
        updates = []  # To keep track of cells to update with scores

        for row_index, row in enumerate(rows):
            for col_index in range(0, len(row), 2):  # Step by 2, assuming every other column contains player names
                if col_index < len(row) - 1:  # Ensure there's a column to the right for the score
                    # Convert the name from the sheet to lowercase for comparison
                    full_name_in_sheet = row[col_index].lower()
                    #print(full_name_in_sheet)
                    if full_name_in_sheet in scraped_player_points:
                        # Prepare the update for this player's score in the adjacent column
                        updates.append({
                            'range': f'{chr(65 + col_index + 1)}{row_index + 1}',
                            'values': [[scraped_player_points[full_name_in_sheet]]]
                        })

        # Update the spreadsheet with the new scores
        if updates:
            request_body = {
                'valueInputOption': 'USER_ENTERED',
                'data': updates
            }
            update_result = sheet.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=request_body).execute()
            print(f"{update_result.get('totalUpdatedCells')} cells updated.")
        else:
            print("No matching players found in the spreadsheet to update.")


boxLinks = fetchBoxScoreLinks(SCOREBOARD_URL)
for link in boxLinks:
    print(link.split('/')[-2])
    playerDict = boxScoreScrape(link)
    updateSheet(playerDict)