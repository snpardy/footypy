import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import patch, MagicMock
from footypy import store


class TestStoreInitialization:
    """Test suite for Store class initialization"""
    
    def test_store_creates_connection(self):
        """Test that Store creates a DuckDB connection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            assert s.connection is not None
            assert s.path == db_path
    
    def test_store_creates_tables(self):
        """Test that Store creates required tables on new database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            # Query for table existence
            tables = s.connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            
            assert 'results' in table_names
            assert 'match_details' in table_names
    
    def test_store_results_table_schema(self):
        """Test that results table has correct columns"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            # Query for column names
            columns = s.connection.execute(
                "PRAGMA table_info(results)"
            ).fetchall()
            column_names = [col[1] for col in columns]
            
            required_columns = [
                'match_id', 'footy_wire_match_id', 'timestamp', 'week_name',
                'week_number', 'home_team', 'away_team', 'venue',
                'home_score', 'away_score', 'bye'
            ]
            for col in required_columns:
                assert col in column_names
    
    def test_store_match_details_table_schema(self):
        """Test that match_details table has correct columns"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            # Query for column names
            columns = s.connection.execute(
                "PRAGMA table_info(match_details)"
            ).fetchall()
            column_names = [col[1] for col in columns]
            
            required_columns = [
                'player_match_id', 'match_id', 'footy_wire_match_id', 'kicks',
                'handballs', 'disposals', 'marks', 'goals', 'behinds', 'tackles',
                'player', 'team'
            ]
            for col in required_columns:
                assert col in column_names


class TestStoreGetFullYearResults:
    """Test suite for Store.get_full_year_results"""
    
    def test_store_returns_dataframe(self):
        """Test that get_full_year_results returns a DataFrame"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            # Mock scrape function
            mock_df = pd.DataFrame({
                'week_name': ['Round 1'],
                'week_number': [1],
                'timestamp': [pd.Timestamp('2023-03-30')],
                'home_team': ['Adelaide'],
                'away_team': ['Geelong'],
                'venue': ['Adelaide Oval'],
                'home_score': [100],
                'away_score': [90],
                'bye': [False],
                'footy_wire_match_id': [5962]
            })
            
            with patch('footypy.scrape.get_full_year_results', return_value=mock_df):
                result = s.get_full_year_results(2023)
                assert isinstance(result, pd.DataFrame)
    
    def test_store_single_year(self):
        """Test getting results for a single year"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            mock_df = pd.DataFrame({
                'week_name': ['Round 1', 'Round 2'],
                'week_number': [1, 2],
                'timestamp': pd.to_datetime(['2023-03-30', '2023-04-06']),
                'home_team': ['Adelaide', 'Collingwood'],
                'away_team': ['Geelong', 'Brisbane'],
                'venue': ['Adelaide Oval', 'MCG'],
                'home_score': [100, 95],
                'away_score': [90, 85],
                'bye': [False, False],
                'footy_wire_match_id': [5962, 5963]
            })
            
            with patch('footypy.scrape.get_full_year_results', return_value=mock_df):
                result = s.get_full_year_results(2023)
                # Verify we got results back with at least 1 record
                assert len(result) >= 1
                # Verify the results table was populated
                assert not result.empty
    
    def test_store_year_range(self):
        """Test getting results for a range of years"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            mock_df_2023 = pd.DataFrame({
                'week_name': ['Round 1'],
                'week_number': [1],
                'timestamp': [pd.Timestamp('2023-03-30')],
                'home_team': ['Adelaide'],
                'away_team': ['Geelong'],
                'venue': ['Adelaide Oval'],
                'home_score': [100],
                'away_score': [90],
                'bye': [False],
                'footy_wire_match_id': [5962]
            })
            
            mock_df_2024 = pd.DataFrame({
                'week_name': ['Round 1'],
                'week_number': [1],
                'timestamp': [pd.Timestamp('2024-03-28')],
                'home_team': ['Collingwood'],
                'away_team': ['Brisbane'],
                'venue': ['MCG'],
                'home_score': [95],
                'away_score': [85],
                'bye': [False],
                'footy_wire_match_id': [6000]
            })
            
            def mock_scrape_side_effect(year, **kwargs):
                return mock_df_2023 if year == 2023 else mock_df_2024
            
            with patch('footypy.scrape.get_full_year_results', side_effect=mock_scrape_side_effect):
                result = s.get_full_year_results(2023, end_year=2024)
                # Should have results from both years
                assert len(result) >= 1


class TestStoreExecute:
    """Test suite for Store.execute method"""
    
    def test_execute_returns_dataframe(self):
        """Test that execute returns a DataFrame"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            # Insert test data
            test_df = pd.DataFrame({
                'match_id': [20231101],
                'footy_wire_match_id': [5962],
                'timestamp': [pd.Timestamp('2023-03-30')],
                'week_name': ['Round 1'],
                'week_number': [1],
                'home_team': ['Adelaide'],
                'away_team': ['Geelong'],
                'venue': ['Adelaide Oval'],
                'home_score': [100],
                'away_score': [90],
                'bye': [False]
            })
            
            s.connection.sql('INSERT INTO results BY NAME SELECT * FROM test_df')
            
            # Test execute query
            result = s.execute('SELECT * FROM results')
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1
            assert result.iloc[0]['home_team'] == 'Adelaide'
    
    def test_execute_with_where_clause(self):
        """Test execute with WHERE clause"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            s = store.Store(db_path)
            
            # Insert multiple test records
            test_df = pd.DataFrame({
                'match_id': [20231101, 20231102],
                'footy_wire_match_id': [5962, 5963],
                'timestamp': pd.to_datetime(['2023-03-30', '2023-04-06']),
                'week_name': ['Round 1', 'Round 2'],
                'week_number': [1, 2],
                'home_team': ['Adelaide', 'Collingwood'],
                'away_team': ['Geelong', 'Brisbane'],
                'venue': ['Adelaide Oval', 'MCG'],
                'home_score': [100, 95],
                'away_score': [90, 85],
                'bye': [False, False]
            })
            
            s.connection.sql('INSERT INTO results BY NAME SELECT * FROM test_df')
            
            # Test WHERE clause
            result = s.execute("SELECT * FROM results WHERE home_team = 'Adelaide'")
            assert len(result) == 1
            assert result.iloc[0]['home_team'] == 'Adelaide'
