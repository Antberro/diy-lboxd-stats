import os
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Manager
from tqdm import tqdm


search_url = lambda name, year: f'https://api.themoviedb.org/3/search/movie?query={name}&year={year}&page=1'
movie_url = lambda tmdb_id: f'https://api.themoviedb.org/3/movie/{tmdb_id}'
credits_url = lambda tmdb_id: f'https://api.themoviedb.org/3/movie/{tmdb_id}/credits'


def main():
    process()
    add_tmdb_data()


def process():
    '''
    Read and combine data from exported letterboxd data.
    '''

    watched_df = pd.read_csv(os.path.join('data', 'watched.csv'))
    ratings_df = pd.read_csv(os.path.join('data', 'ratings.csv'))
    diary_df = pd.read_csv(os.path.join('data', 'diary.csv'))
    reviews_df = pd.read_csv(os.path.join('data', 'reviews.csv'))

    columns = [
        'Rated',
        'Logged',
        'Reviewed',
        'Date',
        'Name',
        'Year',
        'Movie URI',
        'Runtime',
        'Countries',
        'Genres',
        'Languages',
        'Average Rating',
        'Popularity',
        'Poster URI',
        'Directors',
        'Actors',
        # 'Num Reviews',
        # 'Review',
    ]

    movies_df = pd.DataFrame({c: [None for _ in range(len(watched_df))] for c in columns})
    
    # Add data from watched.csv
    movies_df['Date'] = watched_df['Date']
    movies_df['Name'] = watched_df['Name']
    movies_df['Year'] = watched_df['Year']
    movies_df['Movie URI'] = watched_df['Letterboxd URI']

    # Add data from ratings.csv
    ratings_df = ratings_df.rename(columns={'Letterboxd URI': 'Movie URI'})
    movies_df['Rated'] = movies_df['Movie URI'].isin(ratings_df['Movie URI'].tolist())
    movies_df = movies_df.merge(ratings_df[['Rating', 'Movie URI']], how='left', on='Movie URI')

    # Add date from diary.csv
    diary_df = diary_df.rename(columns={'Letterboxd URI': 'Diary URI'})
    diary_df['Movie URI'] = [movies_df[(movies_df['Name'] == r['Name']) & (movies_df['Year'] == r['Year'])]['Movie URI'].head(1).item() for _,r in diary_df.iterrows()]
    movies_df['Logged'] = movies_df['Movie URI'].isin(diary_df['Movie URI'].tolist())
    movies_df = movies_df.merge(diary_df[['Rewatch', 'Tags', 'Watched Date', 'Diary URI', 'Movie URI']], how='left', on='Movie URI')

    # Add data from reviews.csv
    reviews_df['Movie URI'] = [movies_df[(movies_df['Name'] == r['Name']) & (movies_df['Year'] == r['Year'])]['Movie URI'].head(1).item() for _,r in reviews_df.iterrows()]
    movies_df['Reviewed'] = movies_df['Movie URI'].isin(reviews_df['Movie URI'].tolist())
    
    # Save
    os.mkdir('generated')
    movies_df.to_csv(os.path.join('generated', 'movies.csv'), index=False)
    print('Successfully created movies.csv!')


def add_tmdb_data(NUM_THREADS:int = 10):
    '''
    Add additional data from tmdb to `movies.csv`.
    '''

    start_time = time.time()
    print('Fetching movie data...')

    def process_job(job: dict, results_queue):
        name, year = job['Name'], job['Year']
        details = _get_movie_details(name, year)
        credits = _get_movie_credits(details['tmdb_id']) if details is not None else None
        if details is not None and credits is not None:
            results_queue.append({'Ok': True, 'Name': name, 'Year': year, 'Details': details, 'Credits': credits})
        else:
            results_queue.append({'Ok': False, 'Name': name, 'Year': year, 'Details': details, 'Credits': credits})
        
    movies = pd.read_csv(os.path.join('generated', 'movies.csv'))
    # movies = movies.head(100) # Limit jobs for debugging

    jobs = [{'Name': m['Name'], 'Year': m['Year']} for _,m in movies.iterrows()]

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        with Manager() as manager:
            results_queue = manager.list()
            futures = {executor.submit(process_job, job, results_queue): job for job in jobs}
            for future in as_completed(futures):
                future.result()

            # After completed
            print(f'\nCompleted in {round(time.time() - start_time, 3)} seconds')
            print(f'# successes: {len([x for x in results_queue if x["Ok"]])}')
            print(f'# failures: {len([x for x in results_queue if not x["Ok"]])}')

            # Save credits data
            columns = ['id', 'category', 'name', 'profile_path']
            data_dict = {c: [] for c in columns}
            for res in tqdm(results_queue, desc='Saving credits data'):
                if res['Ok']:
                    credits = res['Credits']
                    for category in ('Directors', 'Actors'):
                        for person in credits[category]:
                            data_dict['id'].append(person['id'])
                            data_dict['category'].append(category)
                            data_dict['name'].append(person['name'])
                            data_dict['profile_path'].append(person['profile_path'])
            pd.DataFrame(data_dict).drop_duplicates().to_csv(os.path.join('generated', 'credits.csv'), index=False)
            print('Successfully created credits.csv!')

            # Save details data
            movies.loc[:, 'Runtime'] = movies['Runtime'].fillna(0)
            movies = movies.astype({
                'Genres': 'str', 
                'Languages': 'str', 
                'Popularity': 'float',
                'Poster URI': 'str',
                'Countries': 'str',
                'Runtime': 'int',
                'Average Rating': 'float',
                'Directors': 'str',
                'Actors': 'str',
            })
            for res in tqdm(results_queue, desc='Saving movie details data'):
                if res['Ok']:
                    details = res['Details']
                    selection = (movies['Name'] == res['Name']) & (movies['Year'] == res['Year'])
                    movies.loc[selection, 'Genres'] = '.'.join(details['Genres'])
                    movies.loc[selection, 'Languages'] = '.'.join(details['Languages'])
                    movies.loc[selection, 'Popularity'] = details['Popularity']
                    movies.loc[selection, 'Poster URI'] = details['Poster Path']
                    movies.loc[selection, 'Countries'] = '.'.join(details['Countries'])
                    movies.loc[selection, 'Runtime'] = details['Runtime']
                    movies.loc[selection, 'Average Rating'] = details['Vote Average']
                    credits = res['Credits']
                    movies.loc[selection, 'Directors'] = '.'.join([str(x['id']) for x in credits['Directors']])
                    movies.loc[selection, 'Actors'] = '.'.join([str(x['id']) for x in credits['Actors']])

            movies.to_csv(os.path.join('generated', 'movies.csv'), index=False)
            print('Successfully updated movies.csv!')
            

def _send_http_request(url: str, TIMEOUT: float = 0.1) -> dict | None:
    '''
    Send http request and resolve to answer with optional TIMEOUT.
    '''

    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {os.environ["TMDB_API_ACCESS_TOKEN"]}'
    }

    try:
        time.sleep(TIMEOUT)
        response = requests.get(url, headers=headers)
        return response.json() if response.ok else None
    except requests.HTTPError:
        return None


def _get_movie_details(name: str, year: int) -> dict | None:
    '''
    Get the following information for a movie: genres, languages,
    popularity, poster_path, countries, runtime, and vote_average.
    '''

    res1 = _send_http_request(search_url(name, year))
    if res1 is not None and len(res1['results']) > 0:
        tmdb_id = res1['results'].pop(0)['id']
        movie = _send_http_request(movie_url(tmdb_id))
        if movie is not None:
            genres = [x['name'] for x in movie['genres']]
            languages = [x['english_name'] for x in movie['spoken_languages']]
            popularity = movie['popularity']
            poster_path = movie['poster_path']
            countries = [x['name'] for x in movie['production_countries']]
            runtime = movie['runtime']
            vote_average_10 = movie['vote_average']

            return {
                'tmdb_id': movie['id'],
                'Genres': genres,
                'Languages': languages,
                'Popularity': popularity,
                'Poster Path': poster_path,
                'Countries': countries,
                'Runtime': runtime,
                'Vote Average': vote_average_10
            }
    
    return None


def _get_movie_credits(tmdb_id: int, MAX_NUM_CAST: int = 10) -> dict | None:
    '''
    Get the following information for a movie: directors and `MAX_NUM_CAST` actors.
    '''

    res = _send_http_request(credits_url(tmdb_id))
    if res is not None:
    
        directors = list(filter(lambda x: x['job'] == 'Director', res['crew']))
        directors = [{'name': x['name'], 'id': x['id'], 'profile_path': x['profile_path']} for x in directors]

        actors = res['cast'][:min(len(res['cast']), MAX_NUM_CAST)]
        actors = [{'name': x['name'], 'id': x['id'], 'profile_path': x['profile_path']} for x in actors]

        return {
            'Directors': directors,
            'Actors': actors
        }

    return None


if __name__ == '__main__':
    main()