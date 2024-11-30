from copy import deepcopy
from datetime import date, datetime
import os
import re
import requests
import pickle as pkl

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

def get_full_year_results(year: int, comp: str = 'AFLM') -> pd.DataFrame:
    '''
    Scrapes full year of AFL results for given year from footywire.
    Please use sparingly so as not to spam the site.

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

    regex = re.compile(r'Round \d+|[A-Z][a-z]+ Final')

    week_name = []
    timestamp = []
    home_team = []
    away_team = []
    venue = []
    home_score = []
    away_score = []
    footy_wire_id = []
    bye = []

    for r in rounds:
        new_round = re.findall(regex, r.find('td').text)
        if new_round:
            assert len(new_round) == 1
            current_round = new_round[0].strip('Round ')
        else:
            match = r.find_all(r'td', {"class": "data"})
            if match:
                if match[2].text == 'BYE':
                    week_name.append(current_round)
                    bye.append(True)
                    home_team.append(
                        re.search(r'^[A-Za-z]+', match[1].text.strip('\n')).group())

                    timestamp.append('NA')
                    away_team.append('NA')
                    venue.append('NA')
                    home_score.append('NA')
                    away_score.append('NA')
                    footy_wire_id.append('NA')
                elif len(match[0].find_previous().find_all('td', string='MATCH CANCELLED')) != 0:
                    # current match was cancelled
                    week_name.append(current_round)
                    bye.append(True)
                    home_team.append(
                        re.search(r'^[A-Za-z]+', match[1].text.strip('\n')).group())
                    timestamp.append('NA')
                    away_team.append('NA')
                    venue.append('NA')
                    home_score.append('NA')
                    away_score.append('NA')
                    footy_wire_id.append('NA')
                else:
                    ts = datetime.strptime(match[0].text.strip() + ' ' + str(year),
                                                    '%a %d %b %I:%M%p %Y'
                                                    )
                    if ts.date() > date.today():
                        # future rounds
                        week_name.append(current_round)
                        timestamp.append(ts)
                        home_team.append(re.search(r'^[A-Za-z]+', match[1].text.strip('\n')).group())
                        away_team.append(re.search(r'([A-Za-z]+ )?[A-Za-z]+$', match[1].text.strip('\n')).group())
                        venue.append(match[2].text.strip('\n'))
                        home_score.append(np.nan)
                        away_score.append(np.nan)
                        footy_wire_id.append(np.nan)
                        bye.append(False)
                    else:
                        week_name.append(current_round)
                        timestamp.append(ts)
                        home_team.append(re.search(r'^[A-Za-z]+', match[1].text.strip('\n')).group())
                        away_team.append(re.search(r'([A-Za-z]+ )?[A-Za-z]+$', match[1].text.strip('\n')).group())
                        venue.append(match[2].text.strip('\n'))
                        home_score.append(re.search(r'^\d+', match[4].text.strip('\n')).group())
                        away_score.append(re.search(r'\d+$', match[4].text.strip('\n')).group())
                        footy_wire_id.append(re.search(r'\d+$', match[4].a.attrs["href"]).group())
                        bye.append(False)

    df = pd.DataFrame({
        'week_name': week_name,
        'timestamp': timestamp,
        'home_team': home_team,
        'away_team': away_team,
        'venue': venue,
        'home_score': home_score,
        'away_score': away_score,
        'bye': bye,
        'footy_wire_match_id': footy_wire_id
    })

    for c in df.columns:
        if c != 'timestamp':
            df[c] = np.where(df[c] == 'NA', np.nan, df[c])


    df.timestamp = pd.to_datetime(df.timestamp, errors='coerce')

    df.home_score = df.home_score.astype(float)
    df.away_score = df.away_score.astype(float)

    df.bye = df.bye.astype(bool)

    team_corrections = {
        'Port': 'Port_Adelaide',
        'Gold': 'Gold_Coast',
        'St': 'St_Kilda',
        'Kilda': 'St_Kilda',
        'West': 'West_Coast',
        'North': 'North_Melbourne',
        'Western': 'Western_Bulldogs'
    }

    finals_weeks = {
        'Qualifying Final': 1,
        'Elimination Final': 1,
        'Semi Final': 2,
        'Preliminary Final': 3,
        'Grand Final': 4
    }

    max_week = max([int(w) for w in df.week_name.unique() if not w.__contains__('Final')])

    df['week_number'] = df.week_name

    for final, offset in finals_weeks.items():
        df.loc[df.week_name == final, 'week_number'] = max_week + offset

    df['week_number'] = df.week_number.astype(int)

    df['home_team'] = df['home_team'].str.replace(' ', '_')
    df['away_team'] = df['away_team'].str.replace(' ', '_')
    for key, value in team_corrections.items():
        df.loc[df.home_team == key, 'home_team'] = value
        df.loc[df.away_team == key, 'away_team'] = value

    # rule based round names

    # Opening Round
    df.loc[df.week_number == 0, 'week_name'] = 'Opening Round'

    # ANZAC Round
    week_number = df[
        (df.timestamp.dt.month == 4) &
        (df.timestamp.dt.day == 25) &
        (df.timestamp.dt.year >= 1995)
        ].week_number
    if not week_number.empty:
        week_number = week_number.iloc[0]
        df.loc[df.week_number == week_number, 'week_name'] = 'ANZAC Round'

    # Gather Round
    week_number = df[
        ~df.venue.isna() &
        df.venue.str.contains('Adelaide') &
        (df.timestamp.dt.year >= 2023)
        ].groupby('week_number')[['venue']].count().query('venue > 3')
    if not week_number.empty:
        week_number = week_number.index[0]
        df.loc[df.week_number == week_number, 'week_name'] = 'Gather Round'

    column_order = ['week_number', 'week_name', 'timestamp', 'venue', 'footy_wire_id', 'home_team', 'away_team',
       'home_score', 'away_score', 'bye',]

    return df

def _detail_helper_player_stats(soup: BeautifulSoup):
    '''
    Given the html soup output of footywire.com/afl/footy/ft_match_statistics?mid={footy_wire_match_id}, return player stat details

    Args:
        footy_wire_detail_soup (BeautifulSoup): _description_
    '''

    stat_table_text_to_title = {
        'K': 'kicks',
        'HB': 'handballs',
        'D': 'disposals',
        'M': 'marks',
        'G': 'goals',
        'B': 'behinds',
        'T': 'tackles',
        'HO': 'hitouts',
        'GA': 'goal_assists',
        'I50': 'inside_50s',
        'CL': 'clearances',
        'CG': 'clangers',
        'R50': 'rebound_50s',
        'FF': 'frees_for',
        'FA': 'frees_against',
        'AF': 'afl_fantasy',
        'SC': 'supercoach'
    }

    team_name_lookup = {
        'St': 'St_Kilda',
        'North': 'North_Melbourne',
        'Port': 'Port_Adelaide',
        'West': 'West_Coast',
        'Western': 'Wester_Bulldogs',
        'Gold': 'Gold_Coast',
    }

    brownlow = [b for b in soup.find_all("b") if b.text == 'Brownlow Votes:']
    brownlow_flag = bool(len(brownlow))  # no votes in finals
    if brownlow_flag:
        brownlow = brownlow[0]
        three_votes = brownlow.find_next()
        two_votes = brownlow.find_next().find_next()
        one_vote = brownlow.find_next().find_next().find_next()

    team_1 = soup.find_all("td", {"id": 'match-statistics-team1-row'})[0].find_all('tr')
    team_2 = soup.find_all("td", {"id": 'match-statistics-team2-row'})[0].find_all('tr')

    home_team = re.search(
        r'^[A-Za-z]+',
        team_1[0].find_all("a", {'name': ['t1', 't2']})[0].find_parent().text
        ).group()
    away_team = re.search(
        r'^[A-Za-z]+',
        team_2[0].find_all("a", {'name': ['t1', 't2']})[0].find_parent().text
        ).group()

    for k, v in team_name_lookup.items():
        if home_team == k:
            home_team = v
            break
    for k, v in team_name_lookup.items():
        if away_team == k:
            away_team = v
            break

    team_1_stats = {}
    table_columns = team_1[2].find_all('td', {'class': ['bnorm']})
    for item in table_columns:
        if 'title' in item.span.attrs:
            team_1_stats[item.span.attrs['title'].lower().replace(' ', '_')] = []
        else:
            team_1_stats[stat_table_text_to_title[item.span.text]] = []
    stat_keys = deepcopy(list(team_1_stats.keys()))
    team_1_stats['player'] = []
    team_1_stats['subbed_on'] = []
    team_1_stats['subbed_off'] = []
    team_1_stats['unused_sub'] = []
    players = team_1[3:][1:]
    for player in players:
        name_row = player.find_next('a').find_parent()
        if 'href' in name_row.find_next('a').attrs:
            if name_row.find_next('a').attrs["href"].startswith('pp-'):
                team_1_stats['player'].append(name_row.find_next('a').attrs["href"])
                if name_row.findChild('span') is None:
                    team_1_stats['subbed_on'].append(False)
                    team_1_stats['subbed_off'].append(False)
                elif player.findChild('span')['title'] == 'Subbed Off':
                    team_1_stats['subbed_on'].append(False)
                    team_1_stats['subbed_off'].append(True)
                elif player.findChild('span')['title'] in ['Subbed On', 'Activated Substitute']:
                    team_1_stats['subbed_on'].append(True)
                    team_1_stats['subbed_off'].append(False)

                # check if unused sub
                if name_row.find_next().find_next().text == 'Unused Substitute':
                    team_1_stats['unused_sub'].append(True)
                    for k in stat_keys:
                        team_1_stats[k].append(np.nan)
                else:
                    team_1_stats['unused_sub'].append(False)
                    stats = player.find_all('td', {'class': 'statdata'})
                    for k, s in zip(stat_keys, stats):
                        team_1_stats[k].append(int(s.text))

    team_1_frame = pd.DataFrame(team_1_stats)
    team_1_frame['team'] = home_team


    team_2_stats = {}
    table_columns = team_2[2].find_all('td', {'class': ['bnorm']})
    for item in table_columns:
        if 'title' in item.span.attrs:
            team_2_stats[item.span.attrs['title'].lower().replace(' ', '_')] = []
        else:
            team_2_stats[stat_table_text_to_title[item.span.text]] = []
    stat_keys = deepcopy(list(team_2_stats.keys()))
    team_2_stats['player'] = []
    team_2_stats['subbed_on'] = []
    team_2_stats['subbed_off'] = []
    team_2_stats['unused_sub'] = []
    players = team_2[3:][1:]
    for player in players:
        name_row = player.find_next('a').find_parent()
        if 'href' in name_row.find_next('a').attrs:
            if name_row.text == 'Head to Head':
                break  # end of table
            elif name_row.find_next('a').attrs["href"].startswith('pp-'):
                team_2_stats['player'].append(name_row.find_next('a').attrs["href"])
                if player.findChild('span') is None:
                    team_2_stats['subbed_on'].append(False)
                    team_2_stats['subbed_off'].append(False)
                elif player.findChild('span')['title'] == 'Subbed Off':
                    team_2_stats['subbed_on'].append(False)
                    team_2_stats['subbed_off'].append(True)
                elif player.findChild('span')['title'] in ['Subbed On', 'Activated Substitute']:
                    team_2_stats['subbed_on'].append(True)
                    team_2_stats['subbed_off'].append(False)

                # check if unused sub
                if name_row.find_next().find_next().text == 'Unused Substitute':
                    team_2_stats['unused_sub'].append(True)
                    for k in stat_keys:
                        team_2_stats[k].append(np.nan)
                else:
                    team_2_stats['unused_sub'].append(False)
                    stats = player.find_all('td', {'class': 'statdata'})
                    for k, s in zip(stat_keys, stats):
                        team_2_stats[k].append(int(s.text))

    team_2_frame = pd.DataFrame(team_2_stats)
    team_2_frame['team'] = away_team
    team_2_stats['unused_sub']
    result_frame = pd.concat([team_1_frame, team_2_frame])

    if brownlow_flag:
        result_frame['brownlow_votes'] = 0

        result_frame.loc[result_frame.player == one_vote.attrs['href'], 'brownlow_votes'] = 1
        result_frame.loc[result_frame.player == two_votes.attrs['href'], 'brownlow_votes'] = 2
        result_frame.loc[result_frame.player == three_votes.attrs['href'], 'brownlow_votes'] = 3
    else:
        result_frame['brownlow_votes'] = np.nan

    return result_frame

def get_match_details(footy_wire_match_id: int) -> pd.DataFrame:
    '''
    Scrapes detailed match statistics from footywire for a given match.
    Please use sparingly so as not to spam the site.

    Args:
        footy_wire_match_id (int): _description_

    Returns:

    '''

    url = f'https://www.footywire.com/afl/footy/ft_match_statistics?mid={footy_wire_match_id}'



    page = requests.get(url)

    soup = BeautifulSoup(page.content, "html.parser")

    player_stats = _detail_helper_player_stats(soup)
    player_stats['footy_wire_match_id'] = footy_wire_match_id

    return player_stats


if __name__ == '__main__':

    matches = pd.read_parquet(os.path.join('../../datadump', f'matches_2015.pq'))

    match_ids = matches.footy_wire_match_id.unique()

    players = []
    for mid in match_ids:
        players.append(get_match_details(mid))

    player_frame = pd.concat(players)

    player_frame.to_parquet(os.path.join('../../datadump', f'player_2015.pq'))

    player_frame