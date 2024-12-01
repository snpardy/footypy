import os

import duckdb
import pandas as pd

from footypy import scrape


class Store():

    def __init__(self, path: str):
        print('init')
        new_db = not os.path.isfile(path)
        self.path = path
        self.connection = duckdb.connect(path)
        
        if new_db:
            print('creating new tables')
            create_results = '''
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
            
            '''
            # CREATE TABLE player_match_details (
                
            # );
            
            self.connection.sql(create_results)

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
        pass 
          

if __name__ == '__main__':
    path = '../test_store.db'
    store = Store(path)
    
    df = store.get_full_year_results(2015, 2024)
    
    df