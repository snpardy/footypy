from datetime import date, datetime
import re
import requests

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


def get_full_year_results(year: int, comp: str = 'AFLM') -> pd.DataFrame:
    '''
    Scrapes full year of AFL results for given year from footywire.
    Please use sparingly so as to not overload the site.

    Args:
        year (int): year you're interested in
        comp (str, optional): defaults to AFL Mens

    Returns:
        pd.DataFrame: Results dataframe
    '''
    url = f'https://www.footywire.com/afl/footy/ft_match_list?year={year}'

    page = requests.get(url)

    soup = BeautifulSoup(page.content, "html.parser")
    rounds = (soup
              .find_all("td", {"class": "tbtitle"})[0]
              .find_parent()
              .find_parent()
              .find_all('tr')
              )

    regex = re.compile('Round \d+|[A-Z][a-z]+ Final')

    week = []
    timestamp = []
    home_team = []
    away_team = []
    venue = []
    home_score = []
    away_score = []
    bye = []

    for r in rounds:
        new_round = re.findall(regex, r.find('td').text)
        if new_round:
            assert len(new_round) == 1
            current_round = new_round[0].strip('Round ')
        else:
            match = r.find_all('td', {"class": "data"})
            if match:
                if match[2].text == 'BYE':
                    week.append(current_round)
                    bye.append(True)
                    home_team.append(
                        re.search('^[A-Za-z]+', match[1].text.strip('\n')).group())

                    timestamp.append('NA')
                    away_team.append('NA')
                    venue.append('NA')
                    home_score.append('NA')
                    away_score.append('NA')
                else:
                    ts = datetime.strptime(match[0].text.strip() + ' ' + str(year),
                                                    '%a %d %b %I:%M%p %Y'
                                                    )
                    if ts.date() > date.today():
                        # hit future rounds, stop parsing
                        break
                    else:
                        week.append(current_round)
                        timestamp.append(ts)
                        home_team.append(re.search('^[A-Za-z]+', match[1].text.strip('\n')).group())
                        away_team.append(re.search('[A-Za-z]+$', match[1].text.strip('\n')).group())
                        venue.append(match[2].text.strip('\n'))
                        home_score.append(re.search('^\d+', match[4].text.strip('\n')).group())
                        away_score.append(re.search('\d+$', match[4].text.strip('\n')).group())
                        bye.append(False)

    df = pd.DataFrame({
        'week': week,
        'timestamp': timestamp,
        'home_team': home_team,
        'away_team': away_team,
        'venue': venue,
        'home_score': home_score,
        'away_score': away_score,
        'bye': bye,
    })

    for c in df.columns:
        df[c] = np.where(df[c] == 'NA', np.nan, df[c])

    df.timestamp = pd.to_datetime(df.timestamp, errors='coerce')

    df.home_score = df.home_score.astype(float)
    df.away_score = df.away_score.astype(float)

    df.bye = df.bye.astype(bool)

    team_corrections = {
        'Port': 'Port_Adelaide',
        'Gold': 'Gold_Coast',
        'St': 'St_Kilda',
        'West$': 'West_Coast',
        'North': 'North_Melbourne'
    }

    for key, value in team_corrections.items():
        df['home_team'] = df['home_team'].str.replace(key, value, regex=True)
        df['away_team'] = df['away_team'].str.replace(key, value, regex=True)

    return df
