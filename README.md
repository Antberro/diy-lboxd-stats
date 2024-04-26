# Getting started

Run the following command to install all
required python libraries:

```shell
pip install -r requirements.txt
```

Login to your Letterboxd account and select `Settings > DATA > EXPORT YOUR DATA`. This will download a folder with all your movie data. Place this folder at the root of this project directory and rename the folder to `data`.

Create a free account with The Movie Database (TMDB) and generate an API Access Token. Save this as an environment variable using the following command:

```shell
export TMDB_API_ACCESS_TOKEN=[ENTER KEY HERE]
```

Run the following command to merge your letterboxd data along with data from TMDB to csv files (`movies.csv`, `credits.csv`):

```shell
python main.py
```

Then run the following command to precompute various statistics from your data. This will create a `stats\` folder with several yaml files to be read by the user interface:

```
python stats.py
```

Finally, run the following command to launch a user interface in the browser:

```
streamlit run ui.py
```