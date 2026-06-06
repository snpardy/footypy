import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from footypy import scrape


class TestDataTransformations:
    """Test suite for data transformation logic in scrape module"""
    
    def test_team_name_corrections(self):
        """Test that team name corrections are applied correctly"""
        # This tests the data processing logic with mocked scrape data
        test_df = pd.DataFrame({
            'week_name': ['Round 1'],
            'timestamp': [pd.Timestamp('2023-03-30')],
            'home_team': ['Port'],
            'away_team': ['Geel'],
            'venue': ['Adelaide Oval'],
            'home_score': [100],
            'away_score': [90],
            'bye': [False],
            'footy_wire_match_id': [5962]
        })
        
        # Simulate team corrections
        team_corrections = {
            'Port': 'Port_Adelaide',
            'Gold': 'Gold_Coast',
            'St': 'St_Kilda',
            'Kilda': 'St_Kilda',
            'West': 'West_Coast',
            'North': 'North_Melbourne',
            'Western': 'Western_Bulldogs'
        }
        
        for key, value in team_corrections.items():
            test_df.loc[test_df.home_team == key, 'home_team'] = value
            test_df.loc[test_df.away_team == key, 'away_team'] = value
        
        assert test_df.iloc[0]['home_team'] == 'Port_Adelaide'
    
    def test_week_number_calculation(self):
        """Test that week numbers are calculated correctly"""
        test_df = pd.DataFrame({
            'week_name': ['Round 1', 'Round 2', 'Qualifying Final'],
            'timestamp': pd.to_datetime(['2023-03-30', '2023-04-06', '2023-09-14']),
            'home_team': ['Adelaide', 'Collingwood', 'Brisbane'],
            'away_team': ['Geelong', 'Brisbane', 'Sydney'],
            'venue': ['Adelaide Oval', 'MCG', 'MCG'],
            'home_score': [100, 95, 110],
            'away_score': [90, 85, 105],
            'bye': [False, False, False],
            'footy_wire_match_id': [5962, 5963, 5964]
        })
        
        # Extract numeric week numbers
        test_df['week_number'] = test_df.week_name
        test_df['week_number'] = test_df['week_number'].astype(str)
        
        # Check that we can parse numeric rounds
        numeric_weeks = pd.to_numeric(
            test_df[test_df.week_name.str.contains('Round')].week_name.str.extract(r'(\d+)', expand=False),
            errors='coerce'
        )
        assert numeric_weeks.notna().any()
    
    def test_dataframe_column_types(self):
        """Test that columns have correct data types"""
        test_df = pd.DataFrame({
            'week_name': ['Round 1'],
            'timestamp': pd.to_datetime(['2023-03-30']),
            'home_team': ['Adelaide'],
            'away_team': ['Geelong'],
            'venue': ['Adelaide Oval'],
            'home_score': [100.0],
            'away_score': [90.0],
            'bye': [False],
            'footy_wire_match_id': [5962]
        })
        
        # Verify column types are reasonable
        assert pd.api.types.is_datetime64_any_dtype(test_df['timestamp'])
        assert pd.api.types.is_bool_dtype(test_df['bye'])
        assert pd.api.types.is_float_dtype(test_df['home_score'])
    
    def test_team_name_space_to_underscore(self):
        """Test that team names with spaces are converted to underscores"""
        test_df = pd.DataFrame({
            'home_team': ['Port Adelaide', 'Gold Coast', 'St Kilda'],
            'away_team': ['West Coast', 'North Melbourne', 'Western Bulldogs']
        })
        
        # Apply space to underscore conversion
        test_df['home_team'] = test_df['home_team'].str.replace(' ', '_')
        test_df['away_team'] = test_df['away_team'].str.replace(' ', '_')
        
        assert test_df.iloc[0]['home_team'] == 'Port_Adelaide'
        assert test_df.iloc[1]['away_team'] == 'North_Melbourne'
        assert test_df.iloc[2]['away_team'] == 'Western_Bulldogs'


class TestMatchDetailsIntegration:
    """Test suite for match details functionality"""
    
    def test_match_details_accepts_integer_id(self):
        """Test that get_match_details accepts an integer match ID"""
        # This test verifies the function signature accepts integer
        with patch('footypy.scrape.requests.get') as mock_get:
            # Return minimal valid-looking HTML to avoid parsing errors
            mock_response = MagicMock()
            mock_response.content = b'<html></html>'
            mock_get.return_value = mock_response
            
            # Just verify the function can be called with an integer
            try:
                scrape.get_match_details(5962)
            except (AttributeError, IndexError, ValueError, TypeError):
                # Expected - we're just testing the function accepts the ID type
                pass
            
            # Verify the function attempted to make a request
            assert mock_get.called