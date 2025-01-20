# FootyPy

A python package for Australian Rules Football data and statistics.

Exposes `scrape` and `store` modules.

The functions in `scrape` can be used to directly scrape result and performance data from AFL matches.

The intention of the `store` module is to enable a convenient layer of protection against spamming the websites that host the data. The `Store` class is a wrapper around a duckdb database and the scraping functions. It will first check the local database before scraping (and saving) new data:

```python
import  footypy as fp

path = 'footypy.db'
store = fp.store.Store(path)
results = store.get_full_year_results(2004, 2023)  # all data is scraped

recent_results = store.get_full_year_results(2020, 2024)  # only 2024 is scraped

# the store can be queried like any duckdb database
store.execute("SELECT * from results WHERE home_team = 'Richmond' and year(timestamp) = 2024")
```

Currently, team level match results and individual player match performance statistics are available.

Package name is of course inspired by the [iconic ad](https://www.youtube.com/watch?v=kPyGrU2Ow8w).