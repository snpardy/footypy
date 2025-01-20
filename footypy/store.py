import os

import duckdb
import pandas as pd

from footypy import scrape


class Store():

    def __init__(self, path: str):
        new_db = not os.path.isfile(path)
        self.path = path
        self.connection = duckdb.connect(path)
        
        if new_db:
            print('creating new tables')
            create_tables = '''
            CREATE TABLE results (
                match_id               INTEGER NOT NULL,
                footy_wire_match_id    INTEGER,
                timestamp              DATETIME,
                week_name              VARCHAR,
                week_number            INTEGER,
                home_team              VARCHAR,
                away_team              VARCHAR,
                venue                  VARCHAR,
                home_score             INTEGER,
                away_score             INTEGER,
                bye                    BOOL,
                PRIMARY KEY (match_id)
            );

            CREATE TABLE match_details (
                player_match_id        VARCHAR NOT NULL,
                match_id               INTEGER NOT NULL,
                footy_wire_match_id    INTEGER NOT NULL,
                kicks                  INTEGER,
                handballs              INTEGER,
                disposals              INTEGER,
                marks                  INTEGER,
                goals                  INTEGER,
                behinds                INTEGER,
                tackles                INTEGER,
                hitouts                INTEGER,
                goal_assists           INTEGER,
                inside_50s             INTEGER,
                clearances             INTEGER,
                clangers               INTEGER,
                rebound_50s            INTEGER,
                frees_for              INTEGER,
                frees_against          INTEGER,
                afl_fantasy            INTEGER,
                supercoach             INTEGER,
                player                 VARCHAR,
                subbed_on              BOOL,
                subbed_off             BOOL,
                unused_sub             BOOL,
                team                   VARCHAR,
                brownlow_votes         FLOAT,
            );
            '''            
            self.connection.sql(create_tables)

    def get_full_year_results(self, year: int, end_year: int = None, force_update: bool = False) -> pd.DataFrame:    
        '''
        Return full year match results for given years.
        Updates store with missing years.
        Only calls scrape function for years not present in store.

        Args:
            year (int): first year of results
            end_year (int, optional): final year of results. Defaults to *year*.
            force_update (bool, optional): force scrapers to run for years currently in store. Defaults to False.

        Returns:
            pd.DataFrame: match results from the results table
        '''        
        end_year = year if end_year is None else end_year
        years = list(range(year, end_year+1))
        if force_update:
            filled_years = {}
        else:
            filled_years = {y[0] for y in 
                                self.connection.execute('''
                                    SELECT
                                    year(timestamp) as year,
                                    count(*)
                                    from results
                                    where year(timestamp) in ?
                                    group by year(timestamp) 
                                    ''', [years]).fetchall()}
        
        scrape_years = list(set(years) - filled_years)
        for year in scrape_years:
            df = scrape.get_full_year_results(year)
            # construct match id: year + round_n + home_team ordered rank (e.g Adelaide is 1)
            rank_lookup = {}
            for v, k in  enumerate(sorted(df.home_team.unique())):
                rank_lookup[k] = v

            df['match_id'] = (
                str(year) + 
                (df.week_number+10).astype(str) + 
                (df.home_team.map(rank_lookup)+10).astype(str)  # add 10s here to make ordering sensible
                ).astype(int)  

            duplicates = df[df.match_id.duplicated(keep=False)]
            if not duplicates.empty:
                if duplicates.iloc[0].week_name == 'Grand Final':  # drawn grand final, incr match week
                    second_index = duplicates[duplicates.timestamp != duplicates.timestamp.min()].index[0]
                    df.loc[second_index, 'week_number'] += 1
                    df['match_id'] = (
                        str(year) + 
                        (df.week_number+10).astype(str) + 
                        (df.home_team.map(rank_lookup)+10).astype(str)  # add 10s here to make ordering sensible
                    ).astype(int)  
                else:
                    raise(f'Duplicated match id: {duplicates}')

            replace_query = 'INSERT OR REPLACE INTO results BY NAME SELECT * FROM df'

            self.connection.sql(replace_query)
            
        df = self.connection.execute('SELECT * FROM results where year(timestamp) in ?', [years]).df()
        
        return df

    def get_match_details_results(self, footy_wire_match_ids: list, force_update: bool = False) -> pd.DataFrame:
        if force_update:
            filled_matches = set()
        else:
            filled_matches = {y[0] for y in 
                                self.connection.execute('''
                                    SELECT
                                    footy_wire_match_id,
                                    count(*)
                                    from match_details
                                    where footy_wire_match_id in ?
                                    group by footy_wire_match_id
                                    ''', [footy_wire_match_ids]).fetchall()}
        
        scrape_matches = list(set(footy_wire_match_ids) - filled_matches)
        
        match_id_lookup = {r[0]: r[1] for r in 
                           (
                               self
                               .connection.execute(
                                   'SELECT DISTINCT footy_wire_match_id, match_id from results WHERE footy_wire_match_id in ?',
                                   [scrape_matches])
                               .fetchall()
                           )
        }

        for match in scrape_matches:
            try:
                df = scrape.get_match_details(match)
                
                df['match_id'] = df.footy_wire_match_id.map(match_id_lookup)
                df['player_match_id'] =  df.player + '_' + df.match_id.astype(str)
                replace_query = 'INSERT OR REPLACE INTO match_details BY NAME SELECT * FROM df'

                self.connection.sql(replace_query)
            
            except Exception:
                print(f'Scraper error for footy_wire_match_id: {match}')
                            
        df = self.connection.execute('SELECT * FROM match_details where footy_wire_match_id in ?', [footy_wire_match_ids]).df()
        
        return df

    def execute(self, query, params=None):
        return self.connection.execute(query, params).df()
