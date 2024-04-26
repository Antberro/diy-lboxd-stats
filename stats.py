import os
import pandas as pd
import yaml
from functools import reduce
import requests
import time


def main():

    start_time = time.time()

    movies = pd.read_csv(os.path.join('generated', 'movies.csv'))
    movies = movies.drop_duplicates(subset=['Movie URI'])
    stats = {}

    # Compute `Summary` stats
    all_directors = reduce(lambda acc, x: {*acc, *set(str(x).split('.'))}, movies['Directors'].tolist(), set())
    all_countries = reduce(lambda acc, x: {*acc, *set(str(x).split('.'))}, movies['Countries'].tolist(), set())
    stats['Summary'] = {}
    stats['Summary']['Films'] = len(movies)
    stats['Summary']['Hours'] = int(movies['Runtime'].sum() // 60)
    stats['Summary']['Directors'] = len(all_directors)
    stats['Summary']['Countries'] = len(all_countries)
    stats['Summary']['Longest_Streak'] = None

    # Compute `By Year` stats
    h1, h2, h3 = _make_by_year_histograms(movies)
    stats['By_Year'] = {}
    stats['By_Year']['Films'] = h1
    stats['By_Year']['Ratings'] = h2
    stats['By_Year']['Diary'] = h3

    # Compute `Highest Rated Decades` stats
    stats['Highest_Rated_Decades'] = _compute_highest_rated_decades(movies)

    # Compute `Genres, Countries, and Languages` stats
    for category in ('Genres', 'Countries', 'Languages'):
        hists = _make_gcl_histograms(movies, category)
        stats[category] = {}
        for metric in ('Most_Watched', 'Highest_Rated'):
            stats[category][metric] = hists[metric]

    # Compute `Most Watched` stats
    stats['Most_Watched'] = _compute_most_watched(movies)

    # Compute `Rated Higher Than Average` stats
    highs, lows = _compute_high_and_low(movies)
    stats['Rated_Higher_Than_Avg'] = highs

    # Compute `Rated Lower Than Average` stats
    stats['Rated_Lower_Than_Avg'] = lows

    # Compute `Actors` stats
    hists = _make_credits_histograms(movies, 'Actors')
    stats['Actors'] = {}
    stats['Actors']['Most_Watched'] = hists['Most_Watched']
    stats['Actors']['Highest_Rated'] = hists['Highest_Rated']

    # Compute `Directors` stats
    hists = _make_credits_histograms(movies, 'Directors')
    stats['Directors'] = {}
    stats['Directors']['Most_Watched'] = hists['Most_Watched']
    stats['Directors']['Highest_Rated'] = hists['Highest_Rated']

    # Compute `World_Map` stats
    stats['World_Map'] = None

    # Write stats to YAML file
    os.mkdir('stats')
    yaml_path = os.path.join('stats', 'all-time-stats.yaml')
    with open(yaml_path, 'w') as file:
        yaml.dump(stats, file, default_flow_style=False)

    print(f'\nCompleted in {round(time.time() - start_time, 3)} seconds')
    print('Successfully created all-time-stats.yaml!')

    year_options = sorted(movies['Watched Date'].dropna().map(lambda x: int(str(x).split('-')[0])).drop_duplicates().tolist())
    for year in year_options:
        process_stats_per_year(movies, year)


def process_stats_per_year(movies: pd.DataFrame, year: int):
    '''
    Compute stats per `year`.
    '''

    start_time = time.time()
    
    ymovies = movies[movies['Logged'] == True]
    ymovies = ymovies[ymovies['Watched Date'].str.contains(str(year))]

    year_stats = {}

    # Compute `Summary` stats
    year_stats['Year'] = year
    year_stats['Summary'] = {}
    year_stats['Summary']['Diary_Entries'] = len(ymovies)
    year_stats['Summary']['Reviews'] = len(ymovies[ymovies['Reviewed'] == True])
    year_stats['Summary']['Lists'] = None
    year_stats['Summary']['Likes'] = None
    year_stats['Summary']['Comments'] = None
    year_stats['Summary']['Hours'] = int(ymovies['Runtime'].sum() // 60)

    # Compute `Highest Rated Films` stats
    year_stats['Highest_Rated'] = _compute_highest_rated(ymovies, year)

    # Compute `By Week` stats
    year_stats['By_Week'] = None

    # Compute `Milestones` stats
    milestones = _compute_milestones(ymovies)
    year_stats['Milestones'] = {}
    year_stats['Milestones']['First'] = milestones['First']
    year_stats['Milestones']['Last'] =  milestones['Last']

    # Compute `Most Watched` stats
    year_stats['Most_Watched'] = _compute_most_watched(ymovies)

    # Compute `Genres, Countries, and Languages` stats
    for category in ('Genres', 'Countries', 'Languages'):
        hists = _make_gcl_histograms(ymovies, category)
        year_stats[category] = {}
        for metric in ('Most_Watched', 'Highest_Rated'):
            year_stats[category][metric] = hists[metric]

    # Compute `Breakdown` stats
    pc = _compute_breakdown(ymovies, year)
    year_stats['Breakdown'] = {}
    year_stats['Breakdown']['Current_Year_Releases'] = pc['Current_Year_Releases']
    year_stats['Breakdown']['Watches'] = pc['Watches']
    year_stats['Breakdown']['Reviewed'] = pc['Reviewed']
    year_stats['Breakdown']['Ratings_Spread'] = pc['Ratings_Spread']
    
    # Compute `Actors` stats
    hists = _make_credits_histograms(ymovies, 'Actors')
    year_stats['Actors'] = {}
    year_stats['Actors']['Most_Watched'] = hists['Most_Watched']
    year_stats['Actors']['Highest_Rated'] = hists['Highest_Rated']

    # Compute `Directors` stats
    hists = _make_credits_histograms(ymovies, 'Directors')
    year_stats['Directors'] = {}
    year_stats['Directors']['Most_Watched'] = hists['Most_Watched']
    year_stats['Directors']['Highest_Rated'] = hists['Highest_Rated']

    # Compute `Highs and Lows` stats
    hl2 = _compute_high_and_low_2(ymovies)
    year_stats['High_And_Lows'] = {}
    year_stats['High_And_Lows']['Highest_Average'] = hl2['Highest_Average']
    year_stats['High_And_Lows']['Lowest_Average'] = hl2['Lowest_Average']
    year_stats['High_And_Lows']['Most_Popular'] = hl2['Most_Popular']
    year_stats['High_And_Lows']['Most_Obscure'] = hl2['Most_Obscure']

    # Compute `Rated Higher Than Average` stats
    highs, lows = _compute_high_and_low(ymovies)
    year_stats['Rated_Higher_Than_Avg'] = highs

    # Compute `Rated Lower Than Average` stats
    year_stats['Rated_Lower_Than_Avg'] = lows

    # Write stats to YAML file
    yaml_path = os.path.join('stats', f'{year}-stats.yaml')
    with open(yaml_path, 'w') as file:
        yaml.dump(year_stats, file, default_flow_style=False)

    print(f'\nCompleted in {round(time.time() - start_time, 3)} seconds')
    print(f'Successfully created {year}-stats.yaml!')


def _map_values(value, from_min=1, from_max=10, to_min=0.5, to_max=5):
    '''
    Map tmdb score (1 - 10 stars) to letterboxd score (0.5 - 5 stars)
    '''
    from_range = from_max - from_min
    to_range = to_max - to_min
    mapped_value = to_min + (value - from_min) * (to_range / from_range)
    return mapped_value


def _get_countries_list() -> list:
        res = requests.get('https://restcountries.com/v3.1/all')
        data = res.json()
        return [x['name']['common'] for x in data]


def MovieObj(name: str, year: int, uri: str, poster: str) -> dict:
    '''Represents a movie.'''
    return {'Name': name, 'Year': year, 'URI': uri, 'Poster': poster}


def HistogramObj(bin_label: str, bins: list, values_label: str, values: list) -> dict:
    '''Represents a histogram.'''
    assert len(bins) == len(values), 'Length of `bins` and `values` must be equal!'
    return {bin_label: bins, values_label: values}


# `All-time` helpers


def _compute_highest_rated_decades(
        movies: pd.DataFrame, 
        TOP_K_DECADES: int = 3,
        MIN_FILMS_PER_DECADE: int = 5,
        MAX_FILMS_PER_DECADE: int = 20,
        ) -> list:
    '''
    Computes the `TOP_K_DECADES` highest rated decades based on user's average rating. Each decade
    category must have between `MIN_FILMS_PER_DECADE` and `MAX_FILMS_PER_DECADE`
    films to be considered.
    '''

    results = []
    
    _movies = movies[movies['Rated'] == True]
    _movies.insert(len(_movies.columns), 'Decade', _movies['Year'].map(lambda y: str(y)[:-1] + '0s'))
    grouped = _movies.groupby('Decade').agg(count=('Decade', 'size'), average_rating=('Rating', 'mean')).reset_index()
    grouped = grouped[grouped['count'] >= MIN_FILMS_PER_DECADE]
    grouped = grouped.sort_values(by='average_rating', ascending=False)
    
    for _,group in grouped.head(TOP_K_DECADES).iterrows():

        decade = group['Decade']
        avg_rating = round(group['average_rating'], 2)
        items = _movies[_movies['Decade'] == decade]
        items = items.sort_values(by='Rating', ascending=False)
        items = items.head(MAX_FILMS_PER_DECADE)
        items = [MovieObj(x['Name'], x['Year'], x['Movie URI'], x['Poster URI']) for _,x in items.iterrows()]

        results.append({
            'Decade': decade,
            'Average_Rating': avg_rating,
            'Movies': items
        })
    
    return results


def _compute_most_watched(movies: pd.DataFrame, TOP_K_FILMS: int = 10) -> list:
    '''
    Computes the `TOP_K_FILMS` rewatched the most by the user.
    '''

    results = []

    _movies = movies[movies['Rewatch'] == 'Yes']
    _movies.insert(len(_movies.columns), 'Times Rewatched', [len(movies[movies['Movie URI'] == x['Movie URI']]) for _,x in _movies.iterrows()])
    _movies = _movies.sort_values(by='Times Rewatched', ascending=False)
    _movies = _movies.head(TOP_K_FILMS)

    for _,movie in _movies.iterrows():
        if movie['Times Rewatched'] > 1:
            item = MovieObj(movie['Name'], movie['Year'], movie['Movie URI'], movie['Poster URI'])
            times_rewatched = movie['Times Rewatched']
            results.append({'Movie': item, 'Times_Rewatched': times_rewatched})

    return results


def _make_by_year_histograms(movies: pd.DataFrame, MIN_FILMS_YEAR: int = 3) -> tuple:
    '''
    Make histograms for `By Year` section.
    '''

    start_year = movies.sort_values(by='Year', ascending=True)['Year'].head(1).item()
    stop_year = movies.sort_values(by='Year', ascending=True)['Year'].tail(1).item()
    years = list(range(start_year, stop_year+1))

    # Films by Year 
    grouped1 = movies.groupby('Year').size().reset_index(name='Count')
    grouped1 = grouped1.sort_values(by='Year', ascending=True)
    counts = [grouped1[grouped1['Year'] == y]['Count'].item() if y in grouped1['Year'].tolist() else 0 for y in years]
    h1 = HistogramObj('Year', years, 'Count', counts)

    # Avg Rating per Year
    grouped2 = movies[movies['Rated'] == True]
    grouped2 = grouped2.groupby('Year').agg(count=('Year', 'size'), average_rating=('Rating', 'mean')).reset_index()
    grouped2 = grouped2[grouped2['count'] >= MIN_FILMS_YEAR]
    grouped2 = grouped2.sort_values(by='Year', ascending=True)
    avg_rating = [round(grouped2[grouped2['Year'] == y]['average_rating'].item(), 2) if y in grouped2['Year'].tolist() else 0 for y in years]
    h2 = HistogramObj('Year', years.copy(), 'Rating', avg_rating)

    # Diary per Year
    grouped3 = movies[movies['Logged'] == True]
    grouped3.loc[:, 'Watched Date'] = grouped3['Watched Date'].map(lambda x: int(x.split('-')[0]))
    grouped3 = grouped3.groupby('Watched Date').size().reset_index(name='Count')
    grouped3 = grouped3.sort_values(by='Watched Date', ascending=True)
    start_watched_year = grouped3['Watched Date'].head(1).item()
    stop_watched_year = grouped3['Watched Date'].tail(1).item()
    watched_years = list(range(start_watched_year, stop_watched_year+1))
    watched_counts = [grouped3[grouped3['Watched Date'] == y]['Count'].item() if y in grouped3['Watched Date'].tolist() else 0 for y in watched_years]
    h3 = HistogramObj('Year', watched_years, 'Count', watched_counts)

    return h1, h2, h3


def _make_gcl_histograms(
        movies: pd.DataFrame, 
        column: str, 
        MIN_FILMS_PER_CATEGORY: int = 3,
        MAX_FILMS_PER_CATEGORY: int = 10
        ) -> tuple:
    '''
    Make histograms for `Genres, Countries, and Languages` section.
    '''

    result = {}

    vals = movies[column].dropna().tolist()
    all_vals = reduce(lambda acc, x: [*acc, *set(str(x).split('.'))], vals, [])
    data_dict = {column: [], 'Count': [], 'Average Rating': []}
    for val in all_vals:
        data_dict[column].append(val)
        data_dict['Count'].append(1)

        _movies = movies.dropna(subset=[column])
        _movies = _movies[_movies['Rated'] == True]
        _movies = _movies[_movies[column].str.contains(val)]['Rating']
        if len(_movies) >= MIN_FILMS_PER_CATEGORY:
            avg_rating = round(_movies.mean(), 2)
        else:
            avg_rating = 0
        data_dict['Average Rating'].append(avg_rating)

    grouped = pd.DataFrame(data_dict)
    grouped = grouped.groupby(column).agg(total=('Count', 'sum'), average_rating=('Average Rating', 'first')).reset_index()
    
    grouped_total = grouped.sort_values(by='total', ascending=False).head(MAX_FILMS_PER_CATEGORY)
    result['Most_Watched'] = HistogramObj(column, grouped_total[column].tolist(), 'Count', grouped_total['total'].tolist())
    
    grouped_rating = grouped.sort_values(by='average_rating', ascending=False).head(MAX_FILMS_PER_CATEGORY)
    result['Highest_Rated'] = HistogramObj(column, grouped_rating[column].tolist(), 'Average_Rating', grouped_rating['average_rating'].tolist())

    return result


def _compute_high_and_low(movies: pd.DataFrame, MIN_NUM_FILMS: int = 3, MAX_NUM_FILMS: int = 12) -> dict:
    '''
    Compute stats for `Rated Higher Than Average` and `Rated Lower Than Average` sections.
    '''

    _movies = movies[movies['Rated'] == True]
    _movies = _movies.dropna(subset=['Average Rating'])
    _movies = _movies[_movies['Average Rating'] != 0]
    _movies.loc[:, 'Average Rating'] = _movies['Average Rating'].map(lambda x: _map_values(x))
    _movies.insert(len(_movies.columns), 'Diff', [round(m['Rating'] - m['Average Rating'], 2) for _,m in _movies.iterrows()])
    _movies = _movies.sort_values(by='Diff', ascending=False)

    highs, lows = [], []

    for _,m in _movies.head(MAX_NUM_FILMS).iterrows():
        highs.append({
            'Movie': MovieObj(m['Name'], m['Year'], m['Movie URI'], m['Poster URI']),
            'Rating': m['Rating'],
            'Average Rating': m['Average Rating'],
            'Diff': m['Diff']
        })

    for _,m in _movies.tail(MAX_NUM_FILMS).iterrows():
        lows.append({
            'Movie': MovieObj(m['Name'], m['Year'], m['Movie URI'], m['Poster URI']),
            'Rating': m['Rating'],
            'Average Rating': m['Average Rating'],
            'Diff': m['Diff']
        })

    return highs, lows


def _make_credits_histograms(movies: pd.DataFrame, column: str):
    '''
    Make histograms for `Actors` and `Directors` sections.
    '''

    credits_df = pd.read_csv(os.path.join('generated', 'credits.csv'))
    credits_df = credits_df[credits_df['category'] == column]

    hists = _make_gcl_histograms(movies, column)

    for category in ('Most_Watched', 'Highest_Rated'):
        ids = hists[category][column]
        names = [credits_df[credits_df['id'] == int(i)]['name'].item() for i in ids]
        profiles = [credits_df[credits_df['id'] == int(i)]['profile_path'].item() for i in ids]
        hists[category][column] = [{'Name': names[i], 'Profile URI': profiles[i]} for i in range(len(ids))]
    
    return hists


def _get_world_map_stats(movies: pd.DataFrame):
    raise NotImplementedError


# `Year` helpers


def _compute_highest_rated(movies: pd.DataFrame, year: int, TOP_K = 8) -> list:
    '''
    Compute `TOP_K` highest rated movies.
    '''
    _ranked = movies[movies['Year'] == year]
    _ranked = _ranked.sort_values(by='Rating', ascending=False)
    _ranked = _ranked.head(TOP_K)
    result = [{
        'Movie': MovieObj(m['Name'], m['Year'], m['Movie URI'], m['Poster URI']),
        'Rating': m['Rating']} for _,m in _ranked.iterrows()]
    return result


def _compute_milestones(movies: pd.DataFrame) -> dict:
    '''
    Compute first and last films watched.
    '''

    _sorted = movies.sort_values(by='Watched Date', ascending=True).reset_index(drop=True)

    first, last = _sorted.head(1), _sorted.tail(1)
    first = {
        'Movie': MovieObj(first['Name'].item(), first['Year'].item(), first['Movie URI'].item(), first['Poster URI'].item()),
        'Date': '-'.join(first['Watched Date'].item().split('-')[1:])
    }
    last = {
        'Movie': MovieObj(last['Name'].item(), last['Year'].item(), last['Movie URI'].item(), last['Poster URI'].item()),
        'Date': '-'.join(last['Watched Date'].item().split('-')[1:])
    }
    
    return {'First': first, 'Last': last}


def _compute_breakdown(movies: pd.DataFrame, year: int) -> dict:
    '''
    Compute pie chart data.
    '''

    result = {}
    
    # Current year releases vs older
    grouped1_y = movies[movies['Year'] == year]
    grouped1_ny = movies[movies['Year'] != year]
    result['Current_Year_Releases'] = {}
    result['Current_Year_Releases'][f'{year}_Releases'] = len(grouped1_y)
    result['Current_Year_Releases']['Older'] = len(grouped1_ny)
    result['Current_Year_Releases']['Total'] = len(grouped1_y) + len(grouped1_ny)

    # Watches vs rewatches
    grouped2_w = movies[movies['Rewatch'] != 'Yes']
    grouped2_r = movies[movies['Rewatch'] == 'Yes']
    result['Watches'] = {}
    result['Watches']['Watches'] = len(grouped2_w)
    result['Watches']['Rewatches'] = len(grouped2_r)
    result['Watches']['Total'] = len(grouped2_w) + len(grouped2_r)

    # Reviewed vs not reviewed
    grouped3_r = movies[movies['Reviewed'] == True]
    grouped3_nr = movies[movies['Reviewed'] == False]
    result['Reviewed'] = {}
    result['Reviewed']['Reviewed'] = len(grouped3_r)
    result['Reviewed']['Not_Reviewed'] = len(grouped3_nr)
    result['Reviewed']['Total'] = len(grouped3_r) + len(grouped3_nr)

    # Ratings spread histogram
    grouped4 = movies.groupby('Rating').size().reset_index(name='Count')
    grouped4 = grouped4.sort_values(by='Rating', ascending=True)
    bins =  [i/10 for i in range(5, 55, 5)]
    counts = [grouped4[grouped4['Rating'] == i]['Count'].item() if i in grouped4['Rating'].tolist() else 0 for i in bins]
    h = HistogramObj('Rating', bins, 'Count', counts)
    result['Ratings_Spread'] = h

    return result
    

def _compute_high_and_low_2(movies: pd.DataFrame) -> dict:
    '''
    Compute high and low stats year specific page.
    '''

    result = {}
    _movies = movies[movies['Rated'] == True]

    # Highest and lowest average rating
    _sorted1 = _movies.dropna(subset=['Average Rating'])
    _sorted1 = _sorted1.sort_values(by='Average Rating', ascending=False)
    _sorted1.loc[:, 'Average Rating'] = [_map_values(x) for x in _sorted1['Average Rating']]
    high, low = _sorted1.head(1), _sorted1.tail(1)
    high = {
        'Movie': MovieObj(high['Name'].item(), high['Year'].item(), high['Movie URI'].item(), high['Poster URI'].item()),
        'Rating': high['Rating'].item()
    }
    low = {
        'Movie': MovieObj(low['Name'].item(), low['Year'].item(), low['Movie URI'].item(), low['Poster URI'].item()),
        'Rating': low['Rating'].item()
    }
    result['Highest_Average'] = high
    result['Lowest_Average'] = low

    # Most and least popular
    _sorted2 = _movies.dropna(subset=['Popularity'])
    _sorted2 = _sorted2.sort_values(by='Popularity', ascending=False)
    pop, unpop = _sorted2.head(1), _sorted2.tail(1)
    pop = {
        'Movie': MovieObj(pop['Name'].item(), pop['Year'].item(), pop['Movie URI'].item(), pop['Poster URI'].item()),
        'Rating': pop['Rating'].item()
    }
    unpop = {
        'Movie': MovieObj(unpop['Name'].item(), unpop['Year'].item(), unpop['Movie URI'].item(), unpop['Poster URI'].item()),
        'Rating': unpop['Rating'].item()
    }
    result['Most_Popular'] = pop
    result['Most_Obscure'] = unpop

    return result


if __name__ == '__main__':
    main()