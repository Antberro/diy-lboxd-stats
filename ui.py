import os
import streamlit as st
import pandas as pd
import altair as alt
import yaml
import math


COLOR_GREEN = '#2ed939'
COLOR_BLUE = '#3fa1e8'
COLOR_ORANGE = '#eba134'
COLOR_GRAY = '#717475'


def _read_yaml_file(file_path):
    with open(file_path, 'r') as file:
        try:
            data = yaml.safe_load(file)
            return data
        except yaml.YAMLError as e:
            print(f"Error reading YAML file '{file_path}': {e}")
            return None


def _img_url(uri: str):
    return f'https://image.tmdb.org/t/p/w500{uri}'
    

def _make_gallery(uris: str, NUM_COLS: int, POSTER_WIDTH: int = 70, captions: list = None, links: list = None):
    NUM_ROWS = math.ceil(len(uris) / NUM_COLS)
    grid = [st.columns(NUM_COLS) for _ in range(NUM_ROWS)]
    for i, item in enumerate(uris):
        col = i % NUM_COLS
        row = i // NUM_COLS
        html_str = lambda target, img: f'<a href="{target}"><img src="{img}" style="width:{POSTER_WIDTH}px" /></a>'
        grid[row][col].markdown(html_str(links[i] if links else '', _img_url(item)), unsafe_allow_html=True)
        if captions:
            grid[row][col].markdown(captions[i])


def ui_all_time():

    stats = _read_yaml_file(os.path.join('stats', 'all-time-stats.yaml'))

    st.title('A Life in Film')

    # `Summary` section
    col11, col12, col13, col14 = st.columns(4)
    col11.metric('FILMS', stats['Summary']['Films'])
    col12.metric('HOURS', stats['Summary']['Hours'])
    col13.metric('DIRECTORS', stats['Summary']['Directors'])
    col14.metric('COUNTRIES', stats['Summary']['Countries'])

    st.divider()

    # `BY YEAR` section
    st.subheader('BY YEAR')
    by_year_selection = st.selectbox('', ('FILMS', 'RATINGS', 'DIARY'), key='by_year')
    if by_year_selection == 'FILMS':
        by_year_data = pd.DataFrame({
            'Year': stats['By_Year']['Films']['Year'], 
            'Count': stats['By_Year']['Films']['Count']
        })
        st.bar_chart(data=by_year_data, x='Year', y='Count', color=COLOR_BLUE)
    elif by_year_selection == 'RATINGS':
        by_year_data = pd.DataFrame({
            'Year': stats['By_Year']['Ratings']['Year'], 
            'Avg Rating': stats['By_Year']['Ratings']['Rating']
        })
        st.bar_chart(data=by_year_data, x='Year', y='Avg Rating', color=COLOR_ORANGE)
    else:
        by_year_data = pd.DataFrame({
            'Year': stats['By_Year']['Diary']['Year'], 
            'Count': stats['By_Year']['Diary']['Count']
        })
        st.bar_chart(data=by_year_data, x='Year', y='Count', color=COLOR_GREEN)

    st.divider()

    # `HIGHEST RATED DECADES` section
    st.subheader('HIGHEST RATED DECADES')
    for x in stats['Highest_Rated_Decades']:
        decade = x['Decade']
        rating = x['Average_Rating']
        st.markdown(f'## {decade}\n★ Average {rating}')
        _make_gallery([i['Poster'] for i in x['Movies']], NUM_COLS=9, links=[i['URI'] for i in x['Movies']])
    
    st.divider()

    # `GENRES, COUNTRIES & LANGUAGES` section
    stats_label = {'MOST WATCHED': 'Most_Watched', 'HIGHEST RATED': 'Highest_Rated'}
    gcl_selection = st.selectbox('', ('MOST WATCHED', 'HIGHEST RATED'), key='gcl')
    st.subheader('GENRES, COUNTRIES & LANGUAGES')
    label = {'Genres': 'Genre', 'Countries': 'Country', 'Languages': 'Language'}
    color = {'Genres': COLOR_GREEN, 'Countries': COLOR_BLUE, 'Languages': COLOR_ORANGE}

    gcl_cols = st.columns(3)
    for i, category in enumerate(('Genres', 'Countries', 'Languages')):
        x_label = 'Count' if gcl_selection == 'MOST WATCHED' else 'Average Rating'
        x_col = 'Count' if gcl_selection == 'MOST WATCHED' else 'Average_Rating'
        gcl_data = pd.DataFrame({
            label[category]: stats[category][stats_label[gcl_selection]][category],
            x_label: stats[category][stats_label[gcl_selection]][x_col]
        })
        gcl_query = (
            alt.Chart(gcl_data)
            .mark_bar(color=color[category])
            .encode(
                x=alt.X(x_label, axis=alt.Axis(labels=False, title=None)), 
                y=alt.Y(label[category], sort=alt.EncodingSortField(field='Count', order='descending'), axis=alt.Axis(labels=True, title=None))
            )
            .properties(width=200, height=350)
            .configure_axis(
                grid=False
            )
        )
        gcl_cols[i].altair_chart(gcl_query)
     
    st.divider()

    # `MOST WATCHED` section
    st.subheader('MOST WATCHED')
    # TODO

    st.divider()

    # `RATED HIGHER THAN AVERAGE` section
    st.subheader('RATED HIGHER THAN AVERAGE')
    highs = [x['Movie']['Poster'] for x in stats['Rated_Higher_Than_Avg']]
    highs_captions = [f'★ {x["Rating"]} vs {round(x["Average Rating"],2)}' for x in stats['Rated_Higher_Than_Avg']]
    highs_links = [x['Movie']['URI'] for x in stats['Rated_Higher_Than_Avg']]
    _make_gallery(highs, NUM_COLS=5, captions=highs_captions, POSTER_WIDTH=100, links=highs_links)

    st.divider()

    # `RATED LOWER THAN AVERAGE` section
    st.subheader('RATED LOWER THAN AVERAGE')
    lows = [x['Movie']['Poster'] for x in stats['Rated_Lower_Than_Avg']]
    lows_captions = [f'★ {x["Rating"]} vs {round(x["Average Rating"],2)}' for x in stats['Rated_Lower_Than_Avg']]
    lows_links = [x['Movie']['URI'] for x in stats['Rated_Lower_Than_Avg']]
    _make_gallery(lows, NUM_COLS=5, captions=lows_captions, POSTER_WIDTH=100, links=lows_links)

    st.divider()

    # `ACTORS` section
    st.subheader('ACTORS')
    actors_selection = st.selectbox('', ('MOST WATCHED', 'HIGHEST RATED'), key='actors')
    if actors_selection == 'MOST WATCHED':
        actors_captions = []
        actors_links = []
        for i, item in enumerate(stats['Actors']['Most_Watched']['Actors']):
            ct = stats['Actors']['Most_Watched']['Count'][i]
            actors_captions.append(f'''{item["Name"]}

                                    {ct} films''')
            actors_links.append(f'https://letterboxd.com/actor/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        actors = [a['Profile URI'] for a in stats['Actors']['Most_Watched']['Actors']]
        _make_gallery(actors, NUM_COLS=5, captions=actors_captions, POSTER_WIDTH=100, links=actors_links)
    else:
        actors_captions = []
        actors_links = []
        for i, item in enumerate(stats['Actors']['Highest_Rated']['Actors']):
            r = round(stats['Actors']['Highest_Rated']['Average_Rating'][i], 2)
            actors_captions.append(f'''{item["Name"]}
                                   
                                   ★ {r}''')
            actors_links.append(f'https://letterboxd.com/actor/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        actors = [a['Profile URI'] for a in stats['Actors']['Highest_Rated']['Actors']]
        _make_gallery(actors, NUM_COLS=5, captions=actors_captions, POSTER_WIDTH=100, links=actors_links)

    st.divider()

    # `DIRECTORS` section
    st.subheader('DIRECTORS')
    directors_selection = st.selectbox('', ('MOST WATCHED', 'HIGHEST RATED'), key='directors')
    if directors_selection == 'MOST WATCHED':
        directors_captions = []
        directors_links = []
        for i, item in enumerate(stats['Directors']['Most_Watched']['Directors']):
            ct = stats['Directors']['Most_Watched']['Count'][i]
            directors_captions.append(f'''{item["Name"]}

                                    {ct} films''')
            directors_links.append(f'https://letterboxd.com/director/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        directors = [d['Profile URI'] for d in stats['Directors']['Most_Watched']['Directors']]
        _make_gallery(directors, NUM_COLS=5, captions=directors_captions, POSTER_WIDTH=100, links=directors_links)
    else:
        directors_captions = []
        directors_links = []
        for i, item in enumerate(stats['Directors']['Highest_Rated']['Directors']):
            r = round(stats['Directors']['Highest_Rated']['Average_Rating'][i], 2)
            directors_captions.append(f'''{item["Name"]}
                                   
                                   ★ {r}''')
            directors_links.append(f'https://letterboxd.com/director/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        directors = [d['Profile URI'] for d in stats['Directors']['Highest_Rated']['Directors']]
        _make_gallery(directors, NUM_COLS=5, captions=directors_captions, POSTER_WIDTH=100, links=directors_links)


def ui_for_year(year: int):

    stats = _read_yaml_file(os.path.join('stats', f'{year}-stats.yaml'))

    st.title(f'{year} in Film')

    # `Summary` section
    cols = st.columns(6)
    cols[0].metric('DIARY ENTRIES', stats['Summary']['Diary_Entries'])
    cols[1].metric('REVIEWS', stats['Summary']['Reviews'])
    cols[2].metric('LISTS', stats['Summary']['Lists'])
    cols[3].metric('LIKES', stats['Summary']['Likes'])
    cols[4].metric('COMMENTS', stats['Summary']['Comments'])
    cols[5].metric('HOURS', stats['Summary']['Hours'])

    st.divider()

    # `HIGHEST RATED FILMS` section
    st.subheader('HIGHEST RATED FILMS')
    items = [x['Movie']['Poster'] for x in stats['Highest_Rated']]
    captions = [f'★ {x["Rating"]}' for x in stats['Highest_Rated']]
    links = [x['Movie']['URI'] for x in stats['Highest_Rated']]
    _make_gallery(items, NUM_COLS=9, captions=captions, links=links)
    
    st.divider()

    # `BY WEEK` section
    st.subheader('BY WEEK')
    # TODO

    st.divider()

    # `MILESTONES` section
    st.subheader('MILESTONES')
    month = {
        '01': 'Jan',
        '02': 'Feb',
        '03': 'Mar',
        '04': 'Apr',
        '05': 'May',
        '06': 'Jun',
        '07': 'Jul',
        '08': 'Aug',
        '09': 'Sep',
        '10': 'Oct',
        '11': 'Nov',
        '12': 'Dec',
    }
    html_str = lambda target, img: f'<a href="{target}"><img src="{img}" style="width:{150}px" /></a>'
    milestones = stats['Milestones']
    links = [milestones['First']['Movie']['URI'], milestones['Last']['Movie']['URI']]
    _, mcol1, _, mcol2, _ = st.columns(5)
    mcol1.markdown('First film')
    mcol1.markdown(html_str(links[0] if links else '', _img_url(milestones['First']['Movie']['Poster'])), unsafe_allow_html=True)
    m1, d1 = milestones['First']['Date'].split('-')
    mcol1.markdown(f'{month[m1]} {d1}')
    mcol2.markdown('Last film')
    mcol2.markdown(html_str(links[1] if links else '', _img_url(milestones['Last']['Movie']['Poster'])), unsafe_allow_html=True)
    m2, d2 = milestones['Last']['Date'].split('-')
    mcol2.markdown(f'{month[m2]} {d2}')

    st.divider()

    # `MOST WATCHED` section
    st.subheader('MOST WATCHED')
    mw_items = [x['Movie']['Poster'] for x in stats['Most_Watched']]
    mw_captions = [x['Times_Rewatched'] for x in stats['Most_Watched']]
    _make_gallery(mw_items, NUM_COLS=9, captions=mw_captions)

    st.divider()

    # `GENRES, COUNTRIES & LANGUAGES` section
    stats_label = {'MOST WATCHED': 'Most_Watched', 'HIGHEST RATED': 'Highest_Rated'}
    gcl_selection = st.selectbox('', ('MOST WATCHED', 'HIGHEST RATED'), key='gcl')
    st.subheader('GENRES, COUNTRIES & LANGUAGES')
    label = {'Genres': 'Genre', 'Countries': 'Country', 'Languages': 'Language'}
    color = {'Genres': COLOR_GREEN, 'Countries': COLOR_BLUE, 'Languages': COLOR_ORANGE}

    gcl_cols = st.columns(3)
    for i, category in enumerate(('Genres', 'Countries', 'Languages')):
        x_label = 'Count' if gcl_selection == 'MOST WATCHED' else 'Average Rating'
        x_col = 'Count' if gcl_selection == 'MOST WATCHED' else 'Average_Rating'
        gcl_data = pd.DataFrame({
            label[category]: stats[category][stats_label[gcl_selection]][category],
            x_label: stats[category][stats_label[gcl_selection]][x_col]
        })
        gcl_query = (
            alt.Chart(gcl_data)
            .mark_bar(color=color[category])
            .encode(
                x=alt.X(x_label, axis=alt.Axis(labels=False, title=None)), 
                y=alt.Y(label[category], sort=alt.EncodingSortField(field='Count', order='descending'), axis=alt.Axis(labels=True, title=None))
            )
            .properties(width=200, height=350)
            .configure_axis(
                grid=False
            )
        )
        gcl_cols[i].altair_chart(gcl_query)
     
    st.divider()

    # `BREAKDOWN` section
    st.subheader('BREAKDOWN')
    PIE_SIZE = 250
    bcols = st.columns(3)
    with bcols[0]:
        pie_data1 = pd.DataFrame({
                'Category': [f'{year} Releases', 'Older'],
                'Value': [
                    stats['Breakdown']['Current_Year_Releases'][f'{year}_Releases'], 
                    stats['Breakdown']['Current_Year_Releases']['Older']
                ],
                'Total': 2*[stats['Breakdown']['Current_Year_Releases']['Total']],
                'Percentage': [
                    f"{round(100*stats['Breakdown']['Current_Year_Releases'][f'{year}_Releases'] / stats['Breakdown']['Current_Year_Releases']['Total'],2)}%", 
                    f"{round(100*stats['Breakdown']['Current_Year_Releases']['Older'] / stats['Breakdown']['Current_Year_Releases']['Total'],2)}%"
                ]
            })
        pie_query1 = (
            alt.Chart(pie_data1)
            .mark_arc()
            .encode(
                angle='Value',
                color=alt.Color('Category', scale=alt.Scale(range=[COLOR_GREEN, COLOR_GRAY])),
                tooltip=['Category', 'Value', 'Total', 'Percentage']
            )
            .properties(
                width=PIE_SIZE,
                height=PIE_SIZE
            )
        )
        bcols[0].altair_chart(pie_query1)
    with bcols[1]:
        pie_data2 = pd.DataFrame({
            'Category': ['Watches', 'Rewatches'],
            'Value': [
                stats['Breakdown']['Watches']['Watches'], 
                stats['Breakdown']['Watches']['Rewatches']
            ],
            'Total': 2*[stats['Breakdown']['Watches']['Total']],
            'Percentage': [
                f"{round(100*stats['Breakdown']['Watches']['Watches'] / stats['Breakdown']['Watches']['Total'],2)}%", 
                f"{round(100*stats['Breakdown']['Watches']['Rewatches'] / stats['Breakdown']['Watches']['Total'],2)}%"
            ]
        })
        pie_query2 = (
            alt.Chart(pie_data2)
            .mark_arc()
            .encode(
                angle='Value',
                color=alt.Color('Category', scale=alt.Scale(range=[COLOR_GREEN, COLOR_GRAY])),
                tooltip=['Category', 'Value', 'Total', 'Percentage']
            )
            .properties(
                width=PIE_SIZE,
                height=PIE_SIZE
            )
        )
        bcols[1].altair_chart(pie_query2)
    with bcols[2]:
        pie_data3 = pd.DataFrame({
            'Category': ['Reviewed', 'Not Reviewed'],
            'Value': [
                stats['Breakdown']['Reviewed']['Reviewed'], 
                stats['Breakdown']['Reviewed']['Not_Reviewed']
            ],
            'Total': 2*[stats['Breakdown']['Reviewed']['Total']],
            'Percentage': [
                f"{round(100*stats['Breakdown']['Reviewed']['Reviewed'] / stats['Breakdown']['Reviewed']['Total'],2)}%", 
                f"{round(100*stats['Breakdown']['Reviewed']['Not_Reviewed'] / stats['Breakdown']['Reviewed']['Total'],2)}%"
            ]
        })
        pie_query3 = (
            alt.Chart(pie_data3)
            .mark_arc()
            .encode(
                angle='Value',
                color=alt.Color('Category', scale=alt.Scale(range=[COLOR_GREEN, COLOR_GRAY])),
                tooltip=['Category', 'Value', 'Total', 'Percentage']
            )
            .properties(
                width=PIE_SIZE,
                height=PIE_SIZE
            )
        )
        bcols[2].altair_chart(pie_query3)

    st.markdown('RATINGS SPREAD')
    ratings_spread_data = pd.DataFrame({
        'Rating': [f'★ {x}' for x in  stats['Breakdown']['Ratings_Spread']['Rating']], 
        'Count': stats['Breakdown']['Ratings_Spread']['Count']
    })
    st.bar_chart(data=ratings_spread_data, x='Rating', y='Count', color=COLOR_GRAY)
    
    st.divider()

    # `ACTORS` section
    st.subheader('ACTORS')
    actors_selection = st.selectbox('', ('MOST WATCHED', 'HIGHEST RATED'), key='actors')
    if actors_selection == 'MOST WATCHED':
        actors_captions = []
        actors_links = []
        for i, item in enumerate(stats['Actors']['Most_Watched']['Actors']):
            ct = stats['Actors']['Most_Watched']['Count'][i]
            actors_captions.append(f'''{item["Name"]}

                                    {ct} films''')
            actors_links.append(f'https://letterboxd.com/actor/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        actors = [a['Profile URI'] for a in stats['Actors']['Most_Watched']['Actors']]
        _make_gallery(actors, NUM_COLS=5, captions=actors_captions, POSTER_WIDTH=100, links=actors_links)
    else:
        actors_captions = []
        actors_links = []
        for i, item in enumerate(stats['Actors']['Highest_Rated']['Actors']):
            r = round(stats['Actors']['Highest_Rated']['Average_Rating'][i], 2)
            actors_captions.append(f'''{item["Name"]}
                                   
                                   ★ {r}''')
            actors_links.append(f'https://letterboxd.com/actor/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        actors = [a['Profile URI'] for a in stats['Actors']['Highest_Rated']['Actors']]
        _make_gallery(actors, NUM_COLS=5, captions=actors_captions, POSTER_WIDTH=100, links=actors_links)

    st.divider()

    # `DIRECTORS` section
    st.subheader('DIRECTORS')
    directors_selection = st.selectbox('', ('MOST WATCHED', 'HIGHEST RATED'), key='directors')
    if directors_selection == 'MOST WATCHED':
        directors_captions = []
        directors_links = []
        for i, item in enumerate(stats['Directors']['Most_Watched']['Directors']):
            ct = stats['Directors']['Most_Watched']['Count'][i]
            directors_captions.append(f'''{item["Name"]}

                                    {ct} films''')
            directors_links.append(f'https://letterboxd.com/director/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        directors = [d['Profile URI'] for d in stats['Directors']['Most_Watched']['Directors']]
        _make_gallery(directors, NUM_COLS=5, captions=directors_captions, POSTER_WIDTH=100, links=directors_links)
    else:
        directors_captions = []
        directors_links = []
        for i, item in enumerate(stats['Directors']['Highest_Rated']['Directors']):
            r = round(stats['Directors']['Highest_Rated']['Average_Rating'][i], 2)
            directors_captions.append(f'''{item["Name"]}
                                   
                                   ★ {r}''')
            directors_links.append(f'https://letterboxd.com/director/{"-".join(item["Name"].replace(".", "").lower().split(" "))}')
        directors = [d['Profile URI'] for d in stats['Directors']['Highest_Rated']['Directors']]
        _make_gallery(directors, NUM_COLS=5, captions=directors_captions, POSTER_WIDTH=100, links=directors_links)

    st.divider()

    # `HIGHS AND LOWS` section
    # TODO: add links
    st.subheader('HIGHS AND LOWS')
    hl_cols = st.columns(4)

    hl_cols[0].markdown('Highest average')
    hl_cols[0].image(_img_url(stats['High_And_Lows']['Highest_Average']['Movie']['Poster']), width=150)
    hl_cols[0].markdown(f"★ {stats['High_And_Lows']['Highest_Average']['Rating']}")
    
    hl_cols[1].markdown('Lowest average')
    hl_cols[1].image(_img_url(stats['High_And_Lows']['Lowest_Average']['Movie']['Poster']), width=150)
    hl_cols[1].markdown(f"★ {stats['High_And_Lows']['Lowest_Average']['Rating']}")

    hl_cols[2].markdown('Most popular')
    hl_cols[2].image(_img_url(stats['High_And_Lows']['Most_Popular']['Movie']['Poster']), width=150)
    hl_cols[2].markdown(f"★ {stats['High_And_Lows']['Most_Popular']['Rating']}")
    
    hl_cols[3].markdown('Most obscure')
    hl_cols[3].image(_img_url(stats['High_And_Lows']['Most_Obscure']['Movie']['Poster']), width=150)
    hl_cols[3].markdown(f"★ {stats['High_And_Lows']['Most_Obscure']['Rating']}")

    st.divider()

    # `RATED HIGHER THAN AVERAGE` section
    st.subheader('RATED HIGHER THAN AVERAGE')
    highs = [x['Movie']['Poster'] for x in stats['Rated_Higher_Than_Avg']]
    highs_captions = [f'★ {x["Rating"]} vs {round(x["Average Rating"],2)}' for x in stats['Rated_Higher_Than_Avg']]
    highs_links = [x['Movie']['URI'] for x in stats['Rated_Higher_Than_Avg']]
    _make_gallery(highs, NUM_COLS=5, captions=highs_captions, POSTER_WIDTH=100, links=highs_links)

    st.divider()

    # `RATED LOWER THAN AVERAGE` section
    st.subheader('RATED LOWER THAN AVERAGE')
    lows = [x['Movie']['Poster'] for x in stats['Rated_Lower_Than_Avg']]
    lows_captions = [f'★ {x["Rating"]} vs {round(x["Average Rating"],2)}' for x in stats['Rated_Lower_Than_Avg']]
    lows_links = [x['Movie']['URI'] for x in stats['Rated_Lower_Than_Avg']]
    _make_gallery(lows, NUM_COLS=5, captions=lows_captions, POSTER_WIDTH=100, links=lows_links)




if __name__ == '__main__':

    movies = pd.read_csv(os.path.join('generated', 'movies.csv'))

    options = sorted(movies['Watched Date'].dropna().map(lambda x: int(str(x).split('-')[0])).drop_duplicates().tolist())
    options = ['All time', *options]
    selection = st.selectbox('', options)

    if selection == 'All time':
        ui_all_time()
    else:
        ui_for_year(selection)

    

    